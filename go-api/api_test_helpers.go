package main

import (
	"encoding/json"
	"fmt"
	"github.com/google/uuid"
	"log"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
)

func setup(t *testing.T) (*gin.Engine, string, string) {
	gin.SetMode(gin.TestMode)
	setupDBConnection()
	createDBTables()
	userEmail := "user@example.com"
	userPassword := "securepassword"
	teardown(userEmail)
	router := setupRouter()
	jsonBody := fmt.Sprintf(`{"email": "%s", "password": "%s"}`, userEmail, userPassword)
	req, _ := http.NewRequest("POST", "/signup", strings.NewReader(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("ADMIN_SECRET", os.Getenv("ADMIN_SECRET"))
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusCreated, w.Code)
	assert.Equal(t, "{\"message\":\"user created successfully\"}", w.Body.String())
	return router, userEmail, userPassword
}

func setupWithLogin(t *testing.T) (*gin.Engine, string, string) {
	router, userEmail, userPassword := setup(t)
	jsonBody := fmt.Sprintf(`{"email": "%s", "password": "%s"}`, userEmail, userPassword)
	req, _ := http.NewRequest("POST", "/login", strings.NewReader(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
	assert.Contains(t, w.Body.String(), "token")
	type Response struct {
		Token string `json:"token"`
	}
	var response Response
	jsonBytes := []byte(w.Body.String())
	err := json.Unmarshal(jsonBytes, &response)
	if err != nil {
		log.Fatalf("Error parsing JSON: %v", err)
	}
	return router, userEmail, response.Token
}

func setupWithRegistedSensorAndUser(t *testing.T) (*gin.Engine, string, string, uuid.UUID, string) {
	router, userEmail, userPassword := setupWithLogin(t)
	sensorUUIDstr := "2ca3c5d2-059b-406c-ac9d-2100b4396390"
	sensorSecret := "LzD6eh8L4pPPxgR0IlBZrmNg+/dzaOlbtiiIfKTJgfCR7lTMVnyoRcJZQG5z7o2d"
	jsonBody := fmt.Sprintf(`{"SensorUUID": "%s", "SensorSecret": "%s", "email": "%s"}`, sensorUUIDstr, sensorSecret, userEmail)
	req, _ := http.NewRequest("POST", "/register_sensor", strings.NewReader(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("ADMIN_SECRET", os.Getenv("ADMIN_SECRET"))
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusCreated, w.Code)
	assert.Equal(t, "{\"message\":\"sensor registered successfully\"}", w.Body.String())
	sensorUUID, _ := uuid.Parse(sensorUUIDstr)
	return router, userEmail, userPassword, sensorUUID, sensorSecret
}

func teardown(userEmail string) {
	if user, err := loadUserByEmail(userEmail); err != nil {
		deleteUserJWTTokens(user.UUID)
	}
	deleteUserByEmail(userEmail)
}
