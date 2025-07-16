package poller

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"waddlebot-bridge/internal/testutils"
)

func TestNewPoller(t *testing.T) {
	cfg := testutils.TestConfig()
	bridgeClient := testutils.NewMockBridgeClient(cfg)
	moduleManager := testutils.NewMockModuleManager()

	poller := NewPoller(cfg, bridgeClient, moduleManager)

	if poller == nil {
		t.Fatal("Expected non-nil poller")
	}

	if poller.config != cfg {
		t.Error("Expected config to be set")
	}

	if poller.bridgeClient != bridgeClient {
		t.Error("Expected bridgeClient to be set")
	}

	if poller.moduleManager != moduleManager {
		t.Error("Expected moduleManager to be set")
	}

	if poller.logger == nil {
		t.Error("Expected logger to be set")
	}

	if poller.httpClient == nil {
		t.Error("Expected httpClient to be set")
	}

	if poller.httpClient.Timeout != 30*time.Second {
		t.Errorf("Expected httpClient timeout 30s, got %v", poller.httpClient.Timeout)
	}
}

func TestPoller_PollForActions_Success(t *testing.T) {
	// Create test server
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Verify request
		if r.URL.Path != "/api/bridge/poll" {
			t.Errorf("Expected path '/api/bridge/poll', got %s", r.URL.Path)
		}

		if r.Method != "GET" {
			t.Errorf("Expected method GET, got %s", r.Method)
		}

		// Check headers
		if r.Header.Get("Authorization") == "" {
			t.Error("Expected Authorization header")
		}

		if r.Header.Get("X-Community-ID") == "" {
			t.Error("Expected X-Community-ID header")
		}

		if r.Header.Get("X-User-ID") == "" {
			t.Error("Expected X-User-ID header")
		}

		// Return successful response
		response := PollResponse{
			Actions: []ActionRequest{
				{
					ID:          "test-action-1",
					Type:        "module_action",
					ModuleName:  "test-module",
					Action:      "ping",
					Parameters:  map[string]string{"test": "value"},
					UserID:      "test-user",
					CommunityID: "test-community",
					Priority:    1,
					Timeout:     30,
					CreatedAt:   time.Now(),
					ExpiresAt:   time.Now().Add(5 * time.Minute),
				},
			},
			NextPoll:   time.Now().Add(30 * time.Second),
			ServerTime: time.Now(),
			HasMore:    false,
			PollCount:  1,
			ClientInfo: ClientInfo{
				LastSeen:       time.Now(),
				ActionsTotal:   1,
				ActionsSuccess: 0,
				ActionsFailed:  0,
				Uptime:         3600,
			},
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
	}))
	defer server.Close()

	// Create test components
	cfg := testutils.TestConfig()
	cfg.APIURL = server.URL
	bridgeClient := testutils.NewMockBridgeClient(cfg)
	moduleManager := testutils.NewMockModuleManager()

	// Add test module
	testModule := testutils.TestModule("test-module")
	moduleManager.AddModule("test-module", testModule)

	poller := NewPoller(cfg, bridgeClient, moduleManager)

	// Mock response server
	responseServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/bridge/response" {
			w.WriteHeader(http.StatusOK)
		}
	}))
	defer responseServer.Close()

	// Update config to use response server
	cfg.APIURL = responseServer.URL
	server.Config.Handler = http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/bridge/poll" {
			response := PollResponse{
				Actions: []ActionRequest{
					{
						ID:          "test-action-1",
						Type:        "module_action",
						ModuleName:  "test-module",
						Action:      "ping",
						Parameters:  map[string]string{"test": "value"},
						UserID:      "test-user",
						CommunityID: "test-community",
						Priority:    1,
						Timeout:     30,
						CreatedAt:   time.Now(),
						ExpiresAt:   time.Now().Add(5 * time.Minute),
					},
				},
				NextPoll:   time.Now().Add(30 * time.Second),
				ServerTime: time.Now(),
				HasMore:    false,
				PollCount:  1,
			}
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(response)
		} else if r.URL.Path == "/api/bridge/response" {
			w.WriteHeader(http.StatusOK)
		}
	})
	cfg.APIURL = server.URL

	// Test polling
	ctx, cancel := testutils.TestContext()
	defer cancel()

	err := poller.pollForActions(ctx)
	if err != nil {
		t.Fatalf("pollForActions failed: %v", err)
	}
}

func TestPoller_PollForActions_EmptyResponse(t *testing.T) {
	// Create test server that returns empty actions
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		response := PollResponse{
			Actions:    []ActionRequest{},
			NextPoll:   time.Now().Add(30 * time.Second),
			ServerTime: time.Now(),
			HasMore:    false,
			PollCount:  1,
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
	}))
	defer server.Close()

	cfg := testutils.TestConfig()
	cfg.APIURL = server.URL
	bridgeClient := testutils.NewMockBridgeClient(cfg)
	moduleManager := testutils.NewMockModuleManager()

	poller := NewPoller(cfg, bridgeClient, moduleManager)

	ctx, cancel := testutils.TestContext()
	defer cancel()

	err := poller.pollForActions(ctx)
	if err != nil {
		t.Fatalf("pollForActions failed: %v", err)
	}
}

func TestPoller_PollForActions_ServerError(t *testing.T) {
	// Create test server that returns error
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte("Internal server error"))
	}))
	defer server.Close()

	cfg := testutils.TestConfig()
	cfg.APIURL = server.URL
	bridgeClient := testutils.NewMockBridgeClient(cfg)
	moduleManager := testutils.NewMockModuleManager()

	poller := NewPoller(cfg, bridgeClient, moduleManager)

	ctx, cancel := testutils.TestContext()
	defer cancel()

	err := poller.pollForActions(ctx)
	if err == nil {
		t.Error("Expected error for server error")
	}
}

func TestPoller_PollForActions_InvalidJSON(t *testing.T) {
	// Create test server that returns invalid JSON
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("invalid json"))
	}))
	defer server.Close()

	cfg := testutils.TestConfig()
	cfg.APIURL = server.URL
	bridgeClient := testutils.NewMockBridgeClient(cfg)
	moduleManager := testutils.NewMockModuleManager()

	poller := NewPoller(cfg, bridgeClient, moduleManager)

	ctx, cancel := testutils.TestContext()
	defer cancel()

	err := poller.pollForActions(ctx)
	if err == nil {
		t.Error("Expected error for invalid JSON")
	}
}

func TestPoller_ProcessAction_Success(t *testing.T) {
	cfg := testutils.TestConfig()
	bridgeClient := testutils.NewMockBridgeClient(cfg)
	moduleManager := testutils.NewMockModuleManager()

	// Add test module
	testModule := testutils.TestModule("test-module")
	moduleManager.AddModule("test-module", testModule)

	// Create response server
	responseServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/bridge/response" {
			// Verify response data
			var response ActionResponse
			err := json.NewDecoder(r.Body).Decode(&response)
			if err != nil {
				t.Fatalf("Failed to decode response: %v", err)
			}

			if response.ID != "test-action-1" {
				t.Errorf("Expected response ID 'test-action-1', got %s", response.ID)
			}

			if !response.Success {
				t.Errorf("Expected success true, got %v", response.Success)
			}

			w.WriteHeader(http.StatusOK)
		}
	}))
	defer responseServer.Close()

	cfg.APIURL = responseServer.URL
	poller := NewPoller(cfg, bridgeClient, moduleManager)

	action := ActionRequest{
		ID:          "test-action-1",
		Type:        "module_action",
		ModuleName:  "test-module",
		Action:      "ping",
		Parameters:  map[string]string{},
		UserID:      "test-user",
		CommunityID: "test-community",
		Priority:    1,
		Timeout:     30,
		CreatedAt:   time.Now(),
		ExpiresAt:   time.Now().Add(5 * time.Minute),
	}

	ctx, cancel := testutils.TestContext()
	defer cancel()

	err := poller.processAction(ctx, action)
	if err != nil {
		t.Fatalf("processAction failed: %v", err)
	}
}

func TestPoller_ProcessAction_ExpiredAction(t *testing.T) {
	cfg := testutils.TestConfig()
	bridgeClient := testutils.NewMockBridgeClient(cfg)
	moduleManager := testutils.NewMockModuleManager()

	// Create response server
	responseServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/bridge/response" {
			var response ActionResponse
			err := json.NewDecoder(r.Body).Decode(&response)
			if err != nil {
				t.Fatalf("Failed to decode response: %v", err)
			}

			if response.Success {
				t.Error("Expected success false for expired action")
			}

			if response.Error != "Action expired" {
				t.Errorf("Expected error 'Action expired', got %s", response.Error)
			}

			w.WriteHeader(http.StatusOK)
		}
	}))
	defer responseServer.Close()

	cfg.APIURL = responseServer.URL
	poller := NewPoller(cfg, bridgeClient, moduleManager)

	// Create expired action
	action := ActionRequest{
		ID:          "expired-action",
		Type:        "module_action",
		ModuleName:  "test-module",
		Action:      "ping",
		Parameters:  map[string]string{},
		UserID:      "test-user",
		CommunityID: "test-community",
		Priority:    1,
		Timeout:     30,
		CreatedAt:   time.Now().Add(-10 * time.Minute),
		ExpiresAt:   time.Now().Add(-5 * time.Minute), // Expired
	}

	ctx, cancel := testutils.TestContext()
	defer cancel()

	err := poller.processAction(ctx, action)
	if err != nil {
		t.Fatalf("processAction failed: %v", err)
	}
}

func TestPoller_ProcessAction_ModuleError(t *testing.T) {
	cfg := testutils.TestConfig()
	bridgeClient := testutils.NewMockBridgeClient(cfg)
	moduleManager := testutils.NewMockModuleManager()

	// Add test module
	testModule := testutils.TestModule("test-module")
	moduleManager.AddModule("test-module", testModule)

	// Create response server
	responseServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/bridge/response" {
			var response ActionResponse
			err := json.NewDecoder(r.Body).Decode(&response)
			if err != nil {
				t.Fatalf("Failed to decode response: %v", err)
			}

			if response.Success {
				t.Error("Expected success false for module error")
			}

			if response.Error == "" {
				t.Error("Expected error message for module error")
			}

			w.WriteHeader(http.StatusOK)
		}
	}))
	defer responseServer.Close()

	cfg.APIURL = responseServer.URL
	poller := NewPoller(cfg, bridgeClient, moduleManager)

	// Create action that will fail
	action := ActionRequest{
		ID:          "fail-action",
		Type:        "module_action",
		ModuleName:  "test-module",
		Action:      "fail", // This action will fail
		Parameters:  map[string]string{},
		UserID:      "test-user",
		CommunityID: "test-community",
		Priority:    1,
		Timeout:     30,
		CreatedAt:   time.Now(),
		ExpiresAt:   time.Now().Add(5 * time.Minute),
	}

	ctx, cancel := testutils.TestContext()
	defer cancel()

	err := poller.processAction(ctx, action)
	if err != nil {
		t.Fatalf("processAction failed: %v", err)
	}
}

func TestPoller_ProcessAction_NonexistentModule(t *testing.T) {
	cfg := testutils.TestConfig()
	bridgeClient := testutils.NewMockBridgeClient(cfg)
	moduleManager := testutils.NewMockModuleManager()

	// Create response server
	responseServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/bridge/response" {
			var response ActionResponse
			err := json.NewDecoder(r.Body).Decode(&response)
			if err != nil {
				t.Fatalf("Failed to decode response: %v", err)
			}

			if response.Success {
				t.Error("Expected success false for nonexistent module")
			}

			w.WriteHeader(http.StatusOK)
		}
	}))
	defer responseServer.Close()

	cfg.APIURL = responseServer.URL
	poller := NewPoller(cfg, bridgeClient, moduleManager)

	action := ActionRequest{
		ID:          "nonexistent-action",
		Type:        "module_action",
		ModuleName:  "nonexistent-module",
		Action:      "ping",
		Parameters:  map[string]string{},
		UserID:      "test-user",
		CommunityID: "test-community",
		Priority:    1,
		Timeout:     30,
		CreatedAt:   time.Now(),
		ExpiresAt:   time.Now().Add(5 * time.Minute),
	}

	ctx, cancel := testutils.TestContext()
	defer cancel()

	err := poller.processAction(ctx, action)
	if err != nil {
		t.Fatalf("processAction failed: %v", err)
	}
}

func TestPoller_SendActionResponse_Success(t *testing.T) {
	// Create test server
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/bridge/response" {
			t.Errorf("Expected path '/api/bridge/response', got %s", r.URL.Path)
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

		// Read and verify response
		var response ActionResponse
		err := json.NewDecoder(r.Body).Decode(&response)
		if err != nil {
			t.Fatalf("Failed to decode response: %v", err)
		}

		if response.ID != "test-action-1" {
			t.Errorf("Expected response ID 'test-action-1', got %s", response.ID)
		}

		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	cfg := testutils.TestConfig()
	cfg.APIURL = server.URL
	bridgeClient := testutils.NewMockBridgeClient(cfg)
	moduleManager := testutils.NewMockModuleManager()

	poller := NewPoller(cfg, bridgeClient, moduleManager)

	response := ActionResponse{
		ID:        "test-action-1",
		Success:   true,
		Result:    map[string]interface{}{"message": "pong"},
		Duration:  100,
		Timestamp: time.Now(),
	}

	ctx, cancel := testutils.TestContext()
	defer cancel()

	err := poller.sendActionResponse(ctx, response)
	if err != nil {
		t.Fatalf("sendActionResponse failed: %v", err)
	}
}

func TestPoller_SendActionResponse_ServerError(t *testing.T) {
	// Create test server that returns error
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte("Internal server error"))
	}))
	defer server.Close()

	cfg := testutils.TestConfig()
	cfg.APIURL = server.URL
	bridgeClient := testutils.NewMockBridgeClient(cfg)
	moduleManager := testutils.NewMockModuleManager()

	poller := NewPoller(cfg, bridgeClient, moduleManager)

	response := ActionResponse{
		ID:        "test-action-1",
		Success:   true,
		Result:    map[string]interface{}{"message": "pong"},
		Duration:  100,
		Timestamp: time.Now(),
	}

	ctx, cancel := testutils.TestContext()
	defer cancel()

	err := poller.sendActionResponse(ctx, response)
	if err == nil {
		t.Error("Expected error for server error")
	}
}

func TestPoller_UpdatePollInterval(t *testing.T) {
	cfg := testutils.TestConfig()
	bridgeClient := testutils.NewMockBridgeClient(cfg)
	moduleManager := testutils.NewMockModuleManager()

	poller := NewPoller(cfg, bridgeClient, moduleManager)

	// Test normal update
	poller.UpdatePollInterval(60)
	if poller.config.PollInterval != 60 {
		t.Errorf("Expected poll interval 60, got %d", poller.config.PollInterval)
	}

	// Test minimum value enforcement
	poller.UpdatePollInterval(3)
	if poller.config.PollInterval != 5 {
		t.Errorf("Expected poll interval 5 (minimum), got %d", poller.config.PollInterval)
	}

	// Test with active ticker
	poller.ticker = time.NewTicker(30 * time.Second)
	poller.UpdatePollInterval(45)
	if poller.config.PollInterval != 45 {
		t.Errorf("Expected poll interval 45, got %d", poller.config.PollInterval)
	}
}

func TestPoller_GetStats(t *testing.T) {
	cfg := testutils.TestConfig()
	bridgeClient := testutils.NewMockBridgeClient(cfg)
	moduleManager := testutils.NewMockModuleManager()

	poller := NewPoller(cfg, bridgeClient, moduleManager)

	stats := poller.GetStats()

	if stats == nil {
		t.Fatal("Expected non-nil stats")
	}

	if stats["poll_interval"] != cfg.PollInterval {
		t.Errorf("Expected poll_interval %d, got %v", cfg.PollInterval, stats["poll_interval"])
	}

	if stats["community_id"] != cfg.CommunityID {
		t.Errorf("Expected community_id %s, got %v", cfg.CommunityID, stats["community_id"])
	}

	if stats["user_id"] != cfg.UserID {
		t.Errorf("Expected user_id %s, got %v", cfg.UserID, stats["user_id"])
	}

	if stats["last_poll"] == nil {
		t.Error("Expected last_poll to be set")
	}

	if stats["uptime"] == nil {
		t.Error("Expected uptime to be set")
	}
}

func TestPoller_Start_ContextCancellation(t *testing.T) {
	cfg := testutils.TestConfig()
	bridgeClient := testutils.NewMockBridgeClient(cfg)
	moduleManager := testutils.NewMockModuleManager()

	// Create test server
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		response := PollResponse{
			Actions:    []ActionRequest{},
			NextPoll:   time.Now().Add(30 * time.Second),
			ServerTime: time.Now(),
			HasMore:    false,
			PollCount:  1,
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
	}))
	defer server.Close()

	cfg.APIURL = server.URL
	cfg.PollInterval = 1 // Short interval for testing
	poller := NewPoller(cfg, bridgeClient, moduleManager)

	// Start poller with short-lived context
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	err := poller.Start(ctx)
	if err != nil {
		t.Fatalf("Start failed: %v", err)
	}
}

func TestPoller_Start_PollError(t *testing.T) {
	cfg := testutils.TestConfig()
	bridgeClient := testutils.NewMockBridgeClient(cfg)
	moduleManager := testutils.NewMockModuleManager()

	// Create test server that returns error
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte("Internal server error"))
	}))
	defer server.Close()

	cfg.APIURL = server.URL
	cfg.PollInterval = 1 // Short interval for testing
	poller := NewPoller(cfg, bridgeClient, moduleManager)

	// Start poller with short-lived context
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	// Should not fail even with poll errors
	err := poller.Start(ctx)
	if err != nil {
		t.Fatalf("Start failed: %v", err)
	}
}

func TestPoller_PollForActions_AuthError(t *testing.T) {
	cfg := testutils.TestConfig()
	bridgeClient := testutils.NewMockBridgeClient(cfg)
	moduleManager := testutils.NewMockModuleManager()

	// Configure bridge client to return auth error
	bridgeClient.SetAuthError(true)

	poller := NewPoller(cfg, bridgeClient, moduleManager)

	ctx, cancel := testutils.TestContext()
	defer cancel()

	err := poller.pollForActions(ctx)
	if err == nil {
		t.Error("Expected error for auth failure")
	}

	if !strings.Contains(err.Error(), "failed to get auth token") {
		t.Errorf("Expected auth error, got %v", err)
	}
}

func TestPoller_ProcessAction_Timeout(t *testing.T) {
	cfg := testutils.TestConfig()
	bridgeClient := testutils.NewMockBridgeClient(cfg)
	moduleManager := testutils.NewMockModuleManager()

	// Add slow module
	slowModule := testutils.NewMockModule("slow-module")
	slowModule.AddAction("slow", func(ctx context.Context, parameters map[string]string) (map[string]interface{}, error) {
		time.Sleep(2 * time.Second)
		return map[string]interface{}{"result": "done"}, nil
	})
	moduleManager.AddModule("slow-module", slowModule)

	// Create response server
	responseServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	defer responseServer.Close()

	cfg.APIURL = responseServer.URL
	poller := NewPoller(cfg, bridgeClient, moduleManager)

	// Create action with short timeout
	action := ActionRequest{
		ID:          "timeout-action",
		Type:        "module_action",
		ModuleName:  "slow-module",
		Action:      "slow",
		Parameters:  map[string]string{},
		UserID:      "test-user",
		CommunityID: "test-community",
		Priority:    1,
		Timeout:     1, // 1 second timeout
		CreatedAt:   time.Now(),
		ExpiresAt:   time.Now().Add(5 * time.Minute),
	}

	ctx, cancel := testutils.TestContext()
	defer cancel()

	err := poller.processAction(ctx, action)
	if err != nil {
		t.Fatalf("processAction failed: %v", err)
	}
}