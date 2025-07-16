package auth

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/go-webauthn/webauthn/webauthn"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"github.com/sirupsen/logrus"
	"waddlebot-bridge/internal/config"
	"waddlebot-bridge/internal/logger"
	"waddlebot-bridge/internal/storage"
)

// WebAuthnManager handles WebAuthn authentication
type WebAuthnManager struct {
	config     *config.Config
	storage    storage.Storage
	webauthn   *webauthn.WebAuthn
	logger     *logrus.Logger
	sessions   map[string]*AuthSession
	jwtSecret  []byte
}

// AuthSession represents an active authentication session
type AuthSession struct {
	ID          string    `json:"id"`
	UserID      string    `json:"user_id"`
	CommunityID string    `json:"community_id"`
	IssuedAt    time.Time `json:"issued_at"`
	ExpiresAt   time.Time `json:"expires_at"`
	Credential  []byte    `json:"credential"`
}

// User represents a WebAuthn user
type User struct {
	ID          []byte `json:"id"`
	Name        string `json:"name"`
	DisplayName string `json:"display_name"`
	CommunityID string `json:"community_id"`
	Credentials []webauthn.Credential `json:"credentials"`
}

// WebAuthnID returns the user's WebAuthn ID
func (u *User) WebAuthnID() []byte {
	return u.ID
}

// WebAuthnName returns the user's WebAuthn name
func (u *User) WebAuthnName() string {
	return u.Name
}

// WebAuthnDisplayName returns the user's WebAuthn display name
func (u *User) WebAuthnDisplayName() string {
	return u.DisplayName
}

// WebAuthnCredentials returns the user's WebAuthn credentials
func (u *User) WebAuthnCredentials() []webauthn.Credential {
	return u.Credentials
}

// WebAuthnIcon returns the user's WebAuthn icon (optional)
func (u *User) WebAuthnIcon() string {
	return ""
}

// NewWebAuthnManager creates a new WebAuthn manager
func NewWebAuthnManager(cfg *config.Config, store storage.Storage) (*WebAuthnManager, error) {
	// Configure WebAuthn
	wconfig := &webauthn.Config{
		RPDisplayName: cfg.WebAuthnDisplayName,
		RPID:          "localhost",
		RPOrigins:     []string{cfg.GetWebAuthnURL()},
		AuthenticatorSelection: webauthn.AuthenticatorSelection{
			RequireResidentKey: webauthn.ResidentKeyNotRequired(),
			ResidentKey:        webauthn.ResidentKeyNotRequired(),
			UserVerification:   webauthn.VerificationRequired,
		},
		Timeout: time.Duration(cfg.WebAuthnTimeout) * time.Second,
	}

	// Create WebAuthn instance
	webAuthn, err := webauthn.New(wconfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create WebAuthn instance: %w", err)
	}

	// Generate JWT secret if not provided
	jwtSecret := []byte(cfg.JWTSecret)
	if len(jwtSecret) == 0 {
		jwtSecret = []byte(uuid.New().String())
	}

	manager := &WebAuthnManager{
		config:    cfg,
		storage:   store,
		webauthn:  webAuthn,
		logger:    logger.GetLogger(),
		sessions:  make(map[string]*AuthSession),
		jwtSecret: jwtSecret,
	}

	// Load existing sessions from storage
	manager.loadSessions()

	return manager, nil
}

// StartRegistration starts the WebAuthn registration process
func (m *WebAuthnManager) StartRegistration(userID, communityID string) (*webauthn.CredentialCreation, error) {
	// Check if user is already registered
	if _, exists := m.getUserByID(userID); exists {
		return nil, fmt.Errorf("user %s is already registered", userID)
	}

	// Create new user
	user := &User{
		ID:          []byte(userID),
		Name:        userID,
		DisplayName: fmt.Sprintf("User %s", userID),
		CommunityID: communityID,
		Credentials: []webauthn.Credential{},
	}

	// Begin registration
	creation, session, err := m.webauthn.BeginRegistration(user)
	if err != nil {
		return nil, fmt.Errorf("failed to begin registration: %w", err)
	}

	// Store session for completion
	sessionData, err := json.Marshal(session)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal session: %w", err)
	}

	key := fmt.Sprintf("registration_session_%s", userID)
	if err := m.storage.Set(key, sessionData); err != nil {
		return nil, fmt.Errorf("failed to store session: %w", err)
	}

	// Store user temporarily
	userData, err := json.Marshal(user)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal user: %w", err)
	}

	userKey := fmt.Sprintf("temp_user_%s", userID)
	if err := m.storage.Set(userKey, userData); err != nil {
		return nil, fmt.Errorf("failed to store user: %w", err)
	}

	m.logger.WithFields(logrus.Fields{
		"user_id":      userID,
		"community_id": communityID,
	}).Info("Started WebAuthn registration")

	return creation, nil
}

// CompleteRegistration completes the WebAuthn registration process
func (m *WebAuthnManager) CompleteRegistration(userID string, response []byte) (*AuthSession, error) {
	// Get stored session
	sessionKey := fmt.Sprintf("registration_session_%s", userID)
	sessionData, err := m.storage.Get(sessionKey)
	if err != nil {
		return nil, fmt.Errorf("failed to get session: %w", err)
	}

	var session webauthn.SessionData
	if err := json.Unmarshal(sessionData, &session); err != nil {
		return nil, fmt.Errorf("failed to unmarshal session: %w", err)
	}

	// Get temporary user
	userKey := fmt.Sprintf("temp_user_%s", userID)
	userData, err := m.storage.Get(userKey)
	if err != nil {
		return nil, fmt.Errorf("failed to get user: %w", err)
	}

	var user User
	if err := json.Unmarshal(userData, &user); err != nil {
		return nil, fmt.Errorf("failed to unmarshal user: %w", err)
	}

	// Parse the credential creation response
	var credentialCreationResponse webauthn.CredentialCreationResponse
	if err := json.Unmarshal(response, &credentialCreationResponse); err != nil {
		return nil, fmt.Errorf("failed to unmarshal credential response: %w", err)
	}

	// Complete registration
	credential, err := m.webauthn.CreateCredential(&user, session, &credentialCreationResponse)
	if err != nil {
		return nil, fmt.Errorf("failed to create credential: %w", err)
	}

	// Add credential to user
	user.Credentials = append(user.Credentials, *credential)

	// Store user permanently
	finalUserData, err := json.Marshal(user)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal final user: %w", err)
	}

	permanentUserKey := fmt.Sprintf("user_%s", userID)
	if err := m.storage.Set(permanentUserKey, finalUserData); err != nil {
		return nil, fmt.Errorf("failed to store final user: %w", err)
	}

	// Clean up temporary data
	m.storage.Delete(sessionKey)
	m.storage.Delete(userKey)

	// Create auth session
	authSession := &AuthSession{
		ID:          uuid.New().String(),
		UserID:      userID,
		CommunityID: user.CommunityID,
		IssuedAt:    time.Now(),
		ExpiresAt:   time.Now().Add(24 * time.Hour),
		Credential:  credential.ID,
	}

	// Store auth session
	m.sessions[authSession.ID] = authSession
	m.saveSessions()

	m.logger.WithFields(logrus.Fields{
		"user_id":      userID,
		"community_id": user.CommunityID,
		"session_id":   authSession.ID,
	}).Info("Completed WebAuthn registration")

	return authSession, nil
}

// StartAuthentication starts the WebAuthn authentication process
func (m *WebAuthnManager) StartAuthentication(userID string) (*webauthn.CredentialAssertion, error) {
	// Get user
	user, exists := m.getUserByID(userID)
	if !exists {
		return nil, fmt.Errorf("user %s not found", userID)
	}

	// Begin authentication
	assertion, session, err := m.webauthn.BeginLogin(user)
	if err != nil {
		return nil, fmt.Errorf("failed to begin authentication: %w", err)
	}

	// Store session for completion
	sessionData, err := json.Marshal(session)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal session: %w", err)
	}

	key := fmt.Sprintf("auth_session_%s", userID)
	if err := m.storage.Set(key, sessionData); err != nil {
		return nil, fmt.Errorf("failed to store session: %w", err)
	}

	m.logger.WithFields(logrus.Fields{
		"user_id":      userID,
		"community_id": user.CommunityID,
	}).Info("Started WebAuthn authentication")

	return assertion, nil
}

// CompleteAuthentication completes the WebAuthn authentication process
func (m *WebAuthnManager) CompleteAuthentication(userID string, response []byte) (*AuthSession, error) {
	// Get stored session
	sessionKey := fmt.Sprintf("auth_session_%s", userID)
	sessionData, err := m.storage.Get(sessionKey)
	if err != nil {
		return nil, fmt.Errorf("failed to get session: %w", err)
	}

	var session webauthn.SessionData
	if err := json.Unmarshal(sessionData, &session); err != nil {
		return nil, fmt.Errorf("failed to unmarshal session: %w", err)
	}

	// Get user
	user, exists := m.getUserByID(userID)
	if !exists {
		return nil, fmt.Errorf("user %s not found", userID)
	}

	// Parse the credential assertion response
	var credentialAssertionResponse webauthn.CredentialAssertionResponse
	if err := json.Unmarshal(response, &credentialAssertionResponse); err != nil {
		return nil, fmt.Errorf("failed to unmarshal credential response: %w", err)
	}

	// Complete authentication
	_, err = m.webauthn.ValidateLogin(user, session, &credentialAssertionResponse)
	if err != nil {
		return nil, fmt.Errorf("failed to validate login: %w", err)
	}

	// Clean up session
	m.storage.Delete(sessionKey)

	// Create auth session
	authSession := &AuthSession{
		ID:          uuid.New().String(),
		UserID:      userID,
		CommunityID: user.CommunityID,
		IssuedAt:    time.Now(),
		ExpiresAt:   time.Now().Add(24 * time.Hour),
		Credential:  credentialAssertionResponse.RawID,
	}

	// Store auth session
	m.sessions[authSession.ID] = authSession
	m.saveSessions()

	m.logger.WithFields(logrus.Fields{
		"user_id":      userID,
		"community_id": user.CommunityID,
		"session_id":   authSession.ID,
	}).Info("Completed WebAuthn authentication")

	return authSession, nil
}

// ValidateSession validates an authentication session
func (m *WebAuthnManager) ValidateSession(sessionID string) (*AuthSession, error) {
	session, exists := m.sessions[sessionID]
	if !exists {
		return nil, fmt.Errorf("session not found")
	}

	if time.Now().After(session.ExpiresAt) {
		delete(m.sessions, sessionID)
		m.saveSessions()
		return nil, fmt.Errorf("session expired")
	}

	return session, nil
}

// GenerateJWT generates a JWT token for the session
func (m *WebAuthnManager) GenerateJWT(session *AuthSession) (string, error) {
	claims := jwt.MapClaims{
		"sub":          session.UserID,
		"community_id": session.CommunityID,
		"session_id":   session.ID,
		"iat":          session.IssuedAt.Unix(),
		"exp":          session.ExpiresAt.Unix(),
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString(m.jwtSecret)
}

// ValidateJWT validates a JWT token
func (m *WebAuthnManager) ValidateJWT(tokenString string) (*AuthSession, error) {
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return m.jwtSecret, nil
	})

	if err != nil {
		return nil, fmt.Errorf("failed to parse token: %w", err)
	}

	if claims, ok := token.Claims.(jwt.MapClaims); ok && token.Valid {
		sessionID, ok := claims["session_id"].(string)
		if !ok {
			return nil, fmt.Errorf("invalid session_id in token")
		}

		return m.ValidateSession(sessionID)
	}

	return nil, fmt.Errorf("invalid token")
}

// RevokeSession revokes an authentication session
func (m *WebAuthnManager) RevokeSession(sessionID string) error {
	delete(m.sessions, sessionID)
	m.saveSessions()
	
	m.logger.WithField("session_id", sessionID).Info("Revoked authentication session")
	return nil
}

// getUserByID retrieves a user by ID
func (m *WebAuthnManager) getUserByID(userID string) (*User, bool) {
	key := fmt.Sprintf("user_%s", userID)
	userData, err := m.storage.Get(key)
	if err != nil {
		return nil, false
	}

	var user User
	if err := json.Unmarshal(userData, &user); err != nil {
		return nil, false
	}

	return &user, true
}

// loadSessions loads existing sessions from storage
func (m *WebAuthnManager) loadSessions() {
	data, err := m.storage.Get("auth_sessions")
	if err != nil {
		return // No existing sessions
	}

	var sessions map[string]*AuthSession
	if err := json.Unmarshal(data, &sessions); err != nil {
		m.logger.WithError(err).Error("Failed to unmarshal sessions")
		return
	}

	// Filter out expired sessions
	now := time.Now()
	for id, session := range sessions {
		if now.Before(session.ExpiresAt) {
			m.sessions[id] = session
		}
	}
}

// saveSessions saves current sessions to storage
func (m *WebAuthnManager) saveSessions() {
	data, err := json.Marshal(m.sessions)
	if err != nil {
		m.logger.WithError(err).Error("Failed to marshal sessions")
		return
	}

	if err := m.storage.Set("auth_sessions", data); err != nil {
		m.logger.WithError(err).Error("Failed to save sessions")
	}
}

// IsAuthenticated checks if the current session is authenticated
func (m *WebAuthnManager) IsAuthenticated() bool {
	return len(m.sessions) > 0
}

// GetCurrentSession returns the current active session (if any)
func (m *WebAuthnManager) GetCurrentSession() *AuthSession {
	for _, session := range m.sessions {
		if time.Now().Before(session.ExpiresAt) {
			return session
		}
	}
	return nil
}