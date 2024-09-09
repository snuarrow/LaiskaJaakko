package main

import (
	"encoding/json"
	"fmt"
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

func teardown(userEmail string) {
	if user, err := loadUserByEmail(userEmail); err != nil {
		deleteUserJWTTokens(user.UUID)
	}
	deleteUserByEmail(userEmail)
}
