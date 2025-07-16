package server

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"waddlebot-bridge/internal/testutils"
)

func TestNewWebServer(t *testing.T) {
	cfg := testutils.TestConfig()
	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	server := NewWebServer(cfg, authenticator, bridgeClient)

	if server == nil {
		t.Fatal("Expected non-nil server")
	}

	if server.config != cfg {
		t.Error("Expected config to be set")
	}

	if server.authenticator != authenticator {
		t.Error("Expected authenticator to be set")
	}

	if server.bridgeClient != bridgeClient {
		t.Error("Expected bridgeClient to be set")
	}

	if server.logger == nil {
		t.Error("Expected logger to be set")
	}
}

func TestWebServer_HandleIndex(t *testing.T) {
	cfg := testutils.TestConfig()
	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	server := NewWebServer(cfg, authenticator, bridgeClient)

	req := httptest.NewRequest("GET", "/", nil)
	w := httptest.NewRecorder()

	server.handleIndex(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	contentType := w.Header().Get("Content-Type")
	if contentType != "text/html" {
		t.Errorf("Expected Content-Type 'text/html', got %s", contentType)
	}

	body := w.Body.String()
	if !strings.Contains(body, "WaddleBot Premium Desktop Bridge") {
		t.Error("Expected body to contain title")
	}

	if !strings.Contains(body, cfg.APIURL) {
		t.Error("Expected body to contain API URL")
	}

	if !strings.Contains(body, fmt.Sprintf("%d", cfg.PollInterval)) {
		t.Error("Expected body to contain poll interval")
	}
}

func TestWebServer_HandleRegisterStart(t *testing.T) {
	cfg := testutils.TestConfig()
	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	server := NewWebServer(cfg, authenticator, bridgeClient)

	// Test valid request
	reqBody := map[string]string{
		"user_id":      "test-user",
		"community_id": "test-community",
	}
	reqJSON, _ := json.Marshal(reqBody)

	req := httptest.NewRequest("POST", "/auth/register/start", bytes.NewBuffer(reqJSON))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	server.handleRegisterStart(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	contentType := w.Header().Get("Content-Type")
	if contentType != "application/json" {
		t.Errorf("Expected Content-Type 'application/json', got %s", contentType)
	}

	var response map[string]interface{}
	err := json.NewDecoder(w.Body).Decode(&response)
	if err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if _, exists := response["credentialCreationOptions"]; !exists {
		t.Error("Expected credentialCreationOptions in response")
	}
}

func TestWebServer_HandleRegisterStart_InvalidRequest(t *testing.T) {
	cfg := testutils.TestConfig()
	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	server := NewWebServer(cfg, authenticator, bridgeClient)

	// Test invalid JSON
	req := httptest.NewRequest("POST", "/auth/register/start", bytes.NewBuffer([]byte("invalid json")))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	server.handleRegisterStart(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400, got %d", w.Code)
	}
}

func TestWebServer_HandleRegisterStart_RegistrationError(t *testing.T) {
	cfg := testutils.TestConfig()
	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	// Configure authenticator to return error
	authenticator.SetRegistrationError(true)

	server := NewWebServer(cfg, authenticator, bridgeClient)

	reqBody := map[string]string{
		"user_id":      "test-user",
		"community_id": "test-community",
	}
	reqJSON, _ := json.Marshal(reqBody)

	req := httptest.NewRequest("POST", "/auth/register/start", bytes.NewBuffer(reqJSON))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	server.handleRegisterStart(w, req)

	if w.Code != http.StatusInternalServerError {
		t.Errorf("Expected status 500, got %d", w.Code)
	}
}

func TestWebServer_HandleRegisterComplete(t *testing.T) {
	cfg := testutils.TestConfig()
	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	server := NewWebServer(cfg, authenticator, bridgeClient)

	// Test valid request
	reqBody := map[string]interface{}{
		"user_id": "test-user",
		"credential": map[string]interface{}{
			"id":   "test-credential-id",
			"type": "public-key",
		},
	}
	reqJSON, _ := json.Marshal(reqBody)

	req := httptest.NewRequest("POST", "/auth/register/complete", bytes.NewBuffer(reqJSON))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	server.handleRegisterComplete(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var response map[string]interface{}
	err := json.NewDecoder(w.Body).Decode(&response)
	if err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if success, exists := response["success"]; !exists || !success.(bool) {
		t.Error("Expected success to be true")
	}

	if _, exists := response["session_id"]; !exists {
		t.Error("Expected session_id in response")
	}
}

func TestWebServer_HandleRegisterComplete_InvalidRequest(t *testing.T) {
	cfg := testutils.TestConfig()
	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	server := NewWebServer(cfg, authenticator, bridgeClient)

	// Test invalid JSON
	req := httptest.NewRequest("POST", "/auth/register/complete", bytes.NewBuffer([]byte("invalid json")))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	server.handleRegisterComplete(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400, got %d", w.Code)
	}
}

func TestWebServer_HandleLoginStart(t *testing.T) {
	cfg := testutils.TestConfig()
	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	server := NewWebServer(cfg, authenticator, bridgeClient)

	// Test valid request
	reqBody := map[string]string{
		"user_id": "test-user",
	}
	reqJSON, _ := json.Marshal(reqBody)

	req := httptest.NewRequest("POST", "/auth/login/start", bytes.NewBuffer(reqJSON))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	server.handleLoginStart(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var response map[string]interface{}
	err := json.NewDecoder(w.Body).Decode(&response)
	if err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if _, exists := response["credentialRequestOptions"]; !exists {
		t.Error("Expected credentialRequestOptions in response")
	}
}

func TestWebServer_HandleLoginStart_InvalidRequest(t *testing.T) {
	cfg := testutils.TestConfig()
	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	server := NewWebServer(cfg, authenticator, bridgeClient)

	// Test invalid JSON
	req := httptest.NewRequest("POST", "/auth/login/start", bytes.NewBuffer([]byte("invalid json")))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	server.handleLoginStart(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400, got %d", w.Code)
	}
}

func TestWebServer_HandleLoginComplete(t *testing.T) {
	cfg := testutils.TestConfig()
	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	server := NewWebServer(cfg, authenticator, bridgeClient)

	// Test valid request
	reqBody := map[string]interface{}{
		"user_id": "test-user",
		"credential": map[string]interface{}{
			"id":   "test-credential-id",
			"type": "public-key",
		},
	}
	reqJSON, _ := json.Marshal(reqBody)

	req := httptest.NewRequest("POST", "/auth/login/complete", bytes.NewBuffer(reqJSON))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	server.handleLoginComplete(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var response map[string]interface{}
	err := json.NewDecoder(w.Body).Decode(&response)
	if err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if success, exists := response["success"]; !exists || !success.(bool) {
		t.Error("Expected success to be true")
	}

	if _, exists := response["session_id"]; !exists {
		t.Error("Expected session_id in response")
	}
}

func TestWebServer_HandleLoginComplete_InvalidRequest(t *testing.T) {
	cfg := testutils.TestConfig()
	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	server := NewWebServer(cfg, authenticator, bridgeClient)

	// Test invalid JSON
	req := httptest.NewRequest("POST", "/auth/login/complete", bytes.NewBuffer([]byte("invalid json")))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	server.handleLoginComplete(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400, got %d", w.Code)
	}
}

func TestWebServer_HandleLogout(t *testing.T) {
	cfg := testutils.TestConfig()
	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	server := NewWebServer(cfg, authenticator, bridgeClient)

	// Add a session
	authenticator.AddSession("test-session", "test-user", "test-community")

	req := httptest.NewRequest("POST", "/auth/logout", nil)
	w := httptest.NewRecorder()

	server.handleLogout(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var response map[string]interface{}
	err := json.NewDecoder(w.Body).Decode(&response)
	if err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if success, exists := response["success"]; !exists || !success.(bool) {
		t.Error("Expected success to be true")
	}
}

func TestWebServer_HandleLogout_NoSession(t *testing.T) {
	cfg := testutils.TestConfig()
	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	server := NewWebServer(cfg, authenticator, bridgeClient)

	req := httptest.NewRequest("POST", "/auth/logout", nil)
	w := httptest.NewRecorder()

	server.handleLogout(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var response map[string]interface{}
	err := json.NewDecoder(w.Body).Decode(&response)
	if err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if success, exists := response["success"]; !exists || !success.(bool) {
		t.Error("Expected success to be true even with no session")
	}
}

func TestWebServer_HandleStatus_Authenticated(t *testing.T) {
	cfg := testutils.TestConfig()
	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	server := NewWebServer(cfg, authenticator, bridgeClient)

	// Add a session
	authenticator.AddSession("test-session", "test-user", "test-community")

	req := httptest.NewRequest("GET", "/status", nil)
	w := httptest.NewRecorder()

	server.handleStatus(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var response map[string]interface{}
	err := json.NewDecoder(w.Body).Decode(&response)
	if err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if authenticated, exists := response["authenticated"]; !exists || !authenticated.(bool) {
		t.Error("Expected authenticated to be true")
	}

	if bridgeStatus, exists := response["bridge_status"]; !exists || bridgeStatus != "running" {
		t.Error("Expected bridge_status to be 'running'")
	}

	if userID, exists := response["user_id"]; !exists || userID != "test-user" {
		t.Error("Expected user_id to be 'test-user'")
	}

	if communityID, exists := response["community_id"]; !exists || communityID != "test-community" {
		t.Error("Expected community_id to be 'test-community'")
	}

	if _, exists := response["session_expires"]; !exists {
		t.Error("Expected session_expires to be present")
	}
}

func TestWebServer_HandleStatus_NotAuthenticated(t *testing.T) {
	cfg := testutils.TestConfig()
	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	server := NewWebServer(cfg, authenticator, bridgeClient)

	req := httptest.NewRequest("GET", "/status", nil)
	w := httptest.NewRecorder()

	server.handleStatus(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var response map[string]interface{}
	err := json.NewDecoder(w.Body).Decode(&response)
	if err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if authenticated, exists := response["authenticated"]; !exists || authenticated.(bool) {
		t.Error("Expected authenticated to be false")
	}

	if bridgeStatus, exists := response["bridge_status"]; !exists || bridgeStatus != "running" {
		t.Error("Expected bridge_status to be 'running'")
	}

	// These should not be present when not authenticated
	if _, exists := response["user_id"]; exists {
		t.Error("Expected user_id to not be present when not authenticated")
	}

	if _, exists := response["community_id"]; exists {
		t.Error("Expected community_id to not be present when not authenticated")
	}

	if _, exists := response["session_expires"]; exists {
		t.Error("Expected session_expires to not be present when not authenticated")
	}
}

func TestWebServer_HandleHealth(t *testing.T) {
	cfg := testutils.TestConfig()
	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	server := NewWebServer(cfg, authenticator, bridgeClient)

	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()

	server.handleHealth(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var response map[string]interface{}
	err := json.NewDecoder(w.Body).Decode(&response)
	if err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if status, exists := response["status"]; !exists || status != "healthy" {
		t.Error("Expected status to be 'healthy'")
	}

	if version, exists := response["version"]; !exists || version != "1.0.0" {
		t.Error("Expected version to be '1.0.0'")
	}

	if _, exists := response["timestamp"]; !exists {
		t.Error("Expected timestamp to be present")
	}
}

func TestWebServer_Start_Shutdown(t *testing.T) {
	cfg := testutils.TestConfig()
	cfg.WebPort = 0 // Use available port

	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	server := NewWebServer(cfg, authenticator, bridgeClient)

	// Start server with short-lived context
	ctx, cancel := context.WithTimeout(context.Background(), 1*time.Second)
	defer cancel()

	err := server.Start(ctx)
	if err != nil {
		t.Fatalf("Server start failed: %v", err)
	}

	// Server should have shut down gracefully
	if server.server == nil {
		t.Error("Expected server to be initialized")
	}
}

func TestWebServer_Routes(t *testing.T) {
	cfg := testutils.TestConfig()
	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	server := NewWebServer(cfg, authenticator, bridgeClient)

	// Test route setup by checking various endpoints
	testCases := []struct {
		method string
		path   string
		body   string
		expect int
	}{
		{"GET", "/", "", http.StatusOK},
		{"GET", "/health", "", http.StatusOK},
		{"GET", "/status", "", http.StatusOK},
		{"POST", "/auth/register/start", `{"user_id":"test","community_id":"test"}`, http.StatusOK},
		{"POST", "/auth/login/start", `{"user_id":"test"}`, http.StatusOK},
		{"POST", "/auth/logout", "", http.StatusOK},
		{"GET", "/nonexistent", "", http.StatusNotFound},
	}

	for _, tc := range testCases {
		t.Run(fmt.Sprintf("%s %s", tc.method, tc.path), func(t *testing.T) {
			var req *http.Request
			if tc.body != "" {
				req = httptest.NewRequest(tc.method, tc.path, strings.NewReader(tc.body))
				req.Header.Set("Content-Type", "application/json")
			} else {
				req = httptest.NewRequest(tc.method, tc.path, nil)
			}

			w := httptest.NewRecorder()

			// Create a temporary router to test routing
			router := http.NewServeMux()
			router.HandleFunc("/", server.handleIndex)
			router.HandleFunc("/health", server.handleHealth)
			router.HandleFunc("/status", server.handleStatus)
			router.HandleFunc("/auth/register/start", server.handleRegisterStart)
			router.HandleFunc("/auth/login/start", server.handleLoginStart)
			router.HandleFunc("/auth/logout", server.handleLogout)

			router.ServeHTTP(w, req)

			if w.Code != tc.expect {
				t.Errorf("Expected status %d, got %d", tc.expect, w.Code)
			}
		})
	}
}

func TestWebServer_ContentTypes(t *testing.T) {
	cfg := testutils.TestConfig()
	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	server := NewWebServer(cfg, authenticator, bridgeClient)

	testCases := []struct {
		handler     func(w http.ResponseWriter, r *http.Request)
		path        string
		method      string
		body        string
		contentType string
	}{
		{server.handleIndex, "/", "GET", "", "text/html"},
		{server.handleHealth, "/health", "GET", "", "application/json"},
		{server.handleStatus, "/status", "GET", "", "application/json"},
		{server.handleRegisterStart, "/auth/register/start", "POST", `{"user_id":"test","community_id":"test"}`, "application/json"},
		{server.handleLoginStart, "/auth/login/start", "POST", `{"user_id":"test"}`, "application/json"},
		{server.handleLogout, "/auth/logout", "POST", "", "application/json"},
	}

	for _, tc := range testCases {
		t.Run(fmt.Sprintf("%s %s", tc.method, tc.path), func(t *testing.T) {
			var req *http.Request
			if tc.body != "" {
				req = httptest.NewRequest(tc.method, tc.path, strings.NewReader(tc.body))
				req.Header.Set("Content-Type", "application/json")
			} else {
				req = httptest.NewRequest(tc.method, tc.path, nil)
			}

			w := httptest.NewRecorder()
			tc.handler(w, req)

			contentType := w.Header().Get("Content-Type")
			if contentType != tc.contentType {
				t.Errorf("Expected Content-Type '%s', got '%s'", tc.contentType, contentType)
			}
		})
	}
}

func TestWebServer_AuthenticationFlow(t *testing.T) {
	cfg := testutils.TestConfig()
	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	server := NewWebServer(cfg, authenticator, bridgeClient)

	// Test complete authentication flow
	// 1. Start registration
	regStartReq := map[string]string{
		"user_id":      "test-user",
		"community_id": "test-community",
	}
	regStartJSON, _ := json.Marshal(regStartReq)

	req := httptest.NewRequest("POST", "/auth/register/start", bytes.NewBuffer(regStartJSON))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	server.handleRegisterStart(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("Register start failed: %d", w.Code)
	}

	// 2. Complete registration
	regCompleteReq := map[string]interface{}{
		"user_id": "test-user",
		"credential": map[string]interface{}{
			"id":   "test-credential-id",
			"type": "public-key",
		},
	}
	regCompleteJSON, _ := json.Marshal(regCompleteReq)

	req = httptest.NewRequest("POST", "/auth/register/complete", bytes.NewBuffer(regCompleteJSON))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()

	server.handleRegisterComplete(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("Register complete failed: %d", w.Code)
	}

	// 3. Check status (should be authenticated)
	req = httptest.NewRequest("GET", "/status", nil)
	w = httptest.NewRecorder()

	server.handleStatus(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("Status check failed: %d", w.Code)
	}

	var statusResponse map[string]interface{}
	err := json.NewDecoder(w.Body).Decode(&statusResponse)
	if err != nil {
		t.Fatalf("Failed to decode status response: %v", err)
	}

	if authenticated, exists := statusResponse["authenticated"]; !exists || !authenticated.(bool) {
		t.Error("Expected to be authenticated after registration")
	}

	// 4. Logout
	req = httptest.NewRequest("POST", "/auth/logout", nil)
	w = httptest.NewRecorder()

	server.handleLogout(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("Logout failed: %d", w.Code)
	}

	// 5. Check status (should not be authenticated)
	req = httptest.NewRequest("GET", "/status", nil)
	w = httptest.NewRecorder()

	server.handleStatus(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("Status check failed: %d", w.Code)
	}

	err = json.NewDecoder(w.Body).Decode(&statusResponse)
	if err != nil {
		t.Fatalf("Failed to decode status response: %v", err)
	}

	if authenticated, exists := statusResponse["authenticated"]; !exists || authenticated.(bool) {
		t.Error("Expected to not be authenticated after logout")
	}
}