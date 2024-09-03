package main

// RegisterSensorRequest represents the expected JSON payload for registering a sensor
type RegisterSensorRequest struct {
	UUID   string `json:"uuid" binding:"required,uuid"`
	Secret string `json:"secret" binding:"required"`
	UserID string `json:"user_id" binding:"required"`
}

// SensorDataRequest represents the expected JSON payload for sensor data
type SensorDataRequest struct {
	UUID       string `json:"uuid" binding:"required,uuid"`
	SensorType string `json:"sensor_type" binding:"required"`
	SensorName string `json:"sensor_name" binding:"required"`
	UnixTime   int64  `json:"unix_time" binding:"required,gt=0"`
	UserID     string `json:"user_id" binding:"required"`
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
