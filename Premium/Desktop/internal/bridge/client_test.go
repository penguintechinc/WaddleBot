package bridge

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"waddlebot-bridge/internal/testutils"
)

func TestNewClient(t *testing.T) {
	cfg := testutils.TestConfig()
	auth := testutils.NewMockWebAuthnManager()
	moduleManager := testutils.NewMockModuleManager()
	
	client, err := NewClient(cfg, auth, moduleManager)
	if err != nil {
		t.Fatalf("NewClient failed: %v", err)
	}
	
	if client == nil {
		t.Fatal("Expected non-nil client")
	}
	
	if client.config != cfg {
		t.Error("Expected config to be set")
	}
	
	if client.authenticator != auth {
		t.Error("Expected authenticator to be set")
	}
	
	if client.moduleManager != moduleManager {
		t.Error("Expected moduleManager to be set")
	}
}

func TestClient_GetAuthToken(t *testing.T) {
	cfg := testutils.TestConfig()
	auth := testutils.NewMockWebAuthnManager()
	moduleManager := testutils.NewMockModuleManager()
	
	client, err := NewClient(cfg, auth, moduleManager)
	if err != nil {
		t.Fatalf("NewClient failed: %v", err)
	}
	
	// Test without session
	_, err = client.GetAuthToken()
	if err == nil {
		t.Error("Expected error for no session")
	}
	
	// Add a mock session
	auth.AddSession("test-session", "test-user", "test-community")
	
	// Test with session
	token, err := client.GetAuthToken()
	if err != nil {
		t.Fatalf("GetAuthToken failed: %v", err)
	}
	
	if token == "" {
		t.Error("Expected non-empty token")
	}
}

func TestClient_RegisterBridge(t *testing.T) {
	// Create test server
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/bridge/register" {
			t.Errorf("Expected path '/api/bridge/register', got %s", r.URL.Path)
		}
		
		if r.Method != "POST" {
			t.Errorf("Expected method POST, got %s", r.Method)
		}
		
		// Check headers
		if r.Header.Get("Authorization") == "" {
			t.Error("Expected Authorization header")
		}
		
		if r.Header.Get("Content-Type") != "application/json" {
			t.Error("Expected Content-Type application/json")
		}
		
		// Return success response
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{
			"success": true,
			"bridge_id": "test-bridge-id",
			"message": "Registration successful",
			"poll_interval": 30
		}`))
	}))
	defer server.Close()
	
	cfg := testutils.TestConfig()
	cfg.APIURL = server.URL
	auth := testutils.NewMockWebAuthnManager()
	moduleManager := testutils.NewMockModuleManager()
	
	// Add a mock session
	auth.AddSession("test-session", "test-user", "test-community")
	
	client, err := NewClient(cfg, auth, moduleManager)
	if err != nil {
		t.Fatalf("NewClient failed: %v", err)
	}
	
	// Test successful registration
	ctx, cancel := testutils.TestContext()
	defer cancel()
	
	err = client.RegisterBridge(ctx)
	if err != nil {
		t.Fatalf("RegisterBridge failed: %v", err)
	}
}

func TestClient_RegisterBridge_Failure(t *testing.T) {
	// Create test server that returns error
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte("Internal server error"))
	}))
	defer server.Close()
	
	cfg := testutils.TestConfig()
	cfg.APIURL = server.URL
	auth := testutils.NewMockWebAuthnManager()
	moduleManager := testutils.NewMockModuleManager()
	
	// Add a mock session
	auth.AddSession("test-session", "test-user", "test-community")
	
	client, err := NewClient(cfg, auth, moduleManager)
	if err != nil {
		t.Fatalf("NewClient failed: %v", err)
	}
	
	// Test registration failure
	ctx, cancel := testutils.TestContext()
	defer cancel()
	
	err = client.RegisterBridge(ctx)
	if err == nil {
		t.Error("Expected error for registration failure")
	}
}

func TestClient_SendHeartbeat(t *testing.T) {
	// Create test server
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/bridge/heartbeat" {
			t.Errorf("Expected path '/api/bridge/heartbeat', got %s", r.URL.Path)
		}
		
		if r.Method != "POST" {
			t.Errorf("Expected method POST, got %s", r.Method)
		}
		
		// Check headers
		if r.Header.Get("Authorization") == "" {
			t.Error("Expected Authorization header")
		}
		
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()
	
	cfg := testutils.TestConfig()
	cfg.APIURL = server.URL
	auth := testutils.NewMockWebAuthnManager()
	moduleManager := testutils.NewMockModuleManager()
	
	// Add a mock session
	auth.AddSession("test-session", "test-user", "test-community")
	
	client, err := NewClient(cfg, auth, moduleManager)
	if err != nil {
		t.Fatalf("NewClient failed: %v", err)
	}
	
	// Test successful heartbeat
	ctx, cancel := testutils.TestContext()
	defer cancel()
	
	err = client.SendHeartbeat(ctx)
	if err != nil {
		t.Fatalf("SendHeartbeat failed: %v", err)
	}
}

func TestClient_GetBridgeInfo(t *testing.T) {
	// Create test server
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/bridge/info" {
			t.Errorf("Expected path '/api/bridge/info', got %s", r.URL.Path)
		}
		
		if r.Method != "GET" {
			t.Errorf("Expected method GET, got %s", r.Method)
		}
		
		// Return bridge info
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{
			"bridge_id": "test-bridge-id",
			"user_id": "test-user",
			"community_id": "test-community",
			"status": "active",
			"version": "1.0.0",
			"platform": "test-platform",
			"last_seen": "2024-01-01T00:00:00Z",
			"capabilities": ["local_execution", "file_operations"]
		}`))
	}))
	defer server.Close()
	
	cfg := testutils.TestConfig()
	cfg.APIURL = server.URL
	auth := testutils.NewMockWebAuthnManager()
	moduleManager := testutils.NewMockModuleManager()
	
	// Add a mock session
	auth.AddSession("test-session", "test-user", "test-community")
	
	client, err := NewClient(cfg, auth, moduleManager)
	if err != nil {
		t.Fatalf("NewClient failed: %v", err)
	}
	
	// Test getting bridge info
	ctx, cancel := testutils.TestContext()
	defer cancel()
	
	info, err := client.GetBridgeInfo(ctx)
	if err != nil {
		t.Fatalf("GetBridgeInfo failed: %v", err)
	}
	
	if info.BridgeID != "test-bridge-id" {
		t.Errorf("Expected bridge ID 'test-bridge-id', got %s", info.BridgeID)
	}
	
	if info.UserID != "test-user" {
		t.Errorf("Expected user ID 'test-user', got %s", info.UserID)
	}
	
	if info.CommunityID != "test-community" {
		t.Errorf("Expected community ID 'test-community', got %s", info.CommunityID)
	}
	
	if info.Status != "active" {
		t.Errorf("Expected status 'active', got %s", info.Status)
	}
}

func TestClient_UnregisterBridge(t *testing.T) {
	// Create test server
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/bridge/unregister" {
			t.Errorf("Expected path '/api/bridge/unregister', got %s", r.URL.Path)
		}
		
		if r.Method != "POST" {
			t.Errorf("Expected method POST, got %s", r.Method)
		}
		
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()
	
	cfg := testutils.TestConfig()
	cfg.APIURL = server.URL
	auth := testutils.NewMockWebAuthnManager()
	moduleManager := testutils.NewMockModuleManager()
	
	// Add a mock session
	auth.AddSession("test-session", "test-user", "test-community")
	
	client, err := NewClient(cfg, auth, moduleManager)
	if err != nil {
		t.Fatalf("NewClient failed: %v", err)
	}
	
	// Test successful unregistration
	ctx, cancel := testutils.TestContext()
	defer cancel()
	
	err = client.UnregisterBridge(ctx)
	if err != nil {
		t.Fatalf("UnregisterBridge failed: %v", err)
	}
}

func TestClient_IsAuthenticated(t *testing.T) {
	cfg := testutils.TestConfig()
	auth := testutils.NewMockWebAuthnManager()
	moduleManager := testutils.NewMockModuleManager()
	
	client, err := NewClient(cfg, auth, moduleManager)
	if err != nil {
		t.Fatalf("NewClient failed: %v", err)
	}
	
	// Test without session
	if client.IsAuthenticated() {
		t.Error("Expected false for no session")
	}
	
	// Add a mock session
	auth.AddSession("test-session", "test-user", "test-community")
	
	// Test with session
	if !client.IsAuthenticated() {
		t.Error("Expected true for existing session")
	}
}

func TestClient_GetStats(t *testing.T) {
	cfg := testutils.TestConfig()
	auth := testutils.NewMockWebAuthnManager()
	moduleManager := testutils.NewMockModuleManager()
	
	client, err := NewClient(cfg, auth, moduleManager)
	if err != nil {
		t.Fatalf("NewClient failed: %v", err)
	}
	
	stats := client.GetStats()
	
	if stats == nil {
		t.Fatal("Expected non-nil stats")
	}
	
	// Check required fields
	if stats["user_id"] != cfg.UserID {
		t.Errorf("Expected user_id %s, got %v", cfg.UserID, stats["user_id"])
	}
	
	if stats["community_id"] != cfg.CommunityID {
		t.Errorf("Expected community_id %s, got %v", cfg.CommunityID, stats["community_id"])
	}
	
	if stats["api_url"] != cfg.APIURL {
		t.Errorf("Expected api_url %s, got %v", cfg.APIURL, stats["api_url"])
	}
	
	if stats["authenticated"] != false {
		t.Errorf("Expected authenticated false, got %v", stats["authenticated"])
	}
}

func TestClient_RequestTimeout(t *testing.T) {
	// Create test server that delays response
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(2 * time.Second)
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()
	
	cfg := testutils.TestConfig()
	cfg.APIURL = server.URL
	auth := testutils.NewMockWebAuthnManager()
	moduleManager := testutils.NewMockModuleManager()
	
	// Add a mock session
	auth.AddSession("test-session", "test-user", "test-community")
	
	client, err := NewClient(cfg, auth, moduleManager)
	if err != nil {
		t.Fatalf("NewClient failed: %v", err)
	}
	
	// Test request timeout
	ctx, cancel := context.WithTimeout(context.Background(), 1*time.Second)
	defer cancel()
	
	err = client.SendHeartbeat(ctx)
	if err == nil {
		t.Error("Expected timeout error")
	}
}

func TestClient_InvalidJSON(t *testing.T) {
	// Create test server that returns invalid JSON
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("invalid json"))
	}))
	defer server.Close()
	
	cfg := testutils.TestConfig()
	cfg.APIURL = server.URL
	auth := testutils.NewMockWebAuthnManager()
	moduleManager := testutils.NewMockModuleManager()
	
	// Add a mock session
	auth.AddSession("test-session", "test-user", "test-community")
	
	client, err := NewClient(cfg, auth, moduleManager)
	if err != nil {
		t.Fatalf("NewClient failed: %v", err)
	}
	
	// Test invalid JSON response
	ctx, cancel := testutils.TestContext()
	defer cancel()
	
	_, err = client.GetBridgeInfo(ctx)
	if err == nil {
		t.Error("Expected error for invalid JSON")
	}
}

func TestClient_AuthorizationHeader(t *testing.T) {
	// Create test server to check authorization header
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		authHeader := r.Header.Get("Authorization")
		if authHeader == "" {
			t.Error("Expected Authorization header")
		}
		
		if !strings.HasPrefix(authHeader, "Bearer ") {
			t.Errorf("Expected Bearer token, got %s", authHeader)
		}
		
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()
	
	cfg := testutils.TestConfig()
	cfg.APIURL = server.URL
	auth := testutils.NewMockWebAuthnManager()
	moduleManager := testutils.NewMockModuleManager()
	
	// Add a mock session
	auth.AddSession("test-session", "test-user", "test-community")
	
	client, err := NewClient(cfg, auth, moduleManager)
	if err != nil {
		t.Fatalf("NewClient failed: %v", err)
	}
	
	// Test authorization header
	ctx, cancel := testutils.TestContext()
	defer cancel()
	
	err = client.SendHeartbeat(ctx)
	if err != nil {
		t.Fatalf("SendHeartbeat failed: %v", err)
	}
}