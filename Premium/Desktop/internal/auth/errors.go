package auth

import "fmt"

// Common auth errors
var (
	ErrSessionNotFound     = fmt.Errorf("session not found")
	ErrSessionExpired      = fmt.Errorf("session expired")
	ErrInvalidCredentials  = fmt.Errorf("invalid credentials")
	ErrUserNotFound        = fmt.Errorf("user not found")
	ErrRegistrationFailed  = fmt.Errorf("registration failed")
	ErrAuthenticationFailed = fmt.Errorf("authentication failed")
	ErrInvalidToken        = fmt.Errorf("invalid token")
	ErrTokenExpired        = fmt.Errorf("token expired")
	ErrPermissionDenied    = fmt.Errorf("permission denied")
)