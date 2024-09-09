package main

// RegisterSensorRequest represents the expected JSON payload for registering a sensor
type RegisterSensorRequest struct {
	SensorUUID   string `json:"SensorUUID" binding:"required,uuid"`
	SensorSecret string `json:"SensorSecret" binding:"required"`
	Email        string `json:"email"`
}

// SensorDataRequest represents the expected JSON payload for sensor data
type SensorDataRequest struct {
	SensorUUID string  `json:"sensorUUID" binding:"required,uuid"`
	SensorType string  `json:"sensorType" binding:"required"`
	SensorName string  `json:"sensorName" binding:"required"`
	UnixTime   int64   `json:"unixTime" binding:"required,gt=0"`
	Email      string  `json:"email" binding:"required"`
	Value      float32 `json:"value" binding:"required"`
}

// SignupRequest represents the expected JSON payload for user signup
type SignupRequest struct {
	Email    string `json:"email" binding:"required,email"`
	Password string `json:"password" binding:"required"`
}

// LoginRequest represents the expected JSON payload for user login
type LoginRequest struct {
	Email    string `json:"email" binding:"required,email"`
	Password string `json:"password" binding:"required"`
}
