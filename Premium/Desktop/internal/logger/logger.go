package logger

import (
	"os"
	"strings"

	"github.com/sirupsen/logrus"
)

var logger *logrus.Logger

// Init initializes the logger with the specified level
func Init(level string) {
	logger = logrus.New()
	
	// Set log level
	switch strings.ToLower(level) {
	case "debug":
		logger.SetLevel(logrus.DebugLevel)
	case "info":
		logger.SetLevel(logrus.InfoLevel)
	case "warn", "warning":
		logger.SetLevel(logrus.WarnLevel)
	case "error":
		logger.SetLevel(logrus.ErrorLevel)
	default:
		logger.SetLevel(logrus.InfoLevel)
	}
	
	// Set output format
	logger.SetFormatter(&logrus.TextFormatter{
		FullTimestamp: true,
		DisableColors: false,
	})
	
	// Set output
	logger.SetOutput(os.Stdout)
}

// GetLogger returns the configured logger instance
func GetLogger() *logrus.Logger {
	if logger == nil {
		Init("info")
	}
	return logger
}