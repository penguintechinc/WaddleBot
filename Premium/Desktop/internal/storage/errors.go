package storage

import "fmt"

// Common storage errors
var (
	ErrKeyNotFound    = fmt.Errorf("key not found")
	ErrBucketNotFound = fmt.Errorf("bucket not found")
	ErrInvalidKey     = fmt.Errorf("invalid key")
	ErrStorageClosed  = fmt.Errorf("storage is closed")
	ErrPermission     = fmt.Errorf("permission denied")
)