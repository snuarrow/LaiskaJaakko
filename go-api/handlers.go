package main

import (
	"fmt"
	"github.com/dgrijalva/jwt-go"
	"github.com/gin-gonic/gin"
	"golang.org/x/crypto/argon2"
	"net/http"
	"os"
	"time"
)

// healthHandler handles the /health endpoint
func healthHandler(c *gin.Context) {
	sqlDB, err := db.DB()
	if err != nil || sqlDB.Ping() != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": "unhealthy"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "healthy"})
}

// registerSensorHandler handles the POST /register_sensor endpoint
func registerSensorHandler(c *gin.Context) {
	adminSecret := c.GetHeader("ADMIN_SECRET")
	if adminSecret != os.Getenv("ADMIN_SECRET") {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	var request RegisterSensorRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var user AppUser
	if err := db.Where("id = ?", request.UserID).First(&user).Error; err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "user ID not found"})
		return
	}

	sensor := RegisteredSensor{
		UUID:   request.UUID,
		Secret: request.Secret,
		UserID: request.UserID,
	}

	if err := db.Create(&sensor).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to register sensor"})
		return
	}

	c.JSON(http.StatusCreated, gin.H{"message": "sensor registered successfully"})
}

// sensorDataHandler handles the POST /sensor_data endpoint
func sensorDataHandler(c *gin.Context) {
	sensorSecret := c.GetHeader("SENSOR_SECRET")
	var sensor RegisteredSensor
	if err := db.Where("secret = ?", sensorSecret).First(&sensor).Error; err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	var request SensorDataRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var user AppUser
	if err := db.Where("id = ?", request.UserID).First(&user).Error; err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "user ID not found"})
		return
	}

	if request.UserID != sensor.UserID {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	sensorReading := SensorReading{
		UUID:       request.UUID,
		SensorType: request.SensorType,
		SensorName: request.SensorName,
		UnixTime:   request.UnixTime,
		UserID:     request.UserID,
	}

	if err := db.Create(&sensorReading).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to register sensor data"})
		return
	}

	c.JSON(http.StatusCreated, gin.H{"message": "sensor data registered successfully"})
}

// signupHandler handles the POST /signup endpoint
func signupHandler(c *gin.Context) {
	var request SignupRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Hash the password using Argon2
	hashedPassword := argon2.IDKey([]byte(request.Password), []byte(os.Getenv("SALT")), 1, 64*1024, 4, 32)
	hashedPasswordStr := fmt.Sprintf("%x", hashedPassword) // Convert to hexadecimal string

	user := AppUser{
		Email:    request.Email,
		Password: hashedPasswordStr,
	}

	if err := db.Create(&user).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create user"})
		return
	}

	c.JSON(http.StatusCreated, gin.H{"message": "user created successfully"})
}

// loginHandler handles the POST /login endpoint
func loginHandler(c *gin.Context) {
	var request LoginRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var user AppUser
	if err := db.Where("email = ?", request.Email).First(&user).Error; err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid credentials"})
		return
	}

	// Hash the incoming password using Argon2
	hashedPassword := argon2.IDKey([]byte(request.Password), []byte(os.Getenv("SALT")), 1, 64*1024, 4, 32)
	hashedPasswordStr := fmt.Sprintf("%x", hashedPassword) // Convert to hexadecimal string

	// Compare the hashed password
	if user.Password != hashedPasswordStr {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid credentials"})
		return
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"email": user.Email,
		"exp":   time.Now().Add(time.Hour * 1).Unix(),
	})
	JWTSecret := []byte(os.Getenv("JWT_SECRET"))
	tokenString, err := token.SignedString(JWTSecret)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "could not generate token"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"token": tokenString})
}

// protectedHandler handles the GET /protected endpoint
func protectedHandler(c *gin.Context) {
	tokenString := c.GetHeader("Authorization")
	if tokenString == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "missing token"})
		return
	}
	JWTSecret := []byte(os.Getenv("JWT_SECRET"))
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return JWTSecret, nil
	})
	if err != nil || !token.Valid {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid token"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "protected resource"})
}

// sensorsHandler handles the GET /sensors endpoint
func sensorsHandler(c *gin.Context) {
	tokenString := c.GetHeader("Authorization")
	if tokenString == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "missing token"})
		return
	}
	JWTSecret := []byte(os.Getenv("JWT_SECRET"))
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return JWTSecret, nil
	})
	if err != nil || !token.Valid {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid token"})
		return
	}

	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok || !token.Valid {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid token"})
		return
	}

	email, _ := claims["email"].(string)
	var user AppUser
	if err := db.Where("email = ?", email).First(&user).Error; err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "user not found"})
		return
	}

	var sensors []RegisteredSensor
	if err := db.Where("user_id = ?", user.ID).Find(&sensors).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch sensors"})
		return
	}

	sensorData := make(map[string][]SensorReading)
	for _, sensor := range sensors {
		var readings []SensorReading
		if err := db.Where("uuid = ? AND user_id = ?", sensor.UUID, user.ID).Find(&readings).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch sensor readings"})
			return
		}
		sensorData[sensor.UUID] = readings
	}

	c.JSON(http.StatusOK, sensorData)
}
