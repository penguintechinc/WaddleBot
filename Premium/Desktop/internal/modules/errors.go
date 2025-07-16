package modules

import "fmt"

// Common module errors
var (
	ErrModuleNotFound     = fmt.Errorf("module not found")
	ErrModuleDisabled     = fmt.Errorf("module is disabled")
	ErrActionNotFound     = fmt.Errorf("action not found")
	ErrActionFailed       = fmt.Errorf("action execution failed")
	ErrInvalidParameters  = fmt.Errorf("invalid parameters")
	ErrModuleInitFailed   = fmt.Errorf("module initialization failed")
	ErrModuleLoadFailed   = fmt.Errorf("module load failed")
	ErrPermissionDenied   = fmt.Errorf("permission denied")
	ErrTimeout            = fmt.Errorf("operation timeout")
)