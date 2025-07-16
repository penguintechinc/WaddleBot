package bridge

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/sirupsen/logrus"
	"waddlebot-bridge/internal/auth"
	"waddlebot-bridge/internal/config"
	"waddlebot-bridge/internal/logger"
	"waddlebot-bridge/internal/modules"
)

// Client handles communication with the WaddleBot API
type Client struct {
	config       *config.Config
	authenticator *auth.WebAuthnManager
	moduleManager *modules.Manager
	logger       *logrus.Logger
	httpClient   *http.Client
}

// BridgeInfo represents bridge information
type BridgeInfo struct {
	BridgeID    string    `json:"bridge_id"`
	UserID      string    `json:"user_id"`
	CommunityID string    `json:"community_id"`
	Status      string    `json:"status"`
	Version     string    `json:"version"`
	Platform    string    `json:"platform"`
	LastSeen    time.Time `json:"last_seen"`
	Capabilities []string `json:"capabilities"`
}

// RegistrationRequest represents a bridge registration request
type RegistrationRequest struct {
	UserID      string            `json:"user_id"`
	CommunityID string            `json:"community_id"`
	BridgeInfo  BridgeInfo        `json:"bridge_info"`
	Modules     []modules.ModuleInfo `json:"modules"`
}

// RegistrationResponse represents the response from bridge registration
type RegistrationResponse struct {
	Success     bool   `json:"success"`
	BridgeID    string `json:"bridge_id"`
	Message     string `json:"message"`
	PollInterval int   `json:"poll_interval"`
}

// NewClient creates a new bridge client
func NewClient(cfg *config.Config, authenticator *auth.WebAuthnManager, moduleManager *modules.Manager) (*Client, error) {
	return &Client{
		config:       cfg,
		authenticator: authenticator,
		moduleManager: moduleManager,
		logger:       logger.GetLogger(),
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}, nil
}

// GetAuthToken gets the current authentication token
func (c *Client) GetAuthToken() (string, error) {
	session := c.authenticator.GetCurrentSession()
	if session == nil {
		return "", fmt.Errorf("no authenticated session found")
	}

	return c.authenticator.GenerateJWT(session)
}

// RegisterBridge registers the bridge with the WaddleBot API
func (c *Client) RegisterBridge(ctx context.Context) error {
	c.logger.Info("Registering bridge with WaddleBot API")

	// Get authentication token
	token, err := c.GetAuthToken()
	if err != nil {
		return fmt.Errorf("failed to get auth token: %w", err)
	}

	// Get module information
	moduleInfos := c.moduleManager.GetModuleInfos()

	// Create registration request
	bridgeInfo := BridgeInfo{
		UserID:      c.config.UserID,
		CommunityID: c.config.CommunityID,
		Status:      "active",
		Version:     "1.0.0",
		Platform:    fmt.Sprintf("%s/%s", c.config.GetUserAgent(), "desktop"),
		LastSeen:    time.Now(),
		Capabilities: []string{
			"local_execution",
			"file_operations",
			"system_info",
			"process_management",
			"network_operations",
		},
	}

	request := RegistrationRequest{
		UserID:      c.config.UserID,
		CommunityID: c.config.CommunityID,
		BridgeInfo:  bridgeInfo,
		Modules:     moduleInfos,
	}

	// Marshal request
	requestData, err := json.Marshal(request)
	if err != nil {
		return fmt.Errorf("failed to marshal registration request: %w", err)
	}

	// Build registration URL
	registrationURL := c.config.GetAPIEndpoint("/api/bridge/register")

	// Create request
	req, err := http.NewRequestWithContext(ctx, "POST", registrationURL, 
		strings.NewReader(string(requestData)))
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	// Add headers
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("User-Agent", c.config.GetUserAgent())
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Community-ID", c.config.CommunityID)
	req.Header.Set("X-User-ID", c.config.UserID)

	// Make request
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to make request: %w", err)
	}
	defer resp.Body.Close()

	// Read response
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("failed to read response: %w", err)
	}

	// Check status code
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("server returned status %d: %s", resp.StatusCode, string(body))
	}

	// Parse response
	var registrationResponse RegistrationResponse
	if err := json.Unmarshal(body, &registrationResponse); err != nil {
		return fmt.Errorf("failed to parse response: %w", err)
	}

	if !registrationResponse.Success {
		return fmt.Errorf("registration failed: %s", registrationResponse.Message)
	}

	c.logger.WithFields(logrus.Fields{
		"bridge_id":     registrationResponse.BridgeID,
		"poll_interval": registrationResponse.PollInterval,
	}).Info("Bridge registered successfully")

	return nil
}

// SendHeartbeat sends a heartbeat to the server
func (c *Client) SendHeartbeat(ctx context.Context) error {
	// Get authentication token
	token, err := c.GetAuthToken()
	if err != nil {
		return fmt.Errorf("failed to get auth token: %w", err)
	}

	// Create heartbeat data
	heartbeat := map[string]interface{}{
		"timestamp":    time.Now(),
		"status":       "active",
		"module_count": len(c.moduleManager.GetModuleInfos()),
		"capabilities": []string{
			"local_execution",
			"file_operations",
			"system_info",
			"process_management",
			"network_operations",
		},
	}

	// Marshal heartbeat
	heartbeatData, err := json.Marshal(heartbeat)
	if err != nil {
		return fmt.Errorf("failed to marshal heartbeat: %w", err)
	}

	// Build heartbeat URL
	heartbeatURL := c.config.GetAPIEndpoint("/api/bridge/heartbeat")

	// Create request
	req, err := http.NewRequestWithContext(ctx, "POST", heartbeatURL, 
		strings.NewReader(string(heartbeatData)))
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	// Add headers
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("User-Agent", c.config.GetUserAgent())
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Community-ID", c.config.CommunityID)
	req.Header.Set("X-User-ID", c.config.UserID)

	// Make request
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to make request: %w", err)
	}
	defer resp.Body.Close()

	// Check status code
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("server returned status %d: %s", resp.StatusCode, string(body))
	}

	c.logger.Debug("Heartbeat sent successfully")
	return nil
}

// GetBridgeInfo retrieves bridge information from the server
func (c *Client) GetBridgeInfo(ctx context.Context) (*BridgeInfo, error) {
	// Get authentication token
	token, err := c.GetAuthToken()
	if err != nil {
		return nil, fmt.Errorf("failed to get auth token: %w", err)
	}

	// Build info URL
	infoURL := c.config.GetAPIEndpoint("/api/bridge/info")

	// Create request
	req, err := http.NewRequestWithContext(ctx, "GET", infoURL, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Add headers
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("User-Agent", c.config.GetUserAgent())
	req.Header.Set("X-Community-ID", c.config.CommunityID)
	req.Header.Set("X-User-ID", c.config.UserID)

	// Make request
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to make request: %w", err)
	}
	defer resp.Body.Close()

	// Read response
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	// Check status code
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("server returned status %d: %s", resp.StatusCode, string(body))
	}

	// Parse response
	var bridgeInfo BridgeInfo
	if err := json.Unmarshal(body, &bridgeInfo); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	return &bridgeInfo, nil
}

// UnregisterBridge unregisters the bridge from the WaddleBot API
func (c *Client) UnregisterBridge(ctx context.Context) error {
	c.logger.Info("Unregistering bridge from WaddleBot API")

	// Get authentication token
	token, err := c.GetAuthToken()
	if err != nil {
		return fmt.Errorf("failed to get auth token: %w", err)
	}

	// Build unregister URL
	unregisterURL := c.config.GetAPIEndpoint("/api/bridge/unregister")

	// Create request
	req, err := http.NewRequestWithContext(ctx, "POST", unregisterURL, nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	// Add headers
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("User-Agent", c.config.GetUserAgent())
	req.Header.Set("X-Community-ID", c.config.CommunityID)
	req.Header.Set("X-User-ID", c.config.UserID)

	// Make request
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to make request: %w", err)
	}
	defer resp.Body.Close()

	// Check status code
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("server returned status %d: %s", resp.StatusCode, string(body))
	}

	c.logger.Info("Bridge unregistered successfully")
	return nil
}

// IsAuthenticated checks if the client is authenticated
func (c *Client) IsAuthenticated() bool {
	return c.authenticator.IsAuthenticated()
}

// GetStats returns client statistics
func (c *Client) GetStats() map[string]interface{} {
	return map[string]interface{}{
		"authenticated": c.IsAuthenticated(),
		"user_id":       c.config.UserID,
		"community_id":  c.config.CommunityID,
		"api_url":       c.config.APIURL,
		"user_agent":    c.config.GetUserAgent(),
		"modules":       len(c.moduleManager.GetModuleInfos()),
	}
}