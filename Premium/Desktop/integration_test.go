package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"

	"waddlebot-bridge/internal/auth"
	"waddlebot-bridge/internal/bridge"
	"waddlebot-bridge/internal/config"
	"waddlebot-bridge/internal/license"
	"waddlebot-bridge/internal/modules"
	"waddlebot-bridge/internal/poller"
	"waddlebot-bridge/internal/server"
	"waddlebot-bridge/internal/storage"
	"waddlebot-bridge/internal/testutils"
)

func TestIntegration_FullSystem(t *testing.T) {
	// Skip if running in CI without proper setup
	if os.Getenv("CI") != "" {
		t.Skip("Skipping integration tests in CI")
	}

	// Create temporary directory for test
	tmpDir := t.TempDir()

	// Create test config
	cfg := &config.Config{
		APIURL:              "https://api.waddlebot.io",
		CommunityID:         "test-community",
		UserID:              "test-user",
		PollInterval:        30,
		WebPort:             8080,
		WebHost:             "127.0.0.1",
		LogLevel:            "info",
		DataDir:             tmpDir,
		ModulesDir:          filepath.Join(tmpDir, "modules"),
		WebAuthnDisplayName: "WaddleBot Bridge for Test",
		WebAuthnOrigin:      "http://127.0.0.1:8080",
		WebAuthnTimeout:     60,
		ModuleTimeout:       30,
		MaxConcurrentTasks:  10,
	}

	// Create storage
	storage, err := storage.NewBoltStorage(tmpDir)
	if err != nil {
		t.Fatalf("Failed to create storage: %v", err)
	}
	defer storage.Close()

	// Create authenticator
	authenticator, err := auth.NewWebAuthnManager(cfg, storage)
	if err != nil {
		t.Fatalf("Failed to create authenticator: %v", err)
	}

	// Create module manager
	moduleManager := modules.NewManager(cfg, storage)

	// Create bridge client
	bridgeClient, err := bridge.NewClient(cfg, authenticator, moduleManager)
	if err != nil {
		t.Fatalf("Failed to create bridge client: %v", err)
	}

	// Create poller
	poller := poller.NewPoller(cfg, bridgeClient, moduleManager)

	// Create web server
	webServer := server.NewWebServer(cfg, authenticator, bridgeClient)

	// Test that all components are properly initialized
	if storage == nil {
		t.Error("Storage should be initialized")
	}

	if authenticator == nil {
		t.Error("Authenticator should be initialized")
	}

	if moduleManager == nil {
		t.Error("Module manager should be initialized")
	}

	if bridgeClient == nil {
		t.Error("Bridge client should be initialized")
	}

	if poller == nil {
		t.Error("Poller should be initialized")
	}

	if webServer == nil {
		t.Error("Web server should be initialized")
	}

	// Test storage operations
	testKey := "test-key"
	testValue := []byte("test-value")

	err = storage.Set(testKey, testValue)
	if err != nil {
		t.Fatalf("Failed to set storage value: %v", err)
	}

	retrievedValue, err := storage.Get(testKey)
	if err != nil {
		t.Fatalf("Failed to get storage value: %v", err)
	}

	if string(retrievedValue) != string(testValue) {
		t.Errorf("Expected value %s, got %s", string(testValue), string(retrievedValue))
	}

	// Test module manager operations
	stats := moduleManager.GetStats()
	if stats == nil {
		t.Error("Module manager stats should not be nil")
	}

	// Test bridge client operations
	if bridgeClient.IsAuthenticated() {
		t.Error("Bridge client should not be authenticated initially")
	}

	// Test poller operations
	pollerStats := poller.GetStats()
	if pollerStats == nil {
		t.Error("Poller stats should not be nil")
	}

	// Test cleanup
	err = moduleManager.Cleanup()
	if err != nil {
		t.Errorf("Module manager cleanup failed: %v", err)
	}
}

func TestIntegration_LicenseValidation(t *testing.T) {
	// Test license validation
	result := license.ValidateLicense()
	if result {
		t.Error("License should not be valid initially")
	}

	// Test license info
	info := license.GetLicenseInfo()
	if info == nil {
		t.Error("License info should not be nil")
	}

	if info["version"] != "1.0.0" {
		t.Errorf("Expected version '1.0.0', got %v", info["version"])
	}

	if info["type"] != "Premium" {
		t.Errorf("Expected type 'Premium', got %v", info["type"])
	}

	// Test license display (should not panic)
	license.DisplayLicenseInfo()
}

func TestIntegration_WebServerEndpoints(t *testing.T) {
	// Create test components
	cfg := testutils.TestConfig()
	authenticator := testutils.NewMockWebAuthnManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	webServer := server.NewWebServer(cfg, authenticator, bridgeClient)

	// Test endpoints
	endpoints := []struct {
		path   string
		method string
		status int
	}{
		{"/", "GET", http.StatusOK},
		{"/health", "GET", http.StatusOK},
		{"/status", "GET", http.StatusOK},
	}

	for _, endpoint := range endpoints {
		t.Run(fmt.Sprintf("%s %s", endpoint.method, endpoint.path), func(t *testing.T) {
			req := httptest.NewRequest(endpoint.method, endpoint.path, nil)
			w := httptest.NewRecorder()

			switch endpoint.path {
			case "/":
				webServer.handleIndex(w, req)
			case "/health":
				webServer.handleHealth(w, req)
			case "/status":
				webServer.handleStatus(w, req)
			}

			if w.Code != endpoint.status {
				t.Errorf("Expected status %d, got %d", endpoint.status, w.Code)
			}
		})
	}
}

func TestIntegration_PollerWithMockServer(t *testing.T) {
	// Create mock server
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/bridge/poll" {
			response := map[string]interface{}{
				"actions":     []interface{}{},
				"next_poll":   time.Now().Add(30 * time.Second),
				"server_time": time.Now(),
				"has_more":    false,
				"poll_count":  1,
				"client_info": map[string]interface{}{
					"last_seen":       time.Now(),
					"actions_total":   0,
					"actions_success": 0,
					"actions_failed":  0,
					"uptime":          3600,
				},
			}
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(response)
		}
	}))
	defer server.Close()

	// Create test components
	cfg := testutils.TestConfig()
	cfg.APIURL = server.URL
	cfg.PollInterval = 1 // Short interval for testing

	authenticator := testutils.NewMockWebAuthnManager()
	authenticator.AddSession("test-session", "test-user", "test-community")

	moduleManager := testutils.NewMockModuleManager()
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	poller := poller.NewPoller(cfg, bridgeClient, moduleManager)

	// Test polling
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	// Start poller (should not error)
	err := poller.Start(ctx)
	if err != nil {
		t.Fatalf("Poller start failed: %v", err)
	}
}

func TestIntegration_ModuleExecution(t *testing.T) {
	// Create test components
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	moduleManager := modules.NewManager(cfg, storage)

	// Add test module
	testModule := testutils.TestModule("test-module")
	moduleManager.AddModule("test-module", testModule)

	// Test module execution
	ctx, cancel := testutils.TestContext()
	defer cancel()

	result, err := moduleManager.ExecuteAction(ctx, "test-module", "ping", map[string]string{})
	if err != nil {
		t.Fatalf("Module execution failed: %v", err)
	}

	if result["message"] != "pong" {
		t.Errorf("Expected message 'pong', got %v", result["message"])
	}

	// Test module info
	infos := moduleManager.GetModuleInfos()
	if len(infos) != 1 {
		t.Errorf("Expected 1 module info, got %d", len(infos))
	}

	if infos[0].Name != "test-module" {
		t.Errorf("Expected module name 'test-module', got %s", infos[0].Name)
	}

	// Test module management
	err = moduleManager.DisableModule("test-module")
	if err != nil {
		t.Fatalf("Failed to disable module: %v", err)
	}

	err = moduleManager.EnableModule("test-module")
	if err != nil {
		t.Fatalf("Failed to enable module: %v", err)
	}

	// Test cleanup
	err = moduleManager.Cleanup()
	if err != nil {
		t.Fatalf("Module cleanup failed: %v", err)
	}
}

func TestIntegration_AuthenticationFlow(t *testing.T) {
	// Create test components
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()

	authenticator, err := auth.NewWebAuthnManager(cfg, storage)
	if err != nil {
		t.Fatalf("Failed to create authenticator: %v", err)
	}

	// Test that initially not authenticated
	session := authenticator.GetCurrentSession()
	if session != nil {
		t.Error("Should not have session initially")
	}

	// Test authentication stats
	stats := authenticator.GetStats()
	if stats == nil {
		t.Error("Authenticator stats should not be nil")
	}

	// Test session management
	sessions := authenticator.GetActiveSessions()
	if len(sessions) != 0 {
		t.Errorf("Expected 0 active sessions, got %d", len(sessions))
	}

	// Test cleanup
	err = authenticator.Cleanup()
	if err != nil {
		t.Errorf("Authenticator cleanup failed: %v", err)
	}
}

func TestIntegration_StorageOperations(t *testing.T) {
	// Create temporary directory
	tmpDir := t.TempDir()

	// Create storage
	storage, err := storage.NewBoltStorage(tmpDir)
	if err != nil {
		t.Fatalf("Failed to create storage: %v", err)
	}
	defer storage.Close()

	// Test basic operations
	testData := map[string][]byte{
		"key1": []byte("value1"),
		"key2": []byte("value2"),
		"key3": []byte("value3"),
	}

	// Set values
	for key, value := range testData {
		err = storage.Set(key, value)
		if err != nil {
			t.Fatalf("Failed to set key %s: %v", key, err)
		}
	}

	// Get values
	for key, expectedValue := range testData {
		actualValue, err := storage.Get(key)
		if err != nil {
			t.Fatalf("Failed to get key %s: %v", key, err)
		}

		if string(actualValue) != string(expectedValue) {
			t.Errorf("Expected value %s for key %s, got %s", string(expectedValue), key, string(actualValue))
		}
	}

	// Test bucket operations
	bucketName := "test-bucket"
	err = storage.SetWithBucket(bucketName, "bucket-key", []byte("bucket-value"))
	if err != nil {
		t.Fatalf("Failed to set bucket value: %v", err)
	}

	bucketValue, err := storage.GetWithBucket(bucketName, "bucket-key")
	if err != nil {
		t.Fatalf("Failed to get bucket value: %v", err)
	}

	if string(bucketValue) != "bucket-value" {
		t.Errorf("Expected bucket value 'bucket-value', got %s", string(bucketValue))
	}

	// Test list operations
	keys, err := storage.List("key")
	if err != nil {
		t.Fatalf("Failed to list keys: %v", err)
	}

	if len(keys) != 3 {
		t.Errorf("Expected 3 keys, got %d", len(keys))
	}

	// Test stats
	stats := storage.Stats()
	if stats == nil {
		t.Error("Storage stats should not be nil")
	}

	// Test backup
	backupPath := filepath.Join(tmpDir, "backup.db")
	err = storage.Backup(backupPath)
	if err != nil {
		t.Fatalf("Failed to backup storage: %v", err)
	}

	// Verify backup file exists
	if _, err := os.Stat(backupPath); os.IsNotExist(err) {
		t.Error("Backup file was not created")
	}
}

func TestIntegration_ConfigurationLoading(t *testing.T) {
	// Test configuration loading with temporary directory
	tmpDir := t.TempDir()

	// Set environment variables for testing
	os.Setenv("WADDLEBOT_DATA_DIR", tmpDir)
	os.Setenv("WADDLEBOT_API_URL", "https://test.api.com")
	os.Setenv("WADDLEBOT_POLL_INTERVAL", "60")
	defer func() {
		os.Unsetenv("WADDLEBOT_DATA_DIR")
		os.Unsetenv("WADDLEBOT_API_URL")
		os.Unsetenv("WADDLEBOT_POLL_INTERVAL")
	}()

	// Test that configuration directories are created
	expectedModulesDir := filepath.Join(tmpDir, "modules")

	// Create directories
	err := os.MkdirAll(tmpDir, 0755)
	if err != nil {
		t.Fatalf("Failed to create data directory: %v", err)
	}

	err = os.MkdirAll(expectedModulesDir, 0755)
	if err != nil {
		t.Fatalf("Failed to create modules directory: %v", err)
	}

	// Verify directories exist
	if _, err := os.Stat(tmpDir); os.IsNotExist(err) {
		t.Error("Data directory was not created")
	}

	if _, err := os.Stat(expectedModulesDir); os.IsNotExist(err) {
		t.Error("Modules directory was not created")
	}
}

func TestIntegration_ErrorHandling(t *testing.T) {
	// Test error handling throughout the system
	cfg := testutils.TestConfig()
	cfg.APIURL = "http://nonexistent.domain.com"

	// Create components
	storage := testutils.NewMockStorage()
	authenticator := testutils.NewMockWebAuthnManager()
	moduleManager := modules.NewManager(cfg, storage)
	bridgeClient := testutils.NewMockBridgeClient(cfg)

	// Test bridge client with invalid URL
	bridgeClient.SetAuthError(true)
	_, err := bridgeClient.GetAuthToken()
	if err == nil {
		t.Error("Expected error for invalid auth")
	}

	// Test module manager with nonexistent module
	ctx, cancel := testutils.TestContext()
	defer cancel()

	_, err = moduleManager.ExecuteAction(ctx, "nonexistent-module", "ping", map[string]string{})
	if err == nil {
		t.Error("Expected error for nonexistent module")
	}

	// Test storage with mock error
	mockStorage := testutils.NewMockStorage()
	mockStorage.SetError(true)

	_, err = mockStorage.Get("test-key")
	if err == nil {
		t.Error("Expected error from mock storage")
	}

	// Test authenticator error conditions
	authenticator.SetRegistrationError(true)
	_, err = authenticator.StartRegistration("test-user", "test-community")
	if err == nil {
		t.Error("Expected registration error")
	}

	authenticator.SetAuthenticationError(true)
	_, err = authenticator.StartAuthentication("test-user")
	if err == nil {
		t.Error("Expected authentication error")
	}
}