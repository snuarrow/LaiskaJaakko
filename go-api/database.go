package main

import (
	"fmt"
	"github.com/joho/godotenv"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"log"
	"os"

	"github.com/google/uuid"
)

var db *gorm.DB

func setupDBConnection() {
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
}

func createDBTables() {
	if err := db.AutoMigrate(
		&AppUser{},
		&RegisteredSensor{},
		&SensorReading{},
		&LeasedJWTToken{},
	); err != nil {
		log.Fatal("Error auto-migrating tables:", err)
	}
}

func createUser(email string, hashedPassword string) error {
	user := AppUser{
		UUID:     uuid.New(),
		Email:    email,
		Password: hashedPassword,
	}
	if err := db.Create(&user).Error; err != nil {
		return err
	}
	return nil
}

func deleteUserByEmail(email string) error {
	result := db.Where("email = ?", email).Delete(&AppUser{})
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return fmt.Errorf("no user found with email: %s", email)
	}
	return nil
}

func loadUserByEmail(email string) (AppUser, error) {
	var user AppUser
	if err := db.Where("email = ?", email).First(&user).Error; err != nil {
		return user, err
	}
	return user, nil
}

func storeUserJWTToken(userUUID uuid.UUID, JWTToken string) error {
	leasedJWTToken := LeasedJWTToken{
		UserUUID: userUUID,
		JWTToken: JWTToken,
	}
	if err := db.Create(&leasedJWTToken).Error; err != nil {
		return err
	}
	return nil
}

func userJWTExists(userUUID uuid.UUID, JWTToken string) error {
	var leasedJWTToken LeasedJWTToken
	if err := db.Where("user_uuid = ? AND jwt_token = ?", userUUID, JWTToken).First(&leasedJWTToken).Error; err != nil {
		return err
	}
	return nil
}

func deleteUserJWTTokens(userUUID uuid.UUID) error {
	result := db.Where("user_uuid = ?", userUUID).Delete(&LeasedJWTToken{})
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return fmt.Errorf("no login session for user found")
	}
	return nil
}

func registerSensor(sensorUUID uuid.UUID, sensorSecret string, userUUID uuid.UUID) error {
	sensor := RegisteredSensor{
		SensorUUID: sensorUUID,
		Secret:     sensorSecret,
		UserUUID:   userUUID,
	}
	if err := db.Create(&sensor).Error; err != nil {
		return err
	}
	return nil
}

func registerSensorWithoutUser(sensorUUID uuid.UUID, sensorSecret string) error {
	sensor := RegisteredSensor{
		SensorUUID: sensorUUID,
		Secret:     sensorSecret,
	}
	if err := db.Create(&sensor).Error; err != nil {
		return err
	}
	return nil
}

func deleteRegisteredSensor(sensorUUID uuid.UUID) error {
	result := db.Where("sensor_uuid = ?", sensorUUID).Delete(&RegisteredSensor{})
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return fmt.Errorf("no sensor found with uuid: %s", sensorUUID)
	}
	return nil
}
