package server

import (
	"context"
	"encoding/json"
	"fmt"
	"html/template"
	"net/http"
	"time"

	"github.com/gorilla/mux"
	"github.com/sirupsen/logrus"
	"waddlebot-bridge/internal/auth"
	"waddlebot-bridge/internal/bridge"
	"waddlebot-bridge/internal/config"
	"waddlebot-bridge/internal/logger"
)

// WebServer handles the web interface for authentication
type WebServer struct {
	config       *config.Config
	authenticator *auth.WebAuthnManager
	bridgeClient *bridge.Client
	logger       *logrus.Logger
	server       *http.Server
}

// NewWebServer creates a new web server
func NewWebServer(cfg *config.Config, authenticator *auth.WebAuthnManager, bridgeClient *bridge.Client) *WebServer {
	return &WebServer{
		config:       cfg,
		authenticator: authenticator,
		bridgeClient: bridgeClient,
		logger:       logger.GetLogger(),
	}
}

// Start starts the web server
func (s *WebServer) Start(ctx context.Context) error {
	router := mux.NewRouter()

	// Static files
	router.PathPrefix("/static/").Handler(http.StripPrefix("/static/", http.FileServer(http.Dir("./web/static/"))))

	// Authentication routes
	router.HandleFunc("/", s.handleIndex).Methods("GET")
	router.HandleFunc("/auth/register/start", s.handleRegisterStart).Methods("POST")
	router.HandleFunc("/auth/register/complete", s.handleRegisterComplete).Methods("POST")
	router.HandleFunc("/auth/login/start", s.handleLoginStart).Methods("POST")
	router.HandleFunc("/auth/login/complete", s.handleLoginComplete).Methods("POST")
	router.HandleFunc("/auth/logout", s.handleLogout).Methods("POST")

	// Status routes
	router.HandleFunc("/status", s.handleStatus).Methods("GET")
	router.HandleFunc("/health", s.handleHealth).Methods("GET")

	// Create server
	s.server = &http.Server{
		Addr:    fmt.Sprintf("%s:%d", s.config.WebHost, s.config.WebPort),
		Handler: router,
	}

	s.logger.WithFields(logrus.Fields{
		"host": s.config.WebHost,
		"port": s.config.WebPort,
	}).Info("Starting web server")

	// Start server in goroutine
	go func() {
		if err := s.server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			s.logger.WithError(err).Error("Web server error")
		}
	}()

	// Wait for context cancellation
	<-ctx.Done()

	// Graceful shutdown
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	return s.server.Shutdown(shutdownCtx)
}

// handleIndex serves the main page
func (s *WebServer) handleIndex(w http.ResponseWriter, r *http.Request) {
	tmpl := `
<!DOCTYPE html>
<html>
<head>
    <title>WaddleBot Premium Desktop Bridge</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .logo { font-size: 2em; color: #4CAF50; margin-bottom: 10px; }
        .status { margin: 20px 0; padding: 15px; border-radius: 5px; }
        .status.connected { background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .status.disconnected { background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        .actions { margin: 20px 0; }
        .btn { padding: 10px 20px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        .btn-primary { background-color: #007bff; color: white; }
        .btn-success { background-color: #28a745; color: white; }
        .btn-warning { background-color: #ffc107; color: black; }
        .btn-danger { background-color: #dc3545; color: white; }
        .form-group { margin: 15px 0; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-group input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        .info { margin: 20px 0; padding: 15px; background-color: #f8f9fa; border-radius: 5px; }
        .footer { margin-top: 30px; text-align: center; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🤖 WaddleBot Premium Desktop Bridge</div>
            <p>Local System Integration Platform</p>
        </div>

        <div id="status" class="status disconnected">
            <strong>Status:</strong> Checking authentication...
        </div>

        <div class="actions">
            <div id="auth-section">
                <h3>Authentication Required</h3>
                <p>Please authenticate using WebAuthn to connect your bridge to WaddleBot.</p>
                
                <div class="form-group">
                    <label for="user-id">User ID:</label>
                    <input type="text" id="user-id" placeholder="Enter your WaddleBot user ID">
                </div>
                
                <div class="form-group">
                    <label for="community-id">Community ID:</label>
                    <input type="text" id="community-id" placeholder="Enter your community ID">
                </div>
                
                <button class="btn btn-primary" onclick="register()">Register New Device</button>
                <button class="btn btn-success" onclick="login()">Login</button>
            </div>
            
            <div id="authenticated-section" style="display: none;">
                <h3>Bridge Connected</h3>
                <p>Your bridge is successfully connected to WaddleBot.</p>
                <button class="btn btn-warning" onclick="logout()">Logout</button>
            </div>
        </div>

        <div class="info">
            <h3>Configuration</h3>
            <div id="config-info">
                <strong>API URL:</strong> {{.APIURL}}<br>
                <strong>Poll Interval:</strong> {{.PollInterval}} seconds<br>
                <strong>Web Port:</strong> {{.WebPort}}<br>
                <strong>Data Directory:</strong> {{.DataDir}}
            </div>
        </div>

        <div class="footer">
            <p>WaddleBot Premium Desktop Bridge v1.0.0</p>
            <p>© 2024 WaddleBot. All rights reserved.</p>
        </div>
    </div>

    <script>
        // Check authentication status on load
        window.onload = checkAuthStatus;

        async function checkAuthStatus() {
            try {
                const response = await fetch('/status');
                const data = await response.json();
                
                if (data.authenticated) {
                    document.getElementById('status').className = 'status connected';
                    document.getElementById('status').innerHTML = '<strong>Status:</strong> Connected and authenticated';
                    document.getElementById('auth-section').style.display = 'none';
                    document.getElementById('authenticated-section').style.display = 'block';
                } else {
                    document.getElementById('status').className = 'status disconnected';
                    document.getElementById('status').innerHTML = '<strong>Status:</strong> Not authenticated';
                    document.getElementById('auth-section').style.display = 'block';
                    document.getElementById('authenticated-section').style.display = 'none';
                }
            } catch (error) {
                console.error('Error checking auth status:', error);
                document.getElementById('status').className = 'status disconnected';
                document.getElementById('status').innerHTML = '<strong>Status:</strong> Error checking authentication';
            }
        }

        async function register() {
            const userId = document.getElementById('user-id').value;
            const communityId = document.getElementById('community-id').value;
            
            if (!userId || !communityId) {
                alert('Please enter both User ID and Community ID');
                return;
            }
            
            try {
                const response = await fetch('/auth/register/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: userId, community_id: communityId })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    const credential = await navigator.credentials.create({
                        publicKey: data.credentialCreationOptions
                    });
                    
                    const completeResponse = await fetch('/auth/register/complete', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            user_id: userId,
                            credential: credential
                        })
                    });
                    
                    if (completeResponse.ok) {
                        alert('Registration successful!');
                        checkAuthStatus();
                    } else {
                        const errorData = await completeResponse.json();
                        alert('Registration failed: ' + errorData.error);
                    }
                } else {
                    alert('Registration failed: ' + data.error);
                }
            } catch (error) {
                console.error('Registration error:', error);
                alert('Registration failed: ' + error.message);
            }
        }

        async function login() {
            const userId = document.getElementById('user-id').value;
            
            if (!userId) {
                alert('Please enter your User ID');
                return;
            }
            
            try {
                const response = await fetch('/auth/login/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: userId })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    const credential = await navigator.credentials.get({
                        publicKey: data.credentialRequestOptions
                    });
                    
                    const completeResponse = await fetch('/auth/login/complete', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            user_id: userId,
                            credential: credential
                        })
                    });
                    
                    if (completeResponse.ok) {
                        alert('Login successful!');
                        checkAuthStatus();
                    } else {
                        const errorData = await completeResponse.json();
                        alert('Login failed: ' + errorData.error);
                    }
                } else {
                    alert('Login failed: ' + data.error);
                }
            } catch (error) {
                console.error('Login error:', error);
                alert('Login failed: ' + error.message);
            }
        }

        async function logout() {
            try {
                const response = await fetch('/auth/logout', {
                    method: 'POST'
                });
                
                if (response.ok) {
                    alert('Logged out successfully');
                    checkAuthStatus();
                } else {
                    alert('Logout failed');
                }
            } catch (error) {
                console.error('Logout error:', error);
                alert('Logout failed: ' + error.message);
            }
        }
    </script>
</body>
</html>
	`

	t, err := template.New("index").Parse(tmpl)
	if err != nil {
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		return
	}

	data := struct {
		APIURL       string
		PollInterval int
		WebPort      int
		DataDir      string
	}{
		APIURL:       s.config.APIURL,
		PollInterval: s.config.PollInterval,
		WebPort:      s.config.WebPort,
		DataDir:      s.config.DataDir,
	}

	w.Header().Set("Content-Type", "text/html")
	t.Execute(w, data)
}

// handleRegisterStart handles the start of WebAuthn registration
func (s *WebServer) handleRegisterStart(w http.ResponseWriter, r *http.Request) {
	var req struct {
		UserID      string `json:"user_id"`
		CommunityID string `json:"community_id"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	creation, err := s.authenticator.StartRegistration(req.UserID, req.CommunityID)
	if err != nil {
		s.logger.WithError(err).Error("Failed to start registration")
		http.Error(w, fmt.Sprintf("Registration failed: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"credentialCreationOptions": creation,
	})
}

// handleRegisterComplete handles the completion of WebAuthn registration
func (s *WebServer) handleRegisterComplete(w http.ResponseWriter, r *http.Request) {
	var req struct {
		UserID     string      `json:"user_id"`
		Credential interface{} `json:"credential"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	credentialData, err := json.Marshal(req.Credential)
	if err != nil {
		http.Error(w, "Invalid credential format", http.StatusBadRequest)
		return
	}

	session, err := s.authenticator.CompleteRegistration(req.UserID, credentialData)
	if err != nil {
		s.logger.WithError(err).Error("Failed to complete registration")
		http.Error(w, fmt.Sprintf("Registration failed: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success":    true,
		"session_id": session.ID,
	})
}

// handleLoginStart handles the start of WebAuthn login
func (s *WebServer) handleLoginStart(w http.ResponseWriter, r *http.Request) {
	var req struct {
		UserID string `json:"user_id"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	assertion, err := s.authenticator.StartAuthentication(req.UserID)
	if err != nil {
		s.logger.WithError(err).Error("Failed to start authentication")
		http.Error(w, fmt.Sprintf("Authentication failed: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"credentialRequestOptions": assertion,
	})
}

// handleLoginComplete handles the completion of WebAuthn login
func (s *WebServer) handleLoginComplete(w http.ResponseWriter, r *http.Request) {
	var req struct {
		UserID     string      `json:"user_id"`
		Credential interface{} `json:"credential"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	credentialData, err := json.Marshal(req.Credential)
	if err != nil {
		http.Error(w, "Invalid credential format", http.StatusBadRequest)
		return
	}

	session, err := s.authenticator.CompleteAuthentication(req.UserID, credentialData)
	if err != nil {
		s.logger.WithError(err).Error("Failed to complete authentication")
		http.Error(w, fmt.Sprintf("Authentication failed: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success":    true,
		"session_id": session.ID,
	})
}

// handleLogout handles user logout
func (s *WebServer) handleLogout(w http.ResponseWriter, r *http.Request) {
	session := s.authenticator.GetCurrentSession()
	if session != nil {
		s.authenticator.RevokeSession(session.ID)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
	})
}

// handleStatus returns the current authentication status
func (s *WebServer) handleStatus(w http.ResponseWriter, r *http.Request) {
	session := s.authenticator.GetCurrentSession()
	authenticated := session != nil

	status := map[string]interface{}{
		"authenticated": authenticated,
		"bridge_status": "running",
	}

	if authenticated {
		status["user_id"] = session.UserID
		status["community_id"] = session.CommunityID
		status["session_expires"] = session.ExpiresAt
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(status)
}

// handleHealth returns the health status
func (s *WebServer) handleHealth(w http.ResponseWriter, r *http.Request) {
	health := map[string]interface{}{
		"status":    "healthy",
		"timestamp": time.Now(),
		"version":   "1.0.0",
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(health)
}