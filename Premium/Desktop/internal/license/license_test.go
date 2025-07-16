package license

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestValidateLicense(t *testing.T) {
	// Create temporary directory for testing
	tmpDir := t.TempDir()
	
	// Override home directory for testing
	originalHome := os.Getenv("HOME")
	defer func() {
		os.Setenv("HOME", originalHome)
	}()
	os.Setenv("HOME", tmpDir)
	
	// Test without license acceptance
	result := ValidateLicense()
	if result {
		t.Error("Expected false for unaccepted license, but got true")
	}
	
	// Test with license acceptance
	bridgeDir := filepath.Join(tmpDir, ".waddlebot-bridge")
	if err := os.MkdirAll(bridgeDir, 0755); err != nil {
		t.Fatalf("Failed to create bridge directory: %v", err)
	}
	
	licenseFile := filepath.Join(bridgeDir, licenseAcceptanceFile)
	licenseHash := generateLicenseHash()
	if err := os.WriteFile(licenseFile, []byte(licenseHash), 0644); err != nil {
		t.Fatalf("Failed to write license file: %v", err)
	}
	
	result = ValidateLicense()
	if !result {
		t.Error("Expected true for accepted license, but got false")
	}
}

func TestHasAcceptedLicense(t *testing.T) {
	// Create temporary directory for testing
	tmpDir := t.TempDir()
	
	// Override home directory for testing
	originalHome := os.Getenv("HOME")
	defer func() {
		os.Setenv("HOME", originalHome)
	}()
	os.Setenv("HOME", tmpDir)
	
	// Test without license file
	result := hasAcceptedLicense()
	if result {
		t.Error("Expected false for missing license file, but got true")
	}
	
	// Test with invalid license file
	bridgeDir := filepath.Join(tmpDir, ".waddlebot-bridge")
	if err := os.MkdirAll(bridgeDir, 0755); err != nil {
		t.Fatalf("Failed to create bridge directory: %v", err)
	}
	
	licenseFile := filepath.Join(bridgeDir, licenseAcceptanceFile)
	if err := os.WriteFile(licenseFile, []byte("invalid-hash"), 0644); err != nil {
		t.Fatalf("Failed to write license file: %v", err)
	}
	
	result = hasAcceptedLicense()
	if result {
		t.Error("Expected false for invalid license hash, but got true")
	}
	
	// Test with valid license file
	validHash := generateLicenseHash()
	if err := os.WriteFile(licenseFile, []byte(validHash), 0644); err != nil {
		t.Fatalf("Failed to write license file: %v", err)
	}
	
	result = hasAcceptedLicense()
	if !result {
		t.Error("Expected true for valid license hash, but got false")
	}
}

func TestSaveLicenseAcceptance(t *testing.T) {
	// Create temporary directory for testing
	tmpDir := t.TempDir()
	
	// Override home directory for testing
	originalHome := os.Getenv("HOME")
	defer func() {
		os.Setenv("HOME", originalHome)
	}()
	os.Setenv("HOME", tmpDir)
	
	// Test saving license acceptance
	err := saveLicenseAcceptance()
	if err != nil {
		t.Fatalf("saveLicenseAcceptance failed: %v", err)
	}
	
	// Verify file was created
	bridgeDir := filepath.Join(tmpDir, ".waddlebot-bridge")
	licenseFile := filepath.Join(bridgeDir, licenseAcceptanceFile)
	
	if _, err := os.Stat(licenseFile); os.IsNotExist(err) {
		t.Error("License acceptance file was not created")
	}
	
	// Verify content
	content, err := os.ReadFile(licenseFile)
	if err != nil {
		t.Fatalf("Failed to read license file: %v", err)
	}
	
	expectedHash := generateLicenseHash()
	if strings.TrimSpace(string(content)) != expectedHash {
		t.Error("License file content does not match expected hash")
	}
}

func TestGenerateLicenseHash(t *testing.T) {
	// Generate hash twice to ensure consistency
	hash1 := generateLicenseHash()
	hash2 := generateLicenseHash()
	
	if hash1 != hash2 {
		t.Error("generateLicenseHash should return consistent results")
	}
	
	// Verify hash is not empty
	if hash1 == "" {
		t.Error("generateLicenseHash should not return empty string")
	}
	
	// Verify hash is hexadecimal
	if len(hash1) != 64 { // SHA256 hash should be 64 characters
		t.Errorf("Expected hash length 64, got %d", len(hash1))
	}
	
	// Verify hash contains only hexadecimal characters
	for _, char := range hash1 {
		if !((char >= '0' && char <= '9') || (char >= 'a' && char <= 'f')) {
			t.Errorf("Hash contains non-hexadecimal character: %c", char)
		}
	}
}

func TestGetLicenseInfo(t *testing.T) {
	// Create temporary directory for testing
	tmpDir := t.TempDir()
	
	// Override home directory for testing
	originalHome := os.Getenv("HOME")
	defer func() {
		os.Setenv("HOME", originalHome)
	}()
	os.Setenv("HOME", tmpDir)
	
	info := GetLicenseInfo()
	
	// Verify required fields
	if info == nil {
		t.Fatal("GetLicenseInfo returned nil")
	}
	
	if info["version"] != "1.0.0" {
		t.Errorf("Expected version '1.0.0', got %v", info["version"])
	}
	
	if info["type"] != "Premium" {
		t.Errorf("Expected type 'Premium', got %v", info["type"])
	}
	
	if info["requirement"] != "Active WaddleBot Premium Subscription" {
		t.Errorf("Expected requirement 'Active WaddleBot Premium Subscription', got %v", info["requirement"])
	}
	
	// Verify accepted field
	accepted, ok := info["accepted"].(bool)
	if !ok {
		t.Error("Expected 'accepted' field to be boolean")
	}
	
	// Should be false initially
	if accepted {
		t.Error("Expected 'accepted' to be false initially")
	}
	
	// Save license acceptance and check again
	saveLicenseAcceptance()
	
	info = GetLicenseInfo()
	accepted, ok = info["accepted"].(bool)
	if !ok {
		t.Error("Expected 'accepted' field to be boolean")
	}
	
	if !accepted {
		t.Error("Expected 'accepted' to be true after saving acceptance")
	}
}

func TestLicenseConstants(t *testing.T) {
	// Test that license text is not empty
	if LicenseText == "" {
		t.Error("LicenseText should not be empty")
	}
	
	// Test that license text contains required components
	requiredComponents := []string{
		"WaddleBot Premium Desktop Bridge License Agreement",
		"Copyright (c) 2024 WaddleBot",
		"PREMIUM SOFTWARE LICENSE",
		"GRANT OF LICENSE",
		"RESTRICTIONS",
		"SUBSCRIPTION REQUIREMENT",
		"TERMINATION",
		"DISCLAIMER",
		"LIMITATION OF LIABILITY",
	}
	
	for _, component := range requiredComponents {
		if !strings.Contains(LicenseText, component) {
			t.Errorf("LicenseText should contain '%s'", component)
		}
	}
	
	// Test license acceptance file constant
	if licenseAcceptanceFile == "" {
		t.Error("licenseAcceptanceFile should not be empty")
	}
	
	expectedFile := ".license-accepted"
	if licenseAcceptanceFile != expectedFile {
		t.Errorf("Expected licenseAcceptanceFile '%s', got '%s'", expectedFile, licenseAcceptanceFile)
	}
}

func TestLicenseTextContent(t *testing.T) {
	// Test that license text mentions premium subscription
	if !strings.Contains(LicenseText, "premium subscription") {
		t.Error("LicenseText should mention 'premium subscription'")
	}
	
	// Test that license text mentions WaddleBot Premium
	if !strings.Contains(LicenseText, "WaddleBot Premium") {
		t.Error("LicenseText should mention 'WaddleBot Premium'")
	}
	
	// Test that license text includes version
	if !strings.Contains(LicenseText, "v1.0.0") {
		t.Error("LicenseText should include version 'v1.0.0'")
	}
	
	// Test that license text includes restrictions
	restrictions := []string{
		"may NOT distribute",
		"may NOT reverse engineer",
		"may NOT use this software without an active",
	}
	
	for _, restriction := range restrictions {
		if !strings.Contains(LicenseText, restriction) {
			t.Errorf("LicenseText should contain restriction: '%s'", restriction)
		}
	}
}

func TestDisplayLicenseInfo(t *testing.T) {
	// This test mainly verifies the function doesn't panic
	// In a real test environment, you might want to capture stdout
	
	// Create temporary directory for testing
	tmpDir := t.TempDir()
	
	// Override home directory for testing
	originalHome := os.Getenv("HOME")
	defer func() {
		os.Setenv("HOME", originalHome)
	}()
	os.Setenv("HOME", tmpDir)
	
	// Should not panic
	defer func() {
		if r := recover(); r != nil {
			t.Errorf("DisplayLicenseInfo panicked: %v", r)
		}
	}()
	
	DisplayLicenseInfo()
}

func TestLicenseValidationEdgeCases(t *testing.T) {
	// Test with invalid home directory
	originalHome := os.Getenv("HOME")
	defer func() {
		os.Setenv("HOME", originalHome)
	}()
	
	// Set invalid home directory
	os.Setenv("HOME", "/nonexistent/directory")
	
	result := hasAcceptedLicense()
	if result {
		t.Error("Expected false for invalid home directory, but got true")
	}
	
	// Test saveLicenseAcceptance with invalid home directory
	err := saveLicenseAcceptance()
	if err == nil {
		t.Error("Expected error for invalid home directory, but got none")
	}
}

func TestLicenseFilePermissions(t *testing.T) {
	// Create temporary directory for testing
	tmpDir := t.TempDir()
	
	// Override home directory for testing
	originalHome := os.Getenv("HOME")
	defer func() {
		os.Setenv("HOME", originalHome)
	}()
	os.Setenv("HOME", tmpDir)
	
	// Save license acceptance
	err := saveLicenseAcceptance()
	if err != nil {
		t.Fatalf("saveLicenseAcceptance failed: %v", err)
	}
	
	// Check file permissions
	licenseFile := filepath.Join(tmpDir, ".waddlebot-bridge", licenseAcceptanceFile)
	info, err := os.Stat(licenseFile)
	if err != nil {
		t.Fatalf("Failed to stat license file: %v", err)
	}
	
	expectedPerms := os.FileMode(0644)
	if info.Mode() != expectedPerms {
		t.Errorf("Expected file permissions %v, got %v", expectedPerms, info.Mode())
	}
	
	// Check directory permissions
	bridgeDir := filepath.Join(tmpDir, ".waddlebot-bridge")
	info, err = os.Stat(bridgeDir)
	if err != nil {
		t.Fatalf("Failed to stat bridge directory: %v", err)
	}
	
	expectedDirPerms := os.FileMode(0755) | os.ModeDir
	if info.Mode() != expectedDirPerms {
		t.Errorf("Expected directory permissions %v, got %v", expectedDirPerms, info.Mode())
	}
}