package config

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"

	"github.com/spf13/viper"
)

// Config holds the application configuration
type Config struct {
	// API Configuration
	APIURL      string `mapstructure:"api-url"`
	CommunityID string `mapstructure:"community-id"`
	UserID      string `mapstructure:"user-id"`

	// Polling Configuration
	PollInterval int `mapstructure:"poll-interval"` // in seconds

	// Web Server Configuration
	WebPort int    `mapstructure:"web-port"`
	WebHost string `mapstructure:"web-host"`

	// Storage Configuration
	DataDir string `mapstructure:"data-dir"`

	// Logging Configuration
	LogLevel string `mapstructure:"log-level"`

	// WebAuthn Configuration
	WebAuthnDisplayName string `mapstructure:"webauthn-display-name"`
	WebAuthnOrigin      string `mapstructure:"webauthn-origin"`
	WebAuthnTimeout     int    `mapstructure:"webauthn-timeout"`

	// Security Configuration
	JWTSecret string `mapstructure:"jwt-secret"`

	// Module Configuration
	ModulesDir         string `mapstructure:"modules-dir"`
	ModuleTimeout      int    `mapstructure:"module-timeout"`
	MaxConcurrentTasks int    `mapstructure:"max-concurrent-tasks"`
}

// Load loads the configuration from various sources
func Load() (*Config, error) {
	// Set defaults
	setDefaults()

	// Create config instance
	cfg := &Config{}

	// Unmarshal configuration
	if err := viper.Unmarshal(cfg); err != nil {
		return nil, fmt.Errorf("failed to unmarshal config: %w", err)
	}

	// Set default data directory if not specified
	if cfg.DataDir == "" {
		homeDir, err := os.UserHomeDir()
		if err != nil {
			return nil, fmt.Errorf("failed to get user home directory: %w", err)
		}
		cfg.DataDir = filepath.Join(homeDir, ".waddlebot-bridge")
	}

	// Set default modules directory
	if cfg.ModulesDir == "" {
		cfg.ModulesDir = filepath.Join(cfg.DataDir, "modules")
	}

	// Ensure data directory exists
	if err := os.MkdirAll(cfg.DataDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create data directory: %w", err)
	}

	// Ensure modules directory exists
	if err := os.MkdirAll(cfg.ModulesDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create modules directory: %w", err)
	}

	// Set platform-specific defaults
	setPlatformDefaults(cfg)

	return cfg, nil
}

// setDefaults sets default configuration values
func setDefaults() {
	viper.SetDefault("api-url", "https://api.waddlebot.io")
	viper.SetDefault("poll-interval", 30)
	viper.SetDefault("web-port", 8080)
	viper.SetDefault("web-host", "127.0.0.1")
	viper.SetDefault("log-level", "info")
	viper.SetDefault("webauthn-display-name", "WaddleBot Bridge")
	viper.SetDefault("webauthn-origin", "http://127.0.0.1:8080")
	viper.SetDefault("webauthn-timeout", 60)
	viper.SetDefault("module-timeout", 30)
	viper.SetDefault("max-concurrent-tasks", 10)
}

// setPlatformDefaults sets platform-specific default values
func setPlatformDefaults(cfg *Config) {
	switch runtime.GOOS {
	case "darwin":
		// macOS specific defaults
		if cfg.WebAuthnDisplayName == "" {
			cfg.WebAuthnDisplayName = "WaddleBot Bridge for macOS"
		}
	case "windows":
		// Windows specific defaults
		if cfg.WebAuthnDisplayName == "" {
			cfg.WebAuthnDisplayName = "WaddleBot Bridge for Windows"
		}
	case "linux":
		// Linux specific defaults
		if cfg.WebAuthnDisplayName == "" {
			cfg.WebAuthnDisplayName = "WaddleBot Bridge for Linux"
		}
	}
}

// GetWebAuthnURL returns the WebAuthn origin URL
func (c *Config) GetWebAuthnURL() string {
	return fmt.Sprintf("http://%s:%d", c.WebHost, c.WebPort)
}

// GetAPIEndpoint returns a formatted API endpoint URL
func (c *Config) GetAPIEndpoint(path string) string {
	return fmt.Sprintf("%s%s", c.APIURL, path)
}

// GetUserAgent returns the user agent string for API requests
func (c *Config) GetUserAgent() string {
	return fmt.Sprintf("WaddleBot-Bridge/1.0.0 (%s %s)", runtime.GOOS, runtime.GOARCH)
}