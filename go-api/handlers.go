package main

import (
	"fmt"
	"github.com/dgrijalva/jwt-go"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"golang.org/x/crypto/argon2"
	"net/http"
	"os"
	"time"
	//"io/ioutil"
)

// pingHandler handles the /ping endpoint
func pingHandler(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

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
	sensorUUID, err := uuid.Parse(request.SensorUUID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "could not parse sensor UUID"})
		return
	}
	if request.Email != "" {
		user, err := loadUserByEmail(request.Email)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "user not found"})
			return
		}
		if err := registerSensor(sensorUUID, request.SensorSecret, user.UUID); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "could not register sensor"})
			return
		}
		c.JSON(http.StatusCreated, gin.H{"message": "sensor registered successfully"})
		return
	}
	if err := registerSensorWithoutUser(sensorUUID, request.SensorSecret); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "could not register sensor"})
		return
	}
	c.JSON(http.StatusCreated, gin.H{"message": "sensor registered successfully"})
}

// sensorDataHandler handles the POST /sensor_data endpoint
func sensorDataHandler(c *gin.Context) {
	var request SensorDataRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	requestSensorSecret := c.GetHeader("SENSOR_SECRET")

	// load registered sensor by sensor_id, then match: user_email, sensor_secret
	sensorUUID, err := uuid.Parse(request.SensorUUID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "could not parse sensor UUID"})
		return
	}
	sensor, err := loadSensorByUUID(sensorUUID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "sensor not found"})
		return
	}
	if sensor.Secret != requestSensorSecret {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}
	user, err := loadUserByEmail(request.Email)
	if sensor.UserUUID != user.UUID {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	// checks ok, now write record to database
	if err := storeSensorReading(
		sensor.SensorUUID, request.SensorType, request.SensorName, request.UnixTime, user.UUID, request.Value,
	); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to register sensor data"})
		return
	}
	c.JSON(http.StatusCreated, gin.H{"message": "sensor data registered successfully"})
}

// signupHandler handles the POST /signup endpoint
func signupHandler(c *gin.Context) {
	adminSecret := c.GetHeader("ADMIN_SECRET")
	if adminSecret != os.Getenv("ADMIN_SECRET") {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}
	var request SignupRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Hash the password using Argon2
	hashedPassword := argon2.IDKey([]byte(request.Password), []byte(os.Getenv("SALT")), 1, 64*1024, 4, 32)
	hashedPasswordStr := fmt.Sprintf("%x", hashedPassword) // Convert to hexadecimal string
	if err := createUser(request.Email, hashedPasswordStr); err != nil {
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
		"userUUID": user.UUID,
		"exp":      time.Now().Add(time.Hour * 1).Unix(),
	})
	JWTSecret := []byte(os.Getenv("JWT_SECRET"))
	tokenString, err := token.SignedString(JWTSecret)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "could not generate token"})
		return
	}
	if err := storeUserJWTToken(user.UUID, tokenString); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "could not store generated token"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"token": tokenString})
}

func logoutHandler(c *gin.Context) {
	contextUserUUID, exists := c.Get("userUUID")
	if !exists {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "User ID not found"})
		return
	}
	userUUID, ok := contextUserUUID.(uuid.UUID)
	if !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Could not parse context UUID"})
		return
	}
	deleteUserJWTTokens(userUUID)
	c.JSON(http.StatusOK, gin.H{"message": "logged out"})
}

// protectedHandler handles the GET /protected endpoint
func protectedHandler(c *gin.Context) {
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
	if err := db.Where("user_id = ?", user.UUID).Find(&sensors).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch sensors"})
		return
	}
	sensorData := make(map[uuid.UUID][]SensorReading)
	for _, sensor := range sensors {
		var readings []SensorReading
		if err := db.Where("uuid = ? AND user_id = ?", sensor.SensorUUID, user.UUID).Find(&readings).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch sensor readings"})
			return
		}
		sensorData[sensor.SensorUUID] = readings
	}
	c.JSON(http.StatusOK, sensorData)
}
