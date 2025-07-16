package poller

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/sirupsen/logrus"
	"waddlebot-bridge/internal/bridge"
	"waddlebot-bridge/internal/config"
	"waddlebot-bridge/internal/logger"
	"waddlebot-bridge/internal/modules"
)

// Poller handles polling the WaddleBot API for actions to execute
type Poller struct {
	config        *config.Config
	bridgeClient  *bridge.Client
	moduleManager *modules.Manager
	logger        *logrus.Logger
	httpClient    *http.Client
	ticker        *time.Ticker
	lastPoll      time.Time
}

// ActionRequest represents an action request from the server
type ActionRequest struct {
	ID          string            `json:"id"`
	Type        string            `json:"type"`
	ModuleName  string            `json:"module_name"`
	Action      string            `json:"action"`
	Parameters  map[string]string `json:"parameters"`
	UserID      string            `json:"user_id"`
	CommunityID string            `json:"community_id"`
	Priority    int               `json:"priority"`
	Timeout     int               `json:"timeout"`
	CreatedAt   time.Time         `json:"created_at"`
	ExpiresAt   time.Time         `json:"expires_at"`
}

// ActionResponse represents the response to an action request
type ActionResponse struct {
	ID        string                 `json:"id"`
	Success   bool                   `json:"success"`
	Result    map[string]interface{} `json:"result,omitempty"`
	Error     string                 `json:"error,omitempty"`
	Duration  int64                  `json:"duration"` // in milliseconds
	Timestamp time.Time              `json:"timestamp"`
}

// PollResponse represents the response from the polling endpoint
type PollResponse struct {
	Actions     []ActionRequest `json:"actions"`
	NextPoll    time.Time       `json:"next_poll"`
	ServerTime  time.Time       `json:"server_time"`
	HasMore     bool            `json:"has_more"`
	PollCount   int             `json:"poll_count"`
	ClientInfo  ClientInfo      `json:"client_info"`
}

// ClientInfo represents client information for the poll
type ClientInfo struct {
	LastSeen       time.Time `json:"last_seen"`
	ActionsTotal   int       `json:"actions_total"`
	ActionsSuccess int       `json:"actions_success"`
	ActionsFailed  int       `json:"actions_failed"`
	Uptime         int64     `json:"uptime"`
}

// NewPoller creates a new poller instance
func NewPoller(cfg *config.Config, bridgeClient *bridge.Client, moduleManager *modules.Manager) *Poller {
	return &Poller{
		config:        cfg,
		bridgeClient:  bridgeClient,
		moduleManager: moduleManager,
		logger:        logger.GetLogger(),
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
		lastPoll: time.Now(),
	}
}

// Start starts the polling process
func (p *Poller) Start(ctx context.Context) error {
	p.logger.WithFields(logrus.Fields{
		"interval":     p.config.PollInterval,
		"community_id": p.config.CommunityID,
		"user_id":      p.config.UserID,
	}).Info("Starting action poller")

	// Create ticker for polling interval
	p.ticker = time.NewTicker(time.Duration(p.config.PollInterval) * time.Second)
	defer p.ticker.Stop()

	// Initial poll
	if err := p.pollForActions(ctx); err != nil {
		p.logger.WithError(err).Error("Initial poll failed")
	}

	// Main polling loop
	for {
		select {
		case <-ctx.Done():
			p.logger.Info("Stopping action poller")
			return nil
		case <-p.ticker.C:
			if err := p.pollForActions(ctx); err != nil {
				p.logger.WithError(err).Error("Poll failed")
			}
		}
	}
}

// pollForActions polls the server for actions to execute
func (p *Poller) pollForActions(ctx context.Context) error {
	startTime := time.Now()
	
	// Get authentication token
	token, err := p.bridgeClient.GetAuthToken()
	if err != nil {
		return fmt.Errorf("failed to get auth token: %w", err)
	}

	// Build poll URL
	pollURL := p.config.GetAPIEndpoint("/api/bridge/poll")
	
	// Create request
	req, err := http.NewRequestWithContext(ctx, "GET", pollURL, nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	// Add headers
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("User-Agent", p.config.GetUserAgent())
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Community-ID", p.config.CommunityID)
	req.Header.Set("X-User-ID", p.config.UserID)
	req.Header.Set("X-Last-Poll", p.lastPoll.Format(time.RFC3339))

	// Make request
	resp, err := p.httpClient.Do(req)
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
	var pollResponse PollResponse
	if err := json.Unmarshal(body, &pollResponse); err != nil {
		return fmt.Errorf("failed to parse response: %w", err)
	}

	// Update last poll time
	p.lastPoll = time.Now()

	// Process actions
	if len(pollResponse.Actions) > 0 {
		p.logger.WithFields(logrus.Fields{
			"action_count": len(pollResponse.Actions),
			"has_more":     pollResponse.HasMore,
		}).Info("Received actions from server")

		// Process each action
		for _, action := range pollResponse.Actions {
			if err := p.processAction(ctx, action); err != nil {
				p.logger.WithError(err).WithField("action_id", action.ID).Error("Failed to process action")
			}
		}
	}

	// Log polling statistics
	duration := time.Since(startTime)
	p.logger.WithFields(logrus.Fields{
		"duration":      duration,
		"actions":       len(pollResponse.Actions),
		"server_time":   pollResponse.ServerTime,
		"next_poll":     pollResponse.NextPoll,
		"poll_count":    pollResponse.PollCount,
	}).Debug("Poll completed")

	return nil
}

// processAction processes a single action request
func (p *Poller) processAction(ctx context.Context, action ActionRequest) error {
	startTime := time.Now()
	
	p.logger.WithFields(logrus.Fields{
		"action_id":   action.ID,
		"module_name": action.ModuleName,
		"action":      action.Action,
		"user_id":     action.UserID,
		"priority":    action.Priority,
	}).Info("Processing action")

	// Check if action has expired
	if time.Now().After(action.ExpiresAt) {
		p.logger.WithField("action_id", action.ID).Warn("Action expired, skipping")
		return p.sendActionResponse(ctx, ActionResponse{
			ID:        action.ID,
			Success:   false,
			Error:     "Action expired",
			Duration:  time.Since(startTime).Milliseconds(),
			Timestamp: time.Now(),
		})
	}

	// Create context with timeout
	actionCtx, cancel := context.WithTimeout(ctx, time.Duration(action.Timeout)*time.Second)
	defer cancel()

	// Execute action through module manager
	result, err := p.moduleManager.ExecuteAction(actionCtx, action.ModuleName, action.Action, action.Parameters)
	
	// Calculate duration
	duration := time.Since(startTime)

	// Create response
	response := ActionResponse{
		ID:        action.ID,
		Success:   err == nil,
		Duration:  duration.Milliseconds(),
		Timestamp: time.Now(),
	}

	if err != nil {
		response.Error = err.Error()
		p.logger.WithError(err).WithField("action_id", action.ID).Error("Action execution failed")
	} else {
		response.Result = result
		p.logger.WithFields(logrus.Fields{
			"action_id": action.ID,
			"duration":  duration,
		}).Info("Action executed successfully")
	}

	// Send response back to server
	return p.sendActionResponse(ctx, response)
}

// sendActionResponse sends the action response back to the server
func (p *Poller) sendActionResponse(ctx context.Context, response ActionResponse) error {
	// Get authentication token
	token, err := p.bridgeClient.GetAuthToken()
	if err != nil {
		return fmt.Errorf("failed to get auth token: %w", err)
	}

	// Build response URL
	responseURL := p.config.GetAPIEndpoint("/api/bridge/response")

	// Marshal response
	responseData, err := json.Marshal(response)
	if err != nil {
		return fmt.Errorf("failed to marshal response: %w", err)
	}

	// Create request
	req, err := http.NewRequestWithContext(ctx, "POST", responseURL, 
		strings.NewReader(string(responseData)))
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	// Add headers
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("User-Agent", p.config.GetUserAgent())
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Community-ID", p.config.CommunityID)
	req.Header.Set("X-User-ID", p.config.UserID)

	// Make request
	resp, err := p.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to make request: %w", err)
	}
	defer resp.Body.Close()

	// Check status code
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("server returned status %d: %s", resp.StatusCode, string(body))
	}

	p.logger.WithFields(logrus.Fields{
		"action_id": response.ID,
		"success":   response.Success,
		"duration":  response.Duration,
	}).Debug("Action response sent")

	return nil
}

// UpdatePollInterval updates the polling interval
func (p *Poller) UpdatePollInterval(seconds int) {
	if seconds < 5 {
		seconds = 5
	}
	
	p.config.PollInterval = seconds
	
	if p.ticker != nil {
		p.ticker.Stop()
		p.ticker = time.NewTicker(time.Duration(seconds) * time.Second)
	}
	
	p.logger.WithField("interval", seconds).Info("Updated poll interval")
}

// GetStats returns polling statistics
func (p *Poller) GetStats() map[string]interface{} {
	return map[string]interface{}{
		"poll_interval": p.config.PollInterval,
		"last_poll":     p.lastPoll,
		"uptime":        time.Since(p.lastPoll).Seconds(),
		"community_id":  p.config.CommunityID,
		"user_id":       p.config.UserID,
	}
}