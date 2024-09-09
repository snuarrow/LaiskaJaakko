package main

import (
	"github.com/google/uuid"
	"time"
)

// AppUser represents the model for the AppUser table in the database
type AppUser struct {
	UUID     uuid.UUID `gorm:"type:uuid;primaryKey"`
	Email    string    `gorm:"uniqueIndex;not null"`
	Password string    `gorm:"not null"`
}

// RegisteredSensor represents the model for the RegisteredSensor table in the database
type RegisteredSensor struct {
	SensorUUID uuid.UUID `gorm:"type:uuid;primaryKey"`
	Secret     string    `gorm:"type:text;not null"`
	UserUUID   uuid.UUID `gorm:"type:uuid"`
}

// SensorReading represents the model for the SensorReadings table in the database
type SensorReading struct {
	ID         uint      `gorm:"primaryKey"`
	SensorUUID uuid.UUID `gorm:"type:uuid"`
	SensorType string    `gorm:"type:text"`
	SensorName string    `gorm:"type:text"`
	UnixTime   int64     `gorm:"type:bigint"`
	UserUUID   uuid.UUID `gorm:"type:uuid;not null"`
	CreatedAt  time.Time `gorm:"autoCreateTime"`
	Value      float32   `gorm:"type:float"`
}

type LeasedJWTToken struct {
	UserUUID uuid.UUID `gorm:"type:uuid;primaryKey`
	JWTToken string    `gorm:"type:text"`
}
