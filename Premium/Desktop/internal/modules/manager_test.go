package modules

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"testing"
	"time"

	"waddlebot-bridge/internal/config"
	"waddlebot-bridge/internal/testutils"
)

func TestNewManager(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	
	manager := NewManager(cfg, storage)
	
	if manager == nil {
		t.Fatal("Expected non-nil manager")
	}
	
	if manager.config != cfg {
		t.Error("Expected config to be set")
	}
	
	if manager.storage != storage {
		t.Error("Expected storage to be set")
	}
	
	if manager.modules == nil {
		t.Error("Expected modules map to be initialized")
	}
	
	if manager.moduleInfos == nil {
		t.Error("Expected moduleInfos map to be initialized")
	}
}

func TestManager_GetModuleInfos(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager := NewManager(cfg, storage)
	
	// Test with no modules
	infos := manager.GetModuleInfos()
	if len(infos) != 0 {
		t.Errorf("Expected 0 modules, got %d", len(infos))
	}
	
	// Add a test module
	testModule := testutils.TestModule("test-module")
	module := &Module{
		Info:     testModule.GetInfo(),
		Instance: testModule,
		Config:   make(map[string]string),
		Enabled:  true,
		LoadedAt: time.Now(),
	}
	
	manager.modules[testModule.GetInfo().Name] = module
	manager.moduleInfos[testModule.GetInfo().Name] = testModule.GetInfo()
	
	// Test with one module
	infos = manager.GetModuleInfos()
	if len(infos) != 1 {
		t.Errorf("Expected 1 module, got %d", len(infos))
	}
	
	if infos[0].Name != "test-module" {
		t.Errorf("Expected module name 'test-module', got %s", infos[0].Name)
	}
}

func TestManager_GetModule(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager := NewManager(cfg, storage)
	
	// Test non-existent module
	_, exists := manager.GetModule("nonexistent")
	if exists {
		t.Error("Expected false for non-existent module")
	}
	
	// Add a test module
	testModule := testutils.TestModule("test-module")
	module := &Module{
		Info:     testModule.GetInfo(),
		Instance: testModule,
		Config:   make(map[string]string),
		Enabled:  true,
		LoadedAt: time.Now(),
	}
	
	manager.modules[testModule.GetInfo().Name] = module
	
	// Test existing module
	retrievedModule, exists := manager.GetModule("test-module")
	if !exists {
		t.Error("Expected true for existing module")
	}
	
	if retrievedModule.Info.Name != "test-module" {
		t.Errorf("Expected module name 'test-module', got %s", retrievedModule.Info.Name)
	}
}

func TestManager_GetModuleInfo(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager := NewManager(cfg, storage)
	
	// Test non-existent module
	_, exists := manager.GetModuleInfo("nonexistent")
	if exists {
		t.Error("Expected false for non-existent module")
	}
	
	// Add a test module
	testModule := testutils.TestModule("test-module")
	manager.moduleInfos[testModule.GetInfo().Name] = testModule.GetInfo()
	
	// Test existing module
	info, exists := manager.GetModuleInfo("test-module")
	if !exists {
		t.Error("Expected true for existing module")
	}
	
	if info.Name != "test-module" {
		t.Errorf("Expected module name 'test-module', got %s", info.Name)
	}
}

func TestManager_ExecuteAction(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager := NewManager(cfg, storage)
	
	// Test non-existent module
	ctx, cancel := testutils.TestContext()
	defer cancel()
	
	_, err := manager.ExecuteAction(ctx, "nonexistent", "ping", map[string]string{})
	if err == nil {
		t.Error("Expected error for non-existent module")
	}
	
	// Add a test module
	testModule := testutils.TestModule("test-module")
	module := &Module{
		Info:     testModule.GetInfo(),
		Instance: testModule,
		Config:   make(map[string]string),
		Enabled:  true,
		LoadedAt: time.Now(),
	}
	
	manager.modules[testModule.GetInfo().Name] = module
	manager.moduleInfos[testModule.GetInfo().Name] = testModule.GetInfo()
	
	// Test successful action execution
	result, err := manager.ExecuteAction(ctx, "test-module", "ping", map[string]string{})
	if err != nil {
		t.Fatalf("ExecuteAction failed: %v", err)
	}
	
	if result["message"] != "pong" {
		t.Errorf("Expected message 'pong', got %v", result["message"])
	}
	
	// Test echo action with parameter
	result, err = manager.ExecuteAction(ctx, "test-module", "echo", map[string]string{"message": "test"})
	if err != nil {
		t.Fatalf("ExecuteAction failed: %v", err)
	}
	
	if result["echo"] != "test" {
		t.Errorf("Expected echo 'test', got %v", result["echo"])
	}
	
	// Test action failure
	_, err = manager.ExecuteAction(ctx, "test-module", "fail", map[string]string{})
	if err == nil {
		t.Error("Expected error for fail action")
	}
}

func TestManager_ExecuteAction_DisabledModule(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager := NewManager(cfg, storage)
	
	// Add a disabled test module
	testModule := testutils.TestModule("test-module")
	module := &Module{
		Info:     testModule.GetInfo(),
		Instance: testModule,
		Config:   make(map[string]string),
		Enabled:  false, // Disabled
		LoadedAt: time.Now(),
	}
	
	manager.modules[testModule.GetInfo().Name] = module
	
	// Test action execution on disabled module
	ctx, cancel := testutils.TestContext()
	defer cancel()
	
	_, err := manager.ExecuteAction(ctx, "test-module", "ping", map[string]string{})
	if err == nil {
		t.Error("Expected error for disabled module")
	}
	
	if err.Error() != "module test-module is disabled" {
		t.Errorf("Expected 'module test-module is disabled' error, got %v", err)
	}
}

func TestManager_EnableModule(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager := NewManager(cfg, storage)
	
	// Test non-existent module
	err := manager.EnableModule("nonexistent")
	if err == nil {
		t.Error("Expected error for non-existent module")
	}
	
	// Add a disabled test module
	testModule := testutils.TestModule("test-module")
	module := &Module{
		Info:     testModule.GetInfo(),
		Instance: testModule,
		Config:   make(map[string]string),
		Enabled:  false,
		LoadedAt: time.Now(),
	}
	
	manager.modules[testModule.GetInfo().Name] = module
	manager.moduleInfos[testModule.GetInfo().Name] = testModule.GetInfo()
	
	// Test enabling module
	err = manager.EnableModule("test-module")
	if err != nil {
		t.Fatalf("EnableModule failed: %v", err)
	}
	
	// Verify module is enabled
	if !module.Enabled {
		t.Error("Expected module to be enabled")
	}
	
	if !module.Info.Enabled {
		t.Error("Expected module info to be enabled")
	}
}

func TestManager_DisableModule(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager := NewManager(cfg, storage)
	
	// Test non-existent module
	err := manager.DisableModule("nonexistent")
	if err == nil {
		t.Error("Expected error for non-existent module")
	}
	
	// Add an enabled test module
	testModule := testutils.TestModule("test-module")
	module := &Module{
		Info:     testModule.GetInfo(),
		Instance: testModule,
		Config:   make(map[string]string),
		Enabled:  true,
		LoadedAt: time.Now(),
	}
	
	manager.modules[testModule.GetInfo().Name] = module
	manager.moduleInfos[testModule.GetInfo().Name] = testModule.GetInfo()
	
	// Test disabling module
	err = manager.DisableModule("test-module")
	if err != nil {
		t.Fatalf("DisableModule failed: %v", err)
	}
	
	// Verify module is disabled
	if module.Enabled {
		t.Error("Expected module to be disabled")
	}
	
	if module.Info.Enabled {
		t.Error("Expected module info to be disabled")
	}
}

func TestManager_UnloadModule(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager := NewManager(cfg, storage)
	
	// Test non-existent module
	err := manager.UnloadModule("nonexistent")
	if err == nil {
		t.Error("Expected error for non-existent module")
	}
	
	// Add a test module
	testModule := testutils.TestModule("test-module")
	module := &Module{
		Info:     testModule.GetInfo(),
		Instance: testModule,
		Config:   make(map[string]string),
		Enabled:  true,
		LoadedAt: time.Now(),
	}
	
	manager.modules[testModule.GetInfo().Name] = module
	manager.moduleInfos[testModule.GetInfo().Name] = testModule.GetInfo()
	
	// Verify module exists
	_, exists := manager.GetModule("test-module")
	if !exists {
		t.Error("Expected module to exist before unloading")
	}
	
	// Test unloading module
	err = manager.UnloadModule("test-module")
	if err != nil {
		t.Fatalf("UnloadModule failed: %v", err)
	}
	
	// Verify module no longer exists
	_, exists = manager.GetModule("test-module")
	if exists {
		t.Error("Expected module to not exist after unloading")
	}
	
	_, exists = manager.GetModuleInfo("test-module")
	if exists {
		t.Error("Expected module info to not exist after unloading")
	}
}

func TestManager_GetStats(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager := NewManager(cfg, storage)
	
	// Test with no modules
	stats := manager.GetStats()
	
	if stats == nil {
		t.Fatal("Expected non-nil stats")
	}
	
	expectedTotal := 0
	expectedEnabled := 0
	expectedDisabled := 0
	
	if stats["total_modules"] != expectedTotal {
		t.Errorf("Expected total_modules %d, got %v", expectedTotal, stats["total_modules"])
	}
	
	if stats["enabled_modules"] != expectedEnabled {
		t.Errorf("Expected enabled_modules %d, got %v", expectedEnabled, stats["enabled_modules"])
	}
	
	if stats["disabled_modules"] != expectedDisabled {
		t.Errorf("Expected disabled_modules %d, got %v", expectedDisabled, stats["disabled_modules"])
	}
	
	// Add enabled and disabled modules
	enabledModule := testutils.TestModule("enabled-module")
	disabledModule := testutils.TestModule("disabled-module")
	
	manager.modules["enabled-module"] = &Module{
		Info:     enabledModule.GetInfo(),
		Instance: enabledModule,
		Enabled:  true,
		LoadedAt: time.Now(),
	}
	
	manager.modules["disabled-module"] = &Module{
		Info:     disabledModule.GetInfo(),
		Instance: disabledModule,
		Enabled:  false,
		LoadedAt: time.Now(),
	}
	
	// Test with modules
	stats = manager.GetStats()
	
	expectedTotal = 2
	expectedEnabled = 1
	expectedDisabled = 1
	
	if stats["total_modules"] != expectedTotal {
		t.Errorf("Expected total_modules %d, got %v", expectedTotal, stats["total_modules"])
	}
	
	if stats["enabled_modules"] != expectedEnabled {
		t.Errorf("Expected enabled_modules %d, got %v", expectedEnabled, stats["enabled_modules"])
	}
	
	if stats["disabled_modules"] != expectedDisabled {
		t.Errorf("Expected disabled_modules %d, got %v", expectedDisabled, stats["disabled_modules"])
	}
	
	if stats["modules_dir"] != cfg.ModulesDir {
		t.Errorf("Expected modules_dir %s, got %v", cfg.ModulesDir, stats["modules_dir"])
	}
}

func TestManager_Cleanup(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager := NewManager(cfg, storage)
	
	// Add test modules
	testModule1 := testutils.TestModule("test-module1")
	testModule2 := testutils.TestModule("test-module2")
	
	manager.modules["test-module1"] = &Module{
		Info:     testModule1.GetInfo(),
		Instance: testModule1,
		Enabled:  true,
		LoadedAt: time.Now(),
	}
	
	manager.modules["test-module2"] = &Module{
		Info:     testModule2.GetInfo(),
		Instance: testModule2,
		Enabled:  true,
		LoadedAt: time.Now(),
	}
	
	manager.moduleInfos["test-module1"] = testModule1.GetInfo()
	manager.moduleInfos["test-module2"] = testModule2.GetInfo()
	
	// Verify modules exist
	if len(manager.modules) != 2 {
		t.Errorf("Expected 2 modules before cleanup, got %d", len(manager.modules))
	}
	
	if len(manager.moduleInfos) != 2 {
		t.Errorf("Expected 2 module infos before cleanup, got %d", len(manager.moduleInfos))
	}
	
	// Test cleanup
	err := manager.Cleanup()
	if err != nil {
		t.Fatalf("Cleanup failed: %v", err)
	}
	
	// Verify modules are cleaned up
	if len(manager.modules) != 0 {
		t.Errorf("Expected 0 modules after cleanup, got %d", len(manager.modules))
	}
	
	if len(manager.moduleInfos) != 0 {
		t.Errorf("Expected 0 module infos after cleanup, got %d", len(manager.moduleInfos))
	}
}

func TestManager_LoadModuleConfig(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager := NewManager(cfg, storage)
	
	moduleName := "test-module"
	expectedConfig := map[string]string{
		"key1": "value1",
		"key2": "value2",
	}
	
	// Test non-existent config
	_, err := manager.loadModuleConfig(moduleName)
	if err == nil {
		t.Error("Expected error for non-existent config")
	}
	
	// Save config to storage
	configData, _ := json.Marshal(expectedConfig)
	storage.Set(fmt.Sprintf("module_config_%s", moduleName), configData)
	
	// Test loading config
	config, err := manager.loadModuleConfig(moduleName)
	if err != nil {
		t.Fatalf("loadModuleConfig failed: %v", err)
	}
	
	if len(config) != len(expectedConfig) {
		t.Errorf("Expected %d config items, got %d", len(expectedConfig), len(config))
	}
	
	for key, expectedValue := range expectedConfig {
		if config[key] != expectedValue {
			t.Errorf("Expected config[%s] = %s, got %s", key, expectedValue, config[key])
		}
	}
}

func TestManager_SaveModuleInfo(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager := NewManager(cfg, storage)
	
	testModule := testutils.TestModule("test-module")
	info := testModule.GetInfo()
	
	// Test saving module info
	err := manager.saveModuleInfo(info)
	if err != nil {
		t.Fatalf("saveModuleInfo failed: %v", err)
	}
	
	// Verify info was saved
	key := fmt.Sprintf("module_info_%s", info.Name)
	data, err := storage.Get(key)
	if err != nil {
		t.Fatalf("Failed to get saved module info: %v", err)
	}
	
	var savedInfo ModuleInfo
	err = json.Unmarshal(data, &savedInfo)
	if err != nil {
		t.Fatalf("Failed to unmarshal saved info: %v", err)
	}
	
	if savedInfo.Name != info.Name {
		t.Errorf("Expected saved name %s, got %s", info.Name, savedInfo.Name)
	}
	
	if savedInfo.Version != info.Version {
		t.Errorf("Expected saved version %s, got %s", info.Version, savedInfo.Version)
	}
}

func TestManager_ExecuteAction_Timeout(t *testing.T) {
	cfg := testutils.TestConfig()
	cfg.ModuleTimeout = 1 // 1 second timeout
	storage := testutils.NewMockStorage()
	manager := NewManager(cfg, storage)
	
	// Create a test module with a slow action
	testModule := testutils.NewMockModule("slow-module")
	testModule.AddAction("slow", func(ctx context.Context, parameters map[string]string) (map[string]interface{}, error) {
		// Sleep longer than timeout
		time.Sleep(2 * time.Second)
		return map[string]interface{}{"result": "done"}, nil
	})
	
	module := &Module{
		Info:     testModule.GetInfo(),
		Instance: testModule,
		Config:   make(map[string]string),
		Enabled:  true,
		LoadedAt: time.Now(),
	}
	
	manager.modules[testModule.GetInfo().Name] = module
	
	// Test timeout
	ctx, cancel := testutils.TestContext()
	defer cancel()
	
	_, err := manager.ExecuteAction(ctx, "slow-module", "slow", map[string]string{})
	if err == nil {
		t.Error("Expected timeout error")
	}
}

func TestManager_ConcurrentExecution(t *testing.T) {
	cfg := testutils.TestConfig()
	storage := testutils.NewMockStorage()
	manager := NewManager(cfg, storage)
	
	// Add a test module
	testModule := testutils.TestModule("test-module")
	module := &Module{
		Info:     testModule.GetInfo(),
		Instance: testModule,
		Config:   make(map[string]string),
		Enabled:  true,
		LoadedAt: time.Now(),
	}
	
	manager.modules[testModule.GetInfo().Name] = module
	manager.moduleInfos[testModule.GetInfo().Name] = testModule.GetInfo()
	
	// Test concurrent execution
	numGoroutines := 10
	done := make(chan bool)
	
	for i := 0; i < numGoroutines; i++ {
		go func() {
			defer func() { done <- true }()
			
			ctx, cancel := testutils.TestContext()
			defer cancel()
			
			result, err := manager.ExecuteAction(ctx, "test-module", "ping", map[string]string{})
			if err != nil {
				t.Errorf("Concurrent ExecuteAction failed: %v", err)
				return
			}
			
			if result["message"] != "pong" {
				t.Errorf("Expected message 'pong', got %v", result["message"])
			}
		}()
	}
	
	// Wait for all goroutines to complete
	for i := 0; i < numGoroutines; i++ {
		<-done
	}
}

