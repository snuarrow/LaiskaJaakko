package main

import (
	"time"
)

// AppUser represents the model for the AppUser table in the database
type AppUser struct {
	ID       uint   `gorm:"primaryKey"`
	Email    string `gorm:"uniqueIndex;not null"`
	Password string `gorm:"not null"`
}

// RegisteredSensor represents the model for the RegisteredSensor table in the database
type RegisteredSensor struct {
	UUID   string `gorm:"type:uuid;primaryKey"`
	Secret string `gorm:"type:text;not null"`
	UserID string `gorm:"type:text;not null"`
}

// SensorReading represents the model for the SensorReadings table in the database
type SensorReading struct {
	ID         uint      `gorm:"primaryKey"`
	UUID       string    `gorm:"type:uuid"`
	SensorType string    `gorm:"type:text"`
	SensorName string    `gorm:"type:text"`
	UnixTime   int64     `gorm:"type:bigint"`
	UserID     string    `gorm:"type:text;not null"`
	CreatedAt  time.Time `gorm:"autoCreateTime"`
}
