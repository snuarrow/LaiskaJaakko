package main

import (
	"fmt"
	"github.com/gin-gonic/gin"
	"log"
)

func setupRouter() *gin.Engine {
	router := gin.Default()
	router.GET("/ping", pingHandler)
	router.GET("/health", healthHandler)
	router.POST("/register_sensor", registerSensorHandler)
	router.POST("/sensor_data", sensorDataHandler)
	router.POST("/signup", signupHandler)
	router.POST("/login", loginHandler)
	router.POST("/logout", authMiddleware(), logoutHandler)
	router.GET("/protected", authMiddleware(), protectedHandler)
	router.GET("/sensors", authMiddleware(), sensorsHandler)
	return router
}

func main() {
	setupDBConnection()
	createDBTables()
	router := setupRouter()
	fmt.Println("Successfully connected to the database and ensured tables exist")
	fmt.Println("Server is listening on port 8090")
	err := router.Run(":8090")
	if err != nil {
		log.Fatal("Error starting the server:", err)
	}
}
