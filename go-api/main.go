package main

import (
	"fmt"
	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"log"
	"os"
)

var db *gorm.DB

func setupRouter() *gin.Engine {
	router := gin.Default()

	router.GET("/health", healthHandler)
	router.POST("/register_sensor", registerSensorHandler)
	router.POST("/sensor_data", sensorDataHandler)
	router.POST("/signup", signupHandler)
	router.POST("/login", loginHandler)
	router.GET("/protected", authMiddleware(), protectedHandler)
	router.GET("/sensors", authMiddleware(), sensorsHandler)

	return router
}

func main() {
	err := godotenv.Load()
	if err != nil {
		log.Fatal("Error loading .env file")
	}

	dbUser := os.Getenv("DB_USER")
	dbPassword := os.Getenv("DB_PASSWORD")
	dbName := os.Getenv("DB_NAME")
	dbHost := os.Getenv("DB_HOST")
	dbPort := os.Getenv("DB_PORT")

	dsn := fmt.Sprintf("user=%s password=%s dbname=%s host=%s port=%s sslmode=disable", dbUser, dbPassword, dbName, dbHost, dbPort)

	db, err = gorm.Open(postgres.Open(dsn), &gorm.Config{})
	if err != nil {
		log.Fatal("Error connecting to the database:", err)
	}

	if err := db.AutoMigrate(&AppUser{}, &RegisteredSensor{}, &SensorReading{}); err != nil {
		log.Fatal("Error auto-migrating tables:", err)
	}

	fmt.Println("Successfully connected to the database and ensured tables exist")

	router := setupRouter()

	fmt.Println("Server is listening on port 8090")
	err = router.Run(":8090")
	if err != nil {
		log.Fatal("Error starting the server:", err)
	}
}
