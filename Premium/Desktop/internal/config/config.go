package config

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"time"

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

	// OBS Configuration
	OBS OBSConfig `mapstructure:"obs"`

	// Gateway Configuration
	Gateway GatewayConfig `mapstructure:"gateway"`

	// Scripting Configuration
	Scripting ScriptingConfig `mapstructure:"scripting"`
}

// OBSConfig holds OBS WebSocket connection configuration
type OBSConfig struct {
	Enabled              bool          `mapstructure:"enabled"`
	Host                 string        `mapstructure:"host"`
	Port                 int           `mapstructure:"port"`
	Password             string        `mapstructure:"password"`
	AutoReconnect        bool          `mapstructure:"auto-reconnect"`
	ReconnectInterval    time.Duration `mapstructure:"reconnect-interval"`
	MaxReconnectInterval time.Duration `mapstructure:"max-reconnect-interval"`
	Timeout              time.Duration `mapstructure:"timeout"`
}

// GatewayConfig holds local API gateway configuration
type GatewayConfig struct {
	Enabled        bool     `mapstructure:"enabled"`
	Host           string   `mapstructure:"host"`
	Port           int      `mapstructure:"port"`
	EnableAuth     bool     `mapstructure:"enable-auth"`
	APIKey         string   `mapstructure:"api-key"`
	RateLimitRPS   int      `mapstructure:"rate-limit-rps"`
	EnableCORS     bool     `mapstructure:"enable-cors"`
	AllowedOrigins []string `mapstructure:"allowed-origins"`
	WSPingInterval int      `mapstructure:"ws-ping-interval"`
}

// ScriptingConfig holds scripting engine configuration
type ScriptingConfig struct {
	Enabled          bool   `mapstructure:"enabled"`
	EnableLua        bool   `mapstructure:"enable-lua"`
	EnablePython     bool   `mapstructure:"enable-python"`
	EnablePowerShell bool   `mapstructure:"enable-powershell"`
	EnableBash       bool   `mapstructure:"enable-bash"`
	ScriptsDir       string `mapstructure:"scripts-dir"`
	DefaultTimeout   int    `mapstructure:"default-timeout"`
	MaxMemoryMB      int    `mapstructure:"max-memory-mb"`
	AllowNetwork     bool   `mapstructure:"allow-network"`
	AllowFileSystem  bool   `mapstructure:"allow-filesystem"`
	PythonPath       string `mapstructure:"python-path"`
	PowerShellPath   string `mapstructure:"powershell-path"`
	BashPath         string `mapstructure:"bash-path"`
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

	// Set default scripts directory
	if cfg.Scripting.ScriptsDir == "" {
		cfg.Scripting.ScriptsDir = filepath.Join(cfg.DataDir, "scripts")
	}

	// Ensure data directory exists
	if err := os.MkdirAll(cfg.DataDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create data directory: %w", err)
	}

	// Ensure modules directory exists
	if err := os.MkdirAll(cfg.ModulesDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create modules directory: %w", err)
	}

	// Ensure scripts directory exists if scripting is enabled
	if cfg.Scripting.Enabled {
		if err := os.MkdirAll(cfg.Scripting.ScriptsDir, 0755); err != nil {
			return nil, fmt.Errorf("failed to create scripts directory: %w", err)
		}
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
	viper.SetDefault("webauthn-display-name", "Waddles Bridge")
	viper.SetDefault("webauthn-origin", "http://127.0.0.1:8080")
	viper.SetDefault("webauthn-timeout", 60)
	viper.SetDefault("module-timeout", 30)
	viper.SetDefault("max-concurrent-tasks", 10)

	// OBS defaults
	viper.SetDefault("obs.enabled", true)
	viper.SetDefault("obs.host", "localhost")
	viper.SetDefault("obs.port", 4455)
	viper.SetDefault("obs.password", "")
	viper.SetDefault("obs.auto-reconnect", true)
	viper.SetDefault("obs.reconnect-interval", time.Second)
	viper.SetDefault("obs.max-reconnect-interval", 30*time.Second)
	viper.SetDefault("obs.timeout", 10*time.Second)

	// Gateway defaults
	viper.SetDefault("gateway.enabled", true)
	viper.SetDefault("gateway.host", "127.0.0.1")
	viper.SetDefault("gateway.port", 8090)
	viper.SetDefault("gateway.enable-auth", true)
	viper.SetDefault("gateway.api-key", "")
	viper.SetDefault("gateway.rate-limit-rps", 100)
	viper.SetDefault("gateway.enable-cors", false)
	viper.SetDefault("gateway.allowed-origins", []string{})
	viper.SetDefault("gateway.ws-ping-interval", 30)

	// Scripting defaults
	viper.SetDefault("scripting.enabled", true)
	viper.SetDefault("scripting.enable-lua", true)
	viper.SetDefault("scripting.enable-python", true)
	viper.SetDefault("scripting.enable-powershell", true)
	viper.SetDefault("scripting.enable-bash", true)
	viper.SetDefault("scripting.scripts-dir", "")
	viper.SetDefault("scripting.default-timeout", 30)
	viper.SetDefault("scripting.max-memory-mb", 256)
	viper.SetDefault("scripting.allow-network", false)
	viper.SetDefault("scripting.allow-filesystem", false)
	viper.SetDefault("scripting.python-path", "python3")
	viper.SetDefault("scripting.powershell-path", "pwsh")
	viper.SetDefault("scripting.bash-path", "bash")
}

// setPlatformDefaults sets platform-specific default values
func setPlatformDefaults(cfg *Config) {
	switch runtime.GOOS {
	case "darwin":
		// macOS specific defaults
		if cfg.WebAuthnDisplayName == "" {
			cfg.WebAuthnDisplayName = "Waddles Bridge for macOS"
		}
	case "windows":
		// Windows specific defaults
		if cfg.WebAuthnDisplayName == "" {
			cfg.WebAuthnDisplayName = "Waddles Bridge for Windows"
		}
	case "linux":
		// Linux specific defaults
		if cfg.WebAuthnDisplayName == "" {
			cfg.WebAuthnDisplayName = "Waddles Bridge for Linux"
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
	return fmt.Sprintf("Waddles-Bridge/1.0.0 (%s %s)", runtime.GOOS, runtime.GOARCH)
}