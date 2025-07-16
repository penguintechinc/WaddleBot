package auth

import (
	"testing"
	"time"

	"waddlebot-bridge/internal/config"
	"waddlebot-bridge/internal/testutils"
)

func TestNewWebAuthnManager(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()

	manager, err := NewWebAuthnManager(cfg, storage)
	if err != nil {
		t.Fatalf("NewWebAuthnManager failed: %v", err)
	}

	if manager == nil {
		t.Fatal("Expected non-nil manager")
	}

	if manager.config != cfg {
		t.Error("Expected config to be set")
	}

	if manager.storage != storage {
		t.Error("Expected storage to be set")
	}

	if manager.sessions == nil {
		t.Error("Expected sessions map to be initialized")
	}
}

func TestWebAuthnManager_StartRegistration(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager, err := NewWebAuthnManager(cfg, storage)
	if err != nil {
		t.Fatalf("NewWebAuthnManager failed: %v", err)
	}

	userID := "test-user"
	communityID := "test-community"

	// Test successful registration start
	creation, err := manager.StartRegistration(userID, communityID)
	if err != nil {
		t.Fatalf("StartRegistration failed: %v", err)
	}

	if creation == nil {
		t.Fatal("Expected non-nil creation")
	}

	// Test duplicate registration
	_, err = manager.StartRegistration(userID, communityID)
	if err == nil {
		t.Error("Expected error for duplicate registration")
	}
}

func TestWebAuthnManager_StartAuthentication(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager, err := NewWebAuthnManager(cfg, storage)
	if err != nil {
		t.Fatalf("NewWebAuthnManager failed: %v", err)
	}

	userID := "test-user"

	// Test authentication for non-existent user
	_, err = manager.StartAuthentication(userID)
	if err == nil {
		t.Error("Expected error for non-existent user")
	}

	// TODO: Add test for successful authentication start
	// This requires a more complex setup with actual WebAuthn credentials
}

func TestWebAuthnManager_ValidateSession(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager, err := NewWebAuthnManager(cfg, storage)
	if err != nil {
		t.Fatalf("NewWebAuthnManager failed: %v", err)
	}

	sessionID := "test-session"
	userID := "test-user"
	communityID := "test-community"

	// Test non-existent session
	_, err = manager.ValidateSession(sessionID)
	if err == nil {
		t.Error("Expected error for non-existent session")
	}

	// Create a test session
	session := &AuthSession{
		ID:          sessionID,
		UserID:      userID,
		CommunityID: communityID,
		IssuedAt:    time.Now(),
		ExpiresAt:   time.Now().Add(time.Hour),
	}
	manager.sessions[sessionID] = session

	// Test valid session
	validatedSession, err := manager.ValidateSession(sessionID)
	if err != nil {
		t.Fatalf("ValidateSession failed: %v", err)
	}

	if validatedSession.ID != sessionID {
		t.Errorf("Expected session ID %s, got %s", sessionID, validatedSession.ID)
	}

	if validatedSession.UserID != userID {
		t.Errorf("Expected user ID %s, got %s", userID, validatedSession.UserID)
	}

	// Test expired session
	session.ExpiresAt = time.Now().Add(-time.Hour)
	_, err = manager.ValidateSession(sessionID)
	if err == nil {
		t.Error("Expected error for expired session")
	}
}

func TestWebAuthnManager_GenerateJWT(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager, err := NewWebAuthnManager(cfg, storage)
	if err != nil {
		t.Fatalf("NewWebAuthnManager failed: %v", err)
	}

	session := &AuthSession{
		ID:          "test-session",
		UserID:      "test-user",
		CommunityID: "test-community",
		IssuedAt:    time.Now(),
		ExpiresAt:   time.Now().Add(time.Hour),
	}

	token, err := manager.GenerateJWT(session)
	if err != nil {
		t.Fatalf("GenerateJWT failed: %v", err)
	}

	if token == "" {
		t.Error("Expected non-empty token")
	}

	// Test token validation
	validatedSession, err := manager.ValidateJWT(token)
	if err != nil {
		t.Fatalf("ValidateJWT failed: %v", err)
	}

	if validatedSession == nil {
		t.Fatal("Expected non-nil session")
	}

	if validatedSession.ID != session.ID {
		t.Errorf("Expected session ID %s, got %s", session.ID, validatedSession.ID)
	}
}

func TestWebAuthnManager_ValidateJWT(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager, err := NewWebAuthnManager(cfg, storage)
	if err != nil {
		t.Fatalf("NewWebAuthnManager failed: %v", err)
	}

	// Test invalid token
	_, err = manager.ValidateJWT("invalid-token")
	if err == nil {
		t.Error("Expected error for invalid token")
	}

	// Test empty token
	_, err = manager.ValidateJWT("")
	if err == nil {
		t.Error("Expected error for empty token")
	}
}

func TestWebAuthnManager_RevokeSession(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager, err := NewWebAuthnManager(cfg, storage)
	if err != nil {
		t.Fatalf("NewWebAuthnManager failed: %v", err)
	}

	sessionID := "test-session"
	session := &AuthSession{
		ID:          sessionID,
		UserID:      "test-user",
		CommunityID: "test-community",
		IssuedAt:    time.Now(),
		ExpiresAt:   time.Now().Add(time.Hour),
	}

	manager.sessions[sessionID] = session

	// Test session exists
	if _, exists := manager.sessions[sessionID]; !exists {
		t.Error("Expected session to exist")
	}

	// Revoke session
	err = manager.RevokeSession(sessionID)
	if err != nil {
		t.Fatalf("RevokeSession failed: %v", err)
	}

	// Test session no longer exists
	if _, exists := manager.sessions[sessionID]; exists {
		t.Error("Expected session to be removed")
	}
}

func TestWebAuthnManager_IsAuthenticated(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager, err := NewWebAuthnManager(cfg, storage)
	if err != nil {
		t.Fatalf("NewWebAuthnManager failed: %v", err)
	}

	// Test no sessions
	if manager.IsAuthenticated() {
		t.Error("Expected false for no sessions")
	}

	// Add a session
	session := &AuthSession{
		ID:          "test-session",
		UserID:      "test-user",
		CommunityID: "test-community",
		IssuedAt:    time.Now(),
		ExpiresAt:   time.Now().Add(time.Hour),
	}
	manager.sessions[session.ID] = session

	// Test with sessions
	if !manager.IsAuthenticated() {
		t.Error("Expected true for existing sessions")
	}
}

func TestWebAuthnManager_GetCurrentSession(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager, err := NewWebAuthnManager(cfg, storage)
	if err != nil {
		t.Fatalf("NewWebAuthnManager failed: %v", err)
	}

	// Test no sessions
	session := manager.GetCurrentSession()
	if session != nil {
		t.Error("Expected nil for no sessions")
	}

	// Add a valid session
	validSession := &AuthSession{
		ID:          "test-session",
		UserID:      "test-user",
		CommunityID: "test-community",
		IssuedAt:    time.Now(),
		ExpiresAt:   time.Now().Add(time.Hour),
	}
	manager.sessions[validSession.ID] = validSession

	// Test with valid session
	currentSession := manager.GetCurrentSession()
	if currentSession == nil {
		t.Error("Expected non-nil session")
	}

	if currentSession.ID != validSession.ID {
		t.Errorf("Expected session ID %s, got %s", validSession.ID, currentSession.ID)
	}

	// Add an expired session
	expiredSession := &AuthSession{
		ID:          "expired-session",
		UserID:      "test-user",
		CommunityID: "test-community",
		IssuedAt:    time.Now().Add(-2 * time.Hour),
		ExpiresAt:   time.Now().Add(-time.Hour),
	}
	manager.sessions[expiredSession.ID] = expiredSession

	// Should still return the valid session
	currentSession = manager.GetCurrentSession()
	if currentSession == nil {
		t.Error("Expected non-nil session")
	}

	if currentSession.ID != validSession.ID {
		t.Errorf("Expected session ID %s, got %s", validSession.ID, currentSession.ID)
	}
}

func TestUser_WebAuthnMethods(t *testing.T) {
	user := &User{
		ID:          []byte("test-user"),
		Name:        "test-user",
		DisplayName: "Test User",
		CommunityID: "test-community",
		Credentials: []webauthn.Credential{},
	}

	// Test WebAuthnID
	id := user.WebAuthnID()
	if string(id) != "test-user" {
		t.Errorf("Expected WebAuthnID 'test-user', got %s", string(id))
	}

	// Test WebAuthnName
	name := user.WebAuthnName()
	if name != "test-user" {
		t.Errorf("Expected WebAuthnName 'test-user', got %s", name)
	}

	// Test WebAuthnDisplayName
	displayName := user.WebAuthnDisplayName()
	if displayName != "Test User" {
		t.Errorf("Expected WebAuthnDisplayName 'Test User', got %s", displayName)
	}

	// Test WebAuthnCredentials
	credentials := user.WebAuthnCredentials()
	if len(credentials) != 0 {
		t.Errorf("Expected 0 credentials, got %d", len(credentials))
	}

	// Test WebAuthnIcon
	icon := user.WebAuthnIcon()
	if icon != "" {
		t.Errorf("Expected empty icon, got %s", icon)
	}
}

func TestAuthSession_Validation(t *testing.T) {
	now := time.Now()
	
	tests := []struct {
		name      string
		session   *AuthSession
		expectErr bool
	}{
		{
			name: "valid session",
			session: &AuthSession{
				ID:          "test-session",
				UserID:      "test-user",
				CommunityID: "test-community",
				IssuedAt:    now,
				ExpiresAt:   now.Add(time.Hour),
			},
			expectErr: false,
		},
		{
			name: "expired session",
			session: &AuthSession{
				ID:          "test-session",
				UserID:      "test-user",
				CommunityID: "test-community",
				IssuedAt:    now.Add(-2 * time.Hour),
				ExpiresAt:   now.Add(-time.Hour),
			},
			expectErr: true,
		},
		{
			name: "empty session ID",
			session: &AuthSession{
				ID:          "",
				UserID:      "test-user",
				CommunityID: "test-community",
				IssuedAt:    now,
				ExpiresAt:   now.Add(time.Hour),
			},
			expectErr: true,
		},
		{
			name: "empty user ID",
			session: &AuthSession{
				ID:          "test-session",
				UserID:      "",
				CommunityID: "test-community",
				IssuedAt:    now,
				ExpiresAt:   now.Add(time.Hour),
			},
			expectErr: true,
		},
		{
			name: "empty community ID",
			session: &AuthSession{
				ID:          "test-session",
				UserID:      "test-user",
				CommunityID: "",
				IssuedAt:    now,
				ExpiresAt:   now.Add(time.Hour),
			},
			expectErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateAuthSession(tt.session)
			if tt.expectErr && err == nil {
				t.Error("Expected error but got none")
			}
			if !tt.expectErr && err != nil {
				t.Errorf("Expected no error but got: %v", err)
			}
		})
	}
}

// Helper function to validate auth session
func validateAuthSession(session *AuthSession) error {
	if session.ID == "" {
		return ErrInvalidCredentials
	}
	if session.UserID == "" {
		return ErrInvalidCredentials
	}
	if session.CommunityID == "" {
		return ErrInvalidCredentials
	}
	if time.Now().After(session.ExpiresAt) {
		return ErrSessionExpired
	}
	return nil
}