package testutils

import "fmt"

// Common test errors
var (
	ErrTestFailed        = fmt.Errorf("test failed")
	ErrTestTimeout       = fmt.Errorf("test timeout")
	ErrTestSetupFailed   = fmt.Errorf("test setup failed")
	ErrTestExpected      = fmt.Errorf("expected test error")
	ErrTestUnexpected    = fmt.Errorf("unexpected test error")
	ErrTestNotImplemented = fmt.Errorf("test not implemented")
)