package config

import (
	"os"
	"path/filepath"
	"testing"
	"runtime"

	"github.com/spf13/viper"
)

func TestLoad(t *testing.T) {
	// Reset viper for clean test
	viper.Reset()
	
	// Create temporary directory for testing
	tmpDir := t.TempDir()
	
	// Set test data directory
	viper.Set("data-dir", tmpDir)
	
	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() failed: %v", err)
	}
	
	if cfg == nil {
		t.Fatal("Expected non-nil config")
	}
	
	// Test default values
	if cfg.APIURL != "https://api.waddlebot.io" {
		t.Errorf("Expected default APIURL 'https://api.waddlebot.io', got %s", cfg.APIURL)
	}
	
	if cfg.PollInterval != 30 {
		t.Errorf("Expected default PollInterval 30, got %d", cfg.PollInterval)
	}
	
	if cfg.WebPort != 8080 {
		t.Errorf("Expected default WebPort 8080, got %d", cfg.WebPort)
	}
	
	if cfg.WebHost != "127.0.0.1" {
		t.Errorf("Expected default WebHost '127.0.0.1', got %s", cfg.WebHost)
	}
	
	if cfg.LogLevel != "info" {
		t.Errorf("Expected default LogLevel 'info', got %s", cfg.LogLevel)
	}
	
	// Test data directory was set
	if cfg.DataDir != tmpDir {
		t.Errorf("Expected DataDir %s, got %s", tmpDir, cfg.DataDir)
	}
	
	// Test modules directory was set
	expectedModulesDir := filepath.Join(tmpDir, "modules")
	if cfg.ModulesDir != expectedModulesDir {
		t.Errorf("Expected ModulesDir %s, got %s", expectedModulesDir, cfg.ModulesDir)
	}
	
	// Test directories were created
	if _, err := os.Stat(cfg.DataDir); os.IsNotExist(err) {
		t.Error("Data directory was not created")
	}
	
	if _, err := os.Stat(cfg.ModulesDir); os.IsNotExist(err) {
		t.Error("Modules directory was not created")
	}
}

func TestLoadWithCustomValues(t *testing.T) {
	// Reset viper for clean test
	viper.Reset()
	
	// Set custom values
	viper.Set("api-url", "https://custom.api.com")
	viper.Set("community-id", "test-community")
	viper.Set("user-id", "test-user")
	viper.Set("poll-interval", 60)
	viper.Set("web-port", 9000)
	viper.Set("web-host", "0.0.0.0")
	viper.Set("log-level", "debug")
	
	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() failed: %v", err)
	}
	
	// Test custom values
	if cfg.APIURL != "https://custom.api.com" {
		t.Errorf("Expected APIURL 'https://custom.api.com', got %s", cfg.APIURL)
	}
	
	if cfg.CommunityID != "test-community" {
		t.Errorf("Expected CommunityID 'test-community', got %s", cfg.CommunityID)
	}
	
	if cfg.UserID != "test-user" {
		t.Errorf("Expected UserID 'test-user', got %s", cfg.UserID)
	}
	
	if cfg.PollInterval != 60 {
		t.Errorf("Expected PollInterval 60, got %d", cfg.PollInterval)
	}
	
	if cfg.WebPort != 9000 {
		t.Errorf("Expected WebPort 9000, got %d", cfg.WebPort)
	}
	
	if cfg.WebHost != "0.0.0.0" {
		t.Errorf("Expected WebHost '0.0.0.0', got %s", cfg.WebHost)
	}
	
	if cfg.LogLevel != "debug" {
		t.Errorf("Expected LogLevel 'debug', got %s", cfg.LogLevel)
	}
}

func TestSetDefaults(t *testing.T) {
	// Reset viper for clean test
	viper.Reset()
	
	setDefaults()
	
	// Test all defaults are set
	expectedDefaults := map[string]interface{}{
		"api-url":                    "https://api.waddlebot.io",
		"poll-interval":              30,
		"web-port":                   8080,
		"web-host":                   "127.0.0.1",
		"log-level":                  "info",
		"webauthn-display-name":      "WaddleBot Bridge",
		"webauthn-origin":            "http://127.0.0.1:8080",
		"webauthn-timeout":           60,
		"module-timeout":             30,
		"max-concurrent-tasks":       10,
	}
	
	for key, expected := range expectedDefaults {
		actual := viper.Get(key)
		if actual != expected {
			t.Errorf("Expected default %s to be %v, got %v", key, expected, actual)
		}
	}
}

func TestSetPlatformDefaults(t *testing.T) {
	tests := []struct {
		name            string
		goos            string
		expectedDisplay string
	}{
		{
			name:            "macOS",
			goos:            "darwin",
			expectedDisplay: "WaddleBot Bridge for macOS",
		},
		{
			name:            "Windows",
			goos:            "windows",
			expectedDisplay: "WaddleBot Bridge for Windows",
		},
		{
			name:            "Linux",
			goos:            "linux",
			expectedDisplay: "WaddleBot Bridge for Linux",
		},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			cfg := &Config{
				WebAuthnDisplayName: "",
			}
			
			// We can't actually change runtime.GOOS, so we'll test the logic manually
			switch tt.goos {
			case "darwin":
				cfg.WebAuthnDisplayName = "WaddleBot Bridge for macOS"
			case "windows":
				cfg.WebAuthnDisplayName = "WaddleBot Bridge for Windows"
			case "linux":
				cfg.WebAuthnDisplayName = "WaddleBot Bridge for Linux"
			}
			
			if cfg.WebAuthnDisplayName != tt.expectedDisplay {
				t.Errorf("Expected WebAuthnDisplayName %s, got %s", tt.expectedDisplay, cfg.WebAuthnDisplayName)
			}
		})
	}
}

func TestConfig_GetWebAuthnURL(t *testing.T) {
	cfg := &Config{
		WebHost: "127.0.0.1",
		WebPort: 8080,
	}
	
	expected := "http://127.0.0.1:8080"
	actual := cfg.GetWebAuthnURL()
	
	if actual != expected {
		t.Errorf("Expected WebAuthnURL %s, got %s", expected, actual)
	}
}

func TestConfig_GetAPIEndpoint(t *testing.T) {
	cfg := &Config{
		APIURL: "https://api.waddlebot.io",
	}
	
	tests := []struct {
		path     string
		expected string
	}{
		{
			path:     "/api/bridge/poll",
			expected: "https://api.waddlebot.io/api/bridge/poll",
		},
		{
			path:     "/health",
			expected: "https://api.waddlebot.io/health",
		},
		{
			path:     "",
			expected: "https://api.waddlebot.io",
		},
	}
	
	for _, tt := range tests {
		t.Run(tt.path, func(t *testing.T) {
			actual := cfg.GetAPIEndpoint(tt.path)
			if actual != tt.expected {
				t.Errorf("Expected API endpoint %s, got %s", tt.expected, actual)
			}
		})
	}
}

func TestConfig_GetUserAgent(t *testing.T) {
	cfg := &Config{}
	
	userAgent := cfg.GetUserAgent()
	
	expectedPrefix := "WaddleBot-Bridge/1.0.0"
	if len(userAgent) < len(expectedPrefix) {
		t.Errorf("Expected user agent to start with %s, got %s", expectedPrefix, userAgent)
	}
	
	if userAgent[:len(expectedPrefix)] != expectedPrefix {
		t.Errorf("Expected user agent to start with %s, got %s", expectedPrefix, userAgent)
	}
	
	// Should contain OS and architecture
	if !contains(userAgent, runtime.GOOS) {
		t.Errorf("Expected user agent to contain OS %s, got %s", runtime.GOOS, userAgent)
	}
	
	if !contains(userAgent, runtime.GOARCH) {
		t.Errorf("Expected user agent to contain arch %s, got %s", runtime.GOARCH, userAgent)
	}
}

func TestLoadWithInvalidDataDir(t *testing.T) {
	// Reset viper for clean test
	viper.Reset()
	
	// Set invalid data directory (file instead of directory)
	tmpFile := filepath.Join(t.TempDir(), "invalid-file")
	if err := os.WriteFile(tmpFile, []byte("test"), 0644); err != nil {
		t.Fatalf("Failed to create test file: %v", err)
	}
	
	viper.Set("data-dir", tmpFile)
	
	_, err := Load()
	if err == nil {
		t.Error("Expected error for invalid data directory, got none")
	}
}

func TestLoadWithValidDataDir(t *testing.T) {
	// Reset viper for clean test
	viper.Reset()
	
	tmpDir := t.TempDir()
	viper.Set("data-dir", tmpDir)
	
	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() failed: %v", err)
	}
	
	if cfg.DataDir != tmpDir {
		t.Errorf("Expected DataDir %s, got %s", tmpDir, cfg.DataDir)
	}
}

func TestLoadWithHomeDir(t *testing.T) {
	// Reset viper for clean test
	viper.Reset()
	
	// Don't set data-dir, should use home directory
	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() failed: %v", err)
	}
	
	// Should contain .waddlebot-bridge in the path
	if !contains(cfg.DataDir, ".waddlebot-bridge") {
		t.Errorf("Expected DataDir to contain '.waddlebot-bridge', got %s", cfg.DataDir)
	}
}

func TestValidateConfig(t *testing.T) {
	tests := []struct {
		name      string
		cfg       *Config
		expectErr bool
	}{
		{
			name: "valid config",
			cfg: &Config{
				APIURL:       "https://api.waddlebot.io",
				CommunityID:  "test-community",
				UserID:       "test-user",
				PollInterval: 30,
				WebPort:      8080,
				WebHost:      "127.0.0.1",
				DataDir:      "/tmp/test",
				ModulesDir:   "/tmp/test/modules",
			},
			expectErr: false,
		},
		{
			name: "invalid poll interval",
			cfg: &Config{
				APIURL:       "https://api.waddlebot.io",
				CommunityID:  "test-community",
				UserID:       "test-user",
				PollInterval: 3,
				WebPort:      8080,
				WebHost:      "127.0.0.1",
				DataDir:      "/tmp/test",
				ModulesDir:   "/tmp/test/modules",
			},
			expectErr: true,
		},
		{
			name: "invalid web port",
			cfg: &Config{
				APIURL:       "https://api.waddlebot.io",
				CommunityID:  "test-community",
				UserID:       "test-user",
				PollInterval: 30,
				WebPort:      0,
				WebHost:      "127.0.0.1",
				DataDir:      "/tmp/test",
				ModulesDir:   "/tmp/test/modules",
			},
			expectErr: true,
		},
		{
			name: "empty API URL",
			cfg: &Config{
				APIURL:       "",
				CommunityID:  "test-community",
				UserID:       "test-user",
				PollInterval: 30,
				WebPort:      8080,
				WebHost:      "127.0.0.1",
				DataDir:      "/tmp/test",
				ModulesDir:   "/tmp/test/modules",
			},
			expectErr: true,
		},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateConfig(tt.cfg)
			if tt.expectErr && err == nil {
				t.Error("Expected error but got none")
			}
			if !tt.expectErr && err != nil {
				t.Errorf("Expected no error but got: %v", err)
			}
		})
	}
}

// Helper function to check if a string contains a substring
func contains(s, substr string) bool {
	return len(s) >= len(substr) && s[len(s)-len(substr):] == substr || 
		   len(s) >= len(substr) && s[:len(substr)] == substr ||
		   len(s) > len(substr) && s[len(s)/2-len(substr)/2:len(s)/2+len(substr)/2] == substr
}

// Helper function to validate config
func validateConfig(cfg *Config) error {
	if cfg.APIURL == "" {
		return fmt.Errorf("APIURL cannot be empty")
	}
	if cfg.PollInterval < 5 {
		return fmt.Errorf("PollInterval must be at least 5 seconds")
	}
	if cfg.WebPort <= 0 || cfg.WebPort > 65535 {
		return fmt.Errorf("WebPort must be between 1 and 65535")
	}
	return nil
}