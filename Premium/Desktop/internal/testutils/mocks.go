package testutils

import (
	"context"
	"time"

	"waddlebot-bridge/internal/auth"
	"waddlebot-bridge/internal/config"
	"waddlebot-bridge/internal/modules"
	"waddlebot-bridge/internal/storage"
)

// MockStorage implements the storage interface for testing
type MockStorage struct {
	data map[string][]byte
}

// NewMockStorage creates a new mock storage instance
func NewMockStorage() *MockStorage {
	return &MockStorage{
		data: make(map[string][]byte),
	}
}

func (m *MockStorage) Set(key string, value []byte) error {
	m.data[key] = value
	return nil
}

func (m *MockStorage) Get(key string) ([]byte, error) {
	if value, exists := m.data[key]; exists {
		return value, nil
	}
	return nil, storage.ErrKeyNotFound
}

func (m *MockStorage) Delete(key string) error {
	delete(m.data, key)
	return nil
}

func (m *MockStorage) Exists(key string) bool {
	_, exists := m.data[key]
	return exists
}

func (m *MockStorage) List(prefix string) ([]string, error) {
	var keys []string
	for key := range m.data {
		if len(key) >= len(prefix) && key[:len(prefix)] == prefix {
			keys = append(keys, key)
		}
	}
	return keys, nil
}

func (m *MockStorage) SetWithBucket(bucketName, key string, value []byte) error {
	return m.Set(bucketName+":"+key, value)
}

func (m *MockStorage) GetWithBucket(bucketName, key string) ([]byte, error) {
	return m.Get(bucketName + ":" + key)
}

func (m *MockStorage) DeleteWithBucket(bucketName, key string) error {
	return m.Delete(bucketName + ":" + key)
}

func (m *MockStorage) ListWithBucket(bucketName, prefix string) ([]string, error) {
	return m.List(bucketName + ":" + prefix)
}

func (m *MockStorage) GetAllFromBucket(bucketName string) (map[string][]byte, error) {
	result := make(map[string][]byte)
	bucketPrefix := bucketName + ":"
	for key, value := range m.data {
		if len(key) >= len(bucketPrefix) && key[:len(bucketPrefix)] == bucketPrefix {
			cleanKey := key[len(bucketPrefix):]
			result[cleanKey] = value
		}
	}
	return result, nil
}

func (m *MockStorage) ClearBucket(bucketName string) error {
	bucketPrefix := bucketName + ":"
	for key := range m.data {
		if len(key) >= len(bucketPrefix) && key[:len(bucketPrefix)] == bucketPrefix {
			delete(m.data, key)
		}
	}
	return nil
}

func (m *MockStorage) Close() error {
	return nil
}

func (m *MockStorage) Backup(backupPath string) error {
	return nil
}

func (m *MockStorage) Stats() map[string]interface{} {
	return map[string]interface{}{
		"keys": len(m.data),
	}
}

// MockModule implements the module interface for testing
type MockModule struct {
	name     string
	actions  map[string]func(ctx context.Context, parameters map[string]string) (map[string]interface{}, error)
	initFunc func(config map[string]string) error
}

// NewMockModule creates a new mock module
func NewMockModule(name string) *MockModule {
	return &MockModule{
		name:    name,
		actions: make(map[string]func(ctx context.Context, parameters map[string]string) (map[string]interface{}, error)),
	}
}

func (m *MockModule) Initialize(config map[string]string) error {
	if m.initFunc != nil {
		return m.initFunc(config)
	}
	return nil
}

func (m *MockModule) GetInfo() *modules.ModuleInfo {
	var actions []modules.ActionInfo
	for actionName := range m.actions {
		actions = append(actions, modules.ActionInfo{
			Name:        actionName,
			Description: "Test action",
			Parameters:  map[string]interface{}{},
			ReturnType:  "object",
			Timeout:     30,
		})
	}

	return &modules.ModuleInfo{
		Name:        m.name,
		Version:     "1.0.0",
		Description: "Mock module for testing",
		Author:      "Test",
		Actions:     actions,
		Enabled:     true,
		LoadedAt:    time.Now(),
	}
}

func (m *MockModule) ExecuteAction(ctx context.Context, action string, parameters map[string]string) (map[string]interface{}, error) {
	if actionFunc, exists := m.actions[action]; exists {
		return actionFunc(ctx, parameters)
	}
	return nil, modules.ErrActionNotFound
}

func (m *MockModule) GetActions() []modules.ActionInfo {
	return m.GetInfo().Actions
}

func (m *MockModule) Cleanup() error {
	return nil
}

// AddAction adds an action to the mock module
func (m *MockModule) AddAction(name string, handler func(ctx context.Context, parameters map[string]string) (map[string]interface{}, error)) {
	m.actions[name] = handler
}

// SetInitFunc sets the initialization function
func (m *MockModule) SetInitFunc(fn func(config map[string]string) error) {
	m.initFunc = fn
}

// MockAuthSession represents a mock auth session
type MockAuthSession struct {
	ID          string
	UserID      string
	CommunityID string
	IssuedAt    time.Time
	ExpiresAt   time.Time
	Valid       bool
}

// MockWebAuthnManager implements auth manager for testing
type MockWebAuthnManager struct {
	sessions map[string]*MockAuthSession
	users    map[string]*MockUser
}

// MockUser represents a mock user
type MockUser struct {
	ID          string
	Name        string
	DisplayName string
	CommunityID string
}

// NewMockWebAuthnManager creates a new mock auth manager
func NewMockWebAuthnManager() *MockWebAuthnManager {
	return &MockWebAuthnManager{
		sessions: make(map[string]*MockAuthSession),
		users:    make(map[string]*MockUser),
	}
}

// AddUser adds a user to the mock manager
func (m *MockWebAuthnManager) AddUser(userID, communityID string) {
	m.users[userID] = &MockUser{
		ID:          userID,
		Name:        userID,
		DisplayName: "Test User " + userID,
		CommunityID: communityID,
	}
}

// AddSession adds a session to the mock manager
func (m *MockWebAuthnManager) AddSession(sessionID, userID, communityID string) {
	m.sessions[sessionID] = &MockAuthSession{
		ID:          sessionID,
		UserID:      userID,
		CommunityID: communityID,
		IssuedAt:    time.Now(),
		ExpiresAt:   time.Now().Add(time.Hour),
		Valid:       true,
	}
}

// ValidateSession validates a session
func (m *MockWebAuthnManager) ValidateSession(sessionID string) (*auth.AuthSession, error) {
	session, exists := m.sessions[sessionID]
	if !exists {
		return nil, auth.ErrSessionNotFound
	}
	
	if !session.Valid || time.Now().After(session.ExpiresAt) {
		return nil, auth.ErrSessionExpired
	}

	return &auth.AuthSession{
		ID:          session.ID,
		UserID:      session.UserID,
		CommunityID: session.CommunityID,
		IssuedAt:    session.IssuedAt,
		ExpiresAt:   session.ExpiresAt,
	}, nil
}

// IsAuthenticated checks if authenticated
func (m *MockWebAuthnManager) IsAuthenticated() bool {
	return len(m.sessions) > 0
}

// GetCurrentSession returns current session
func (m *MockWebAuthnManager) GetCurrentSession() *auth.AuthSession {
	for _, session := range m.sessions {
		if session.Valid && time.Now().Before(session.ExpiresAt) {
			return &auth.AuthSession{
				ID:          session.ID,
				UserID:      session.UserID,
				CommunityID: session.CommunityID,
				IssuedAt:    session.IssuedAt,
				ExpiresAt:   session.ExpiresAt,
			}
		}
	}
	return nil
}

// TestConfig creates a test configuration
func TestConfig() *config.Config {
	return &config.Config{
		APIURL:      "http://test.waddlebot.io",
		CommunityID: "test-community",
		UserID:      "test-user",
		PollInterval: 30,
		WebPort:     8080,
		WebHost:     "127.0.0.1",
		DataDir:     "/tmp/waddlebot-test",
		LogLevel:    "info",
		WebAuthnDisplayName: "Test Bridge",
		WebAuthnOrigin:      "http://127.0.0.1:8080",
		WebAuthnTimeout:     60,
		JWTSecret:          "test-secret",
		ModulesDir:         "/tmp/waddlebot-test/modules",
		ModuleTimeout:      30,
		MaxConcurrentTasks: 10,
	}
}

// TestModule creates a test module
func TestModule(name string) *MockModule {
	module := NewMockModule(name)
	
	// Add some basic test actions
	module.AddAction("ping", func(ctx context.Context, parameters map[string]string) (map[string]interface{}, error) {
		return map[string]interface{}{"message": "pong"}, nil
	})
	
	module.AddAction("echo", func(ctx context.Context, parameters map[string]string) (map[string]interface{}, error) {
		message := parameters["message"]
		if message == "" {
			message = "hello"
		}
		return map[string]interface{}{"echo": message}, nil
	})
	
	module.AddAction("fail", func(ctx context.Context, parameters map[string]string) (map[string]interface{}, error) {
		return nil, modules.ErrActionFailed
	})
	
	return module
}

// ErrKeyNotFound is returned when a key is not found
var ErrKeyNotFound = storage.ErrKeyNotFound

// Define common test errors
var (
	ErrTestFailed = fmt.Errorf("test failed")
)

// Helper function to create a test context with timeout
func TestContext() (context.Context, context.CancelFunc) {
	return context.WithTimeout(context.Background(), 5*time.Second)
}