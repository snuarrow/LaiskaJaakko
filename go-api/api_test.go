package main

import (
	"fmt"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"
)

func TestPingRoute(t *testing.T) {
	r := setupRouter()
	req, _ := http.NewRequest("GET", "/ping", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
	assert.Equal(t, "{\"status\":\"ok\"}", w.Body.String())
}

func TestHealthRoute(t *testing.T) {
	setupDBConnection()
	r := setupRouter()
	req, _ := http.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
	assert.Equal(t, "{\"status\":\"healthy\"}", w.Body.String())
}

func TestSignupRoute(t *testing.T) {
	r := setupRouter()
	userEmail := "user@example.com"
	userPassword := "securepassword"
	jsonBody := fmt.Sprintf(`{"email": "%s", "password": "%s"}`, userEmail, userPassword)
	req, _ := http.NewRequest("POST", "/signup", strings.NewReader(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("ADMIN_SECRET", os.Getenv("ADMIN_SECRET"))
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusCreated, w.Code)
	assert.Equal(t, "{\"message\":\"user created successfully\"}", w.Body.String())
	teardown(userEmail)
}

func TestLogin(t *testing.T) {
	_, userEmail, _ := setupWithLogin(t)
	teardown(userEmail)
}

func TestLoginInvalidPasswordFail(t *testing.T) {
	router, userEmail, _ := setup(t)
	userPassword := "invalid_password"
	jsonBody := fmt.Sprintf(`{"email": "%s", "password": "%s"}`, userEmail, userPassword)
	req, _ := http.NewRequest("POST", "/login", strings.NewReader(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
	assert.Contains(t, "{\"error\":\"invalid credentials\"}", w.Body.String())
	teardown(userEmail)
}

func TestLoginInvalidUserEmailFail(t *testing.T) {
	router, _, userPassword := setup(t)
	userEmail := "invaliduser@example.com"
	jsonBody := fmt.Sprintf(`{"email": "%s", "password": "%s"}`, userEmail, userPassword)
	req, _ := http.NewRequest("POST", "/login", strings.NewReader(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
	assert.Contains(t, w.Body.String(), "{\"error\":\"invalid credentials\"}")
	teardown(userEmail)
}

func TestProtectedRoute(t *testing.T) {
	router, userEmail, token := setupWithLogin(t)
	req, _ := http.NewRequest("GET", "/protected", nil)
	req.Header.Set("Authorization", token)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
	assert.Equal(t, "{\"message\":\"protected resource\"}", w.Body.String())
	teardown(userEmail)
}

func TestProtectedRouteInvalidTokenFail(t *testing.T) {
	router, userEmail, token := setupWithLogin(t)
	token = "invalid"
	req, _ := http.NewRequest("GET", "/protected", nil)
	req.Header.Set("Authorization", token)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
	assert.Equal(t, "{\"error\":\"invalid token\"}", w.Body.String())
	teardown(userEmail)
}

func TestLogoutRoute(t *testing.T) {
	router, userEmail, token := setupWithLogin(t)
	req, _ := http.NewRequest("POST", "/logout", nil)
	req.Header.Set("Authorization", token)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
	assert.Equal(t, "{\"message\":\"logged out\"}", w.Body.String())

	// after logging out, test restricted access to /protected
	req, _ = http.NewRequest("GET", "/protected", nil)
	req.Header.Set("Authorization", token)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
	assert.Equal(t, "{\"error\":\"invalid token\"}", w.Body.String())
	teardown(userEmail)
}

func TestRegisterSensorRoute(t *testing.T) {
	router, userEmail, _ := setup(t)
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
	deleteRegisteredSensor(sensorUUID)
	teardown(userEmail)
}

func TestRegisterSensorRouteWithoutUser(t *testing.T) {
	setupDBConnection()
	createDBTables()
	router := setupRouter()
	sensorUUIDstr := "2ca3c5d2-059b-406c-ac9d-2100b4396390"
	sensorSecret := "LzD6eh8L4pPPxgR0IlBZrmNg+/dzaOlbtiiIfKTJgfCR7lTMVnyoRcJZQG5z7o2d"
	jsonBody := fmt.Sprintf(`{"SensorUUID": "%s", "SensorSecret": "%s"}`, sensorUUIDstr, sensorSecret)
	req, _ := http.NewRequest("POST", "/register_sensor", strings.NewReader(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("ADMIN_SECRET", os.Getenv("ADMIN_SECRET"))
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusCreated, w.Code)
	assert.Equal(t, "{\"message\":\"sensor registered successfully\"}", w.Body.String())
	sensorUUID, _ := uuid.Parse(sensorUUIDstr)
	deleteRegisteredSensor(sensorUUID)
}

func TestRegisterSensorRouteFailWithoutAdminSecret(t *testing.T) {
	setupDBConnection()
	createDBTables()
	router := setupRouter()
	sensorUUIDstr := "2ca3c5d2-059b-406c-ac9d-2100b4396390"
	sensorSecret := "LzD6eh8L4pPPxgR0IlBZrmNg+/dzaOlbtiiIfKTJgfCR7lTMVnyoRcJZQG5z7o2d"
	jsonBody := fmt.Sprintf(`{"SensorUUID": "%s", "SensorSecret": "%s"}`, sensorUUIDstr, sensorSecret)
	req, _ := http.NewRequest("POST", "/register_sensor", strings.NewReader(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
	assert.Equal(t, "{\"error\":\"unauthorized\"}", w.Body.String())
	sensorUUID, _ := uuid.Parse(sensorUUIDstr)
	deleteRegisteredSensor(sensorUUID)
}

func TestRegisterSensorRouteFailInvalidAdminSecret(t *testing.T) {
	setupDBConnection()
	createDBTables()
	router := setupRouter()
	sensorUUIDstr := "2ca3c5d2-059b-406c-ac9d-2100b4396390"
	sensorSecret := "LzD6eh8L4pPPxgR0IlBZrmNg+/dzaOlbtiiIfKTJgfCR7lTMVnyoRcJZQG5z7o2d"
	jsonBody := fmt.Sprintf(`{"SensorUUID": "%s", "SensorSecret": "%s"}`, sensorUUIDstr, sensorSecret)
	req, _ := http.NewRequest("POST", "/register_sensor", strings.NewReader(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("ADMIN_SECRET", "INVALID_ADMIN_SECRET")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
	assert.Equal(t, "{\"error\":\"unauthorized\"}", w.Body.String())
	sensorUUID, _ := uuid.Parse(sensorUUIDstr)
	deleteRegisteredSensor(sensorUUID)
}

func TestSensorDataRoute(t *testing.T) {
	router, userEmail, _, sensorUUID, sensorSecret := setupWithRegistedSensorAndUser(t)
	sensorType := "MH-Moisture"
	sensorName := "Kääpiövuorimänty"
	unixTime := time.Now().Unix()
	jsonBody := fmt.Sprintf(`{
		"sensorUUID": "%s",
		"sensorType": "%s",
		"sensorName": "%s",
		"unixTime": %d,
		"email": "%s",
		"value": 47.6
	}`, sensorUUID, sensorType, sensorName, unixTime, userEmail)
	req, _ := http.NewRequest("POST", "/sensor_data", strings.NewReader(jsonBody))
	req.Header.Set("SENSOR_SECRET", sensorSecret)
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusCreated, w.Code)
	assert.Equal(t, "{\"message\":\"sensor data registered successfully\"}", w.Body.String())
	deleteRegisteredSensor(sensorUUID)
	teardown(userEmail)
}

func TestSensorDataRouteFailWithInvalidSensorSecret(t *testing.T) {
	router, userEmail, _, sensorUUID, _ := setupWithRegistedSensorAndUser(t)
	sensorType := "MH-Moisture"
	sensorName := "Kääpiövuorimänty"
	unixTime := time.Now().Unix()
	jsonBody := fmt.Sprintf(`{
		"sensorUUID": "%s",
		"sensorType": "%s",
		"sensorName": "%s",
		"unixTime": %d,
		"email": "%s",
		"value": 47.6
	}`, sensorUUID, sensorType, sensorName, unixTime, userEmail)
	req, _ := http.NewRequest("POST", "/sensor_data", strings.NewReader(jsonBody))
	req.Header.Set("SENSOR_SECRET", "INVALID_SENSOR_SECRET")
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
	assert.Equal(t, "{\"error\":\"unauthorized\"}", w.Body.String())
	deleteRegisteredSensor(sensorUUID)
	teardown(userEmail)
}
