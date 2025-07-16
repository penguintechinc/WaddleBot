package modules

import (
	"context"
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"plugin"
	"strings"
	"sync"
	"time"

	"github.com/sirupsen/logrus"
	"waddlebot-bridge/internal/config"
	"waddlebot-bridge/internal/logger"
	"waddlebot-bridge/internal/storage"
)

// Manager handles module loading and execution
type Manager struct {
	config      *config.Config
	storage     storage.Storage
	logger      *logrus.Logger
	modules     map[string]*Module
	moduleInfos map[string]*ModuleInfo
	mutex       sync.RWMutex
}

// ModuleInfo represents information about a module
type ModuleInfo struct {
	Name         string            `json:"name"`
	Version      string            `json:"version"`
	Description  string            `json:"description"`
	Author       string            `json:"author"`
	Actions      []ActionInfo      `json:"actions"`
	Dependencies []string          `json:"dependencies"`
	Permissions  []string          `json:"permissions"`
	Config       map[string]string `json:"config"`
	Enabled      bool              `json:"enabled"`
	LoadedAt     time.Time         `json:"loaded_at"`
	LastUsed     time.Time         `json:"last_used"`
}

// ActionInfo represents information about an action
type ActionInfo struct {
	Name        string                 `json:"name"`
	Description string                 `json:"description"`
	Parameters  map[string]interface{} `json:"parameters"`
	ReturnType  string                 `json:"return_type"`
	Timeout     int                    `json:"timeout"`
	Permissions []string               `json:"permissions"`
}

// Module represents a loaded module
type Module struct {
	Info     *ModuleInfo
	Plugin   *plugin.Plugin
	Instance ModuleInterface
	Config   map[string]string
	Enabled  bool
	LoadedAt time.Time
}

// ModuleInterface defines the interface that all modules must implement
type ModuleInterface interface {
	// Initialize initializes the module with configuration
	Initialize(config map[string]string) error
	
	// GetInfo returns module information
	GetInfo() *ModuleInfo
	
	// ExecuteAction executes a specific action
	ExecuteAction(ctx context.Context, action string, parameters map[string]string) (map[string]interface{}, error)
	
	// GetActions returns available actions
	GetActions() []ActionInfo
	
	// Cleanup cleans up module resources
	Cleanup() error
}

// NewManager creates a new module manager
func NewManager(cfg *config.Config, store storage.Storage) *Manager {
	return &Manager{
		config:      cfg,
		storage:     store,
		logger:      logger.GetLogger(),
		modules:     make(map[string]*Module),
		moduleInfos: make(map[string]*ModuleInfo),
	}
}

// LoadModules loads all modules from the modules directory
func (m *Manager) LoadModules() error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	m.logger.WithField("modules_dir", m.config.ModulesDir).Info("Loading modules")

	// Walk through modules directory
	err := filepath.WalkDir(m.config.ModulesDir, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}

		// Skip directories
		if d.IsDir() {
			return nil
		}

		// Check if it's a .so file (plugin)
		if strings.HasSuffix(path, ".so") {
			if err := m.loadModule(path); err != nil {
				m.logger.WithError(err).WithField("path", path).Error("Failed to load module")
				// Continue loading other modules
			}
		}

		return nil
	})

	if err != nil {
		return fmt.Errorf("failed to walk modules directory: %w", err)
	}

	m.logger.WithField("loaded_modules", len(m.modules)).Info("Finished loading modules")
	return nil
}

// loadModule loads a single module from a plugin file
func (m *Manager) loadModule(path string) error {
	m.logger.WithField("path", path).Debug("Loading module")

	// Load plugin
	plug, err := plugin.Open(path)
	if err != nil {
		return fmt.Errorf("failed to open plugin: %w", err)
	}

	// Look for the required symbol
	symbol, err := plug.Lookup("NewModule")
	if err != nil {
		return fmt.Errorf("failed to find NewModule symbol: %w", err)
	}

	// Assert the symbol is the correct type
	newModuleFunc, ok := symbol.(func() ModuleInterface)
	if !ok {
		return fmt.Errorf("NewModule is not of type func() ModuleInterface")
	}

	// Create module instance
	instance := newModuleFunc()
	
	// Get module info
	info := instance.GetInfo()
	if info == nil {
		return fmt.Errorf("module returned nil info")
	}

	// Load module configuration
	config, err := m.loadModuleConfig(info.Name)
	if err != nil {
		m.logger.WithError(err).WithField("module", info.Name).Warn("Failed to load module config, using defaults")
		config = make(map[string]string)
	}

	// Initialize module
	if err := instance.Initialize(config); err != nil {
		return fmt.Errorf("failed to initialize module: %w", err)
	}

	// Create module wrapper
	module := &Module{
		Info:     info,
		Plugin:   plug,
		Instance: instance,
		Config:   config,
		Enabled:  true,
		LoadedAt: time.Now(),
	}

	// Store module
	m.modules[info.Name] = module
	m.moduleInfos[info.Name] = info

	// Save module info to storage
	if err := m.saveModuleInfo(info); err != nil {
		m.logger.WithError(err).WithField("module", info.Name).Warn("Failed to save module info")
	}

	m.logger.WithFields(logrus.Fields{
		"module":  info.Name,
		"version": info.Version,
		"actions": len(info.Actions),
	}).Info("Module loaded successfully")

	return nil
}

// loadModuleConfig loads configuration for a module
func (m *Manager) loadModuleConfig(moduleName string) (map[string]string, error) {
	configKey := fmt.Sprintf("module_config_%s", moduleName)
	
	data, err := m.storage.Get(configKey)
	if err != nil {
		return nil, err
	}

	var config map[string]string
	if err := json.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("failed to unmarshal config: %w", err)
	}

	return config, nil
}

// saveModuleInfo saves module information to storage
func (m *Manager) saveModuleInfo(info *ModuleInfo) error {
	data, err := json.Marshal(info)
	if err != nil {
		return fmt.Errorf("failed to marshal module info: %w", err)
	}

	key := fmt.Sprintf("module_info_%s", info.Name)
	return m.storage.Set(key, data)
}

// ExecuteAction executes an action on a specific module
func (m *Manager) ExecuteAction(ctx context.Context, moduleName, action string, parameters map[string]string) (map[string]interface{}, error) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	// Find module
	module, exists := m.modules[moduleName]
	if !exists {
		return nil, fmt.Errorf("module %s not found", moduleName)
	}

	// Check if module is enabled
	if !module.Enabled {
		return nil, fmt.Errorf("module %s is disabled", moduleName)
	}

	// Update last used time
	module.Info.LastUsed = time.Now()

	// Create timeout context
	timeout := time.Duration(m.config.ModuleTimeout) * time.Second
	if timeout == 0 {
		timeout = 30 * time.Second
	}

	actionCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	// Execute action
	result, err := module.Instance.ExecuteAction(actionCtx, action, parameters)
	if err != nil {
		return nil, fmt.Errorf("action execution failed: %w", err)
	}

	// Update module info in storage
	m.saveModuleInfo(module.Info)

	return result, nil
}

// GetModule returns a module by name
func (m *Manager) GetModule(name string) (*Module, bool) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	module, exists := m.modules[name]
	return module, exists
}

// GetModuleInfos returns information about all loaded modules
func (m *Manager) GetModuleInfos() []ModuleInfo {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	infos := make([]ModuleInfo, 0, len(m.moduleInfos))
	for _, info := range m.moduleInfos {
		infos = append(infos, *info)
	}

	return infos
}

// GetModuleInfo returns information about a specific module
func (m *Manager) GetModuleInfo(name string) (*ModuleInfo, bool) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	info, exists := m.moduleInfos[name]
	return info, exists
}

// EnableModule enables a module
func (m *Manager) EnableModule(name string) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	module, exists := m.modules[name]
	if !exists {
		return fmt.Errorf("module %s not found", name)
	}

	module.Enabled = true
	module.Info.Enabled = true

	// Save to storage
	if err := m.saveModuleInfo(module.Info); err != nil {
		return fmt.Errorf("failed to save module info: %w", err)
	}

	m.logger.WithField("module", name).Info("Module enabled")
	return nil
}

// DisableModule disables a module
func (m *Manager) DisableModule(name string) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	module, exists := m.modules[name]
	if !exists {
		return fmt.Errorf("module %s not found", name)
	}

	module.Enabled = false
	module.Info.Enabled = false

	// Save to storage
	if err := m.saveModuleInfo(module.Info); err != nil {
		return fmt.Errorf("failed to save module info: %w", err)
	}

	m.logger.WithField("module", name).Info("Module disabled")
	return nil
}

// ReloadModule reloads a module
func (m *Manager) ReloadModule(name string) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	// Find existing module
	module, exists := m.modules[name]
	if !exists {
		return fmt.Errorf("module %s not found", name)
	}

	// Cleanup existing module
	if err := module.Instance.Cleanup(); err != nil {
		m.logger.WithError(err).WithField("module", name).Warn("Failed to cleanup module")
	}

	// Remove from maps
	delete(m.modules, name)
	delete(m.moduleInfos, name)

	// Find and reload module file
	modulePath := filepath.Join(m.config.ModulesDir, name+".so")
	if _, err := os.Stat(modulePath); os.IsNotExist(err) {
		return fmt.Errorf("module file %s not found", modulePath)
	}

	// Load module
	if err := m.loadModule(modulePath); err != nil {
		return fmt.Errorf("failed to reload module: %w", err)
	}

	m.logger.WithField("module", name).Info("Module reloaded")
	return nil
}

// UnloadModule unloads a module
func (m *Manager) UnloadModule(name string) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	module, exists := m.modules[name]
	if !exists {
		return fmt.Errorf("module %s not found", name)
	}

	// Cleanup module
	if err := module.Instance.Cleanup(); err != nil {
		m.logger.WithError(err).WithField("module", name).Warn("Failed to cleanup module")
	}

	// Remove from maps
	delete(m.modules, name)
	delete(m.moduleInfos, name)

	m.logger.WithField("module", name).Info("Module unloaded")
	return nil
}

// GetStats returns module manager statistics
func (m *Manager) GetStats() map[string]interface{} {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	enabled := 0
	disabled := 0
	for _, module := range m.modules {
		if module.Enabled {
			enabled++
		} else {
			disabled++
		}
	}

	return map[string]interface{}{
		"total_modules":    len(m.modules),
		"enabled_modules":  enabled,
		"disabled_modules": disabled,
		"modules_dir":      m.config.ModulesDir,
	}
}

// Cleanup cleans up all modules
func (m *Manager) Cleanup() error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	for name, module := range m.modules {
		if err := module.Instance.Cleanup(); err != nil {
			m.logger.WithError(err).WithField("module", name).Error("Failed to cleanup module")
		}
	}

	m.modules = make(map[string]*Module)
	m.moduleInfos = make(map[string]*ModuleInfo)

	return nil
}