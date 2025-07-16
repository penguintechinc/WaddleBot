package license

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
	"runtime"
	"strings"
	"time"
)

const (
	// License text that users must accept
	LicenseText = `
WaddleBot Premium Desktop Bridge License Agreement

Copyright (c) 2024 WaddleBot

PREMIUM SOFTWARE LICENSE

This software is licensed exclusively to users with active WaddleBot Premium subscriptions.

1. GRANT OF LICENSE
   Subject to the terms and conditions of this Agreement, WaddleBot grants you a 
   non-exclusive, non-transferable license to use the WaddleBot Premium Desktop Bridge 
   software solely for your personal or business use with WaddleBot Premium services.

2. RESTRICTIONS
   - You may NOT distribute, sublicense, or share this software
   - You may NOT reverse engineer, decompile, or disassemble this software
   - You may NOT use this software without an active WaddleBot Premium subscription
   - You may NOT use this software for commercial purposes without proper licensing

3. SUBSCRIPTION REQUIREMENT
   This software requires an active WaddleBot Premium subscription. Use of this software 
   without a valid subscription is strictly prohibited and constitutes a violation of 
   this license agreement.

4. TERMINATION
   This license terminates automatically if your WaddleBot Premium subscription expires 
   or is cancelled. You must immediately cease all use of the software upon termination.

5. DISCLAIMER
   This software is provided "AS IS" without warranty of any kind. WaddleBot disclaims 
   all warranties, express or implied, including but not limited to warranties of 
   merchantability and fitness for a particular purpose.

6. LIMITATION OF LIABILITY
   In no event shall WaddleBot be liable for any damages arising out of or in connection 
   with the use or performance of this software.

By using this software, you acknowledge that you have read, understood, and agree to be 
bound by the terms of this license agreement.

WaddleBot Premium Desktop Bridge v1.0.0
`

	// License acceptance marker
	licenseAcceptanceFile = ".license-accepted"
)

// ValidateLicense checks if the user has accepted the premium license
func ValidateLicense() bool {
	// Check if license has been accepted
	if !hasAcceptedLicense() {
		return promptForLicenseAcceptance()
	}
	
	// TODO: In production, this should verify the user's premium subscription status
	// For now, we'll assume the license is valid if accepted
	return true
}

// hasAcceptedLicense checks if the user has previously accepted the license
func hasAcceptedLicense() bool {
	homeDir, err := os.UserHomeDir()
	if err != nil {
		return false
	}

	licenseFile := fmt.Sprintf("%s/.waddlebot-bridge/%s", homeDir, licenseAcceptanceFile)
	
	// Check if license acceptance file exists
	if _, err := os.Stat(licenseFile); os.IsNotExist(err) {
		return false
	}

	// Read the acceptance file and verify the hash
	content, err := os.ReadFile(licenseFile)
	if err != nil {
		return false
	}

	expectedHash := generateLicenseHash()
	return strings.TrimSpace(string(content)) == expectedHash
}

// promptForLicenseAcceptance displays the license and prompts for acceptance
func promptForLicenseAcceptance() bool {
	fmt.Println(LicenseText)
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("WaddleBot Premium Desktop Bridge License Agreement")
	fmt.Println(strings.Repeat("=", 80))
	
	fmt.Print("\nDo you have an active WaddleBot Premium subscription? (y/N): ")
	var hasSubscription string
	fmt.Scanln(&hasSubscription)
	
	if strings.ToLower(hasSubscription) != "y" && strings.ToLower(hasSubscription) != "yes" {
		fmt.Println("\nThis software requires an active WaddleBot Premium subscription.")
		fmt.Println("Please visit https://waddlebot.io/premium to subscribe.")
		return false
	}

	fmt.Print("\nDo you accept the terms of the license agreement? (y/N): ")
	var acceptance string
	fmt.Scanln(&acceptance)

	if strings.ToLower(acceptance) != "y" && strings.ToLower(acceptance) != "yes" {
		fmt.Println("\nYou must accept the license agreement to use this software.")
		return false
	}

	// Save license acceptance
	if err := saveLicenseAcceptance(); err != nil {
		fmt.Printf("Warning: Failed to save license acceptance: %v\n", err)
	}

	fmt.Println("\nLicense accepted. Welcome to WaddleBot Premium Desktop Bridge!")
	return true
}

// saveLicenseAcceptance saves the license acceptance to disk
func saveLicenseAcceptance() error {
	homeDir, err := os.UserHomeDir()
	if err != nil {
		return fmt.Errorf("failed to get user home directory: %w", err)
	}

	bridgeDir := fmt.Sprintf("%s/.waddlebot-bridge", homeDir)
	if err := os.MkdirAll(bridgeDir, 0755); err != nil {
		return fmt.Errorf("failed to create bridge directory: %w", err)
	}

	licenseFile := fmt.Sprintf("%s/%s", bridgeDir, licenseAcceptanceFile)
	licenseHash := generateLicenseHash()

	if err := os.WriteFile(licenseFile, []byte(licenseHash), 0644); err != nil {
		return fmt.Errorf("failed to write license acceptance file: %w", err)
	}

	return nil
}

// generateLicenseHash generates a hash of the license text and system info
func generateLicenseHash() string {
	// Combine license text with system information for uniqueness
	data := fmt.Sprintf("%s|%s|%s|%d", 
		LicenseText, 
		runtime.GOOS, 
		runtime.GOARCH, 
		time.Now().Unix()/86400, // Day-based timestamp
	)
	
	hash := sha256.Sum256([]byte(data))
	return hex.EncodeToString(hash[:])
}

// GetLicenseInfo returns information about the current license
func GetLicenseInfo() map[string]interface{} {
	return map[string]interface{}{
		"accepted":    hasAcceptedLicense(),
		"version":     "1.0.0",
		"type":        "Premium",
		"platform":    fmt.Sprintf("%s/%s", runtime.GOOS, runtime.GOARCH),
		"requirement": "Active WaddleBot Premium Subscription",
	}
}

// DisplayLicenseInfo displays the current license information
func DisplayLicenseInfo() {
	info := GetLicenseInfo()
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("WaddleBot Premium Desktop Bridge License Info")
	fmt.Println(strings.Repeat("=", 50))
	fmt.Printf("Version: %s\n", info["version"])
	fmt.Printf("Type: %s\n", info["type"])
	fmt.Printf("Platform: %s\n", info["platform"])
	fmt.Printf("Requirement: %s\n", info["requirement"])
	fmt.Printf("Accepted: %t\n", info["accepted"])
	fmt.Println(strings.Repeat("=", 50))
}