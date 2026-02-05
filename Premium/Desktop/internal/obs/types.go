// Package obs provides OBS WebSocket integration for the Waddles Desktop Bridge.
// It implements the obs-websocket v5 protocol for full OBS Studio control.
package obs

import (
	"time"
)

// ConnectionState represents the current OBS connection status
type ConnectionState int

const (
	// StateDisconnected indicates no active connection to OBS
	StateDisconnected ConnectionState = iota
	// StateConnecting indicates a connection attempt is in progress
	StateConnecting
	// StateConnected indicates an active connection to OBS
	StateConnected
	// StateReconnecting indicates automatic reconnection is in progress
	StateReconnecting
)

// String returns a human-readable representation of the connection state
func (s ConnectionState) String() string {
	switch s {
	case StateDisconnected:
		return "disconnected"
	case StateConnecting:
		return "connecting"
	case StateConnected:
		return "connected"
	case StateReconnecting:
		return "reconnecting"
	default:
		return "unknown"
	}
}

// Config holds OBS WebSocket connection configuration
type Config struct {
	// Host is the OBS WebSocket server hostname (default: localhost)
	Host string `mapstructure:"obs-host"`
	// Port is the OBS WebSocket server port (default: 4455)
	Port int `mapstructure:"obs-port"`
	// Password is the OBS WebSocket authentication password
	Password string `mapstructure:"obs-password"`
	// AutoReconnect enables automatic reconnection on disconnect
	AutoReconnect bool `mapstructure:"obs-auto-reconnect"`
	// ReconnectInterval is the base interval between reconnection attempts
	ReconnectInterval time.Duration `mapstructure:"obs-reconnect-interval"`
	// MaxReconnectInterval is the maximum interval between reconnection attempts
	MaxReconnectInterval time.Duration `mapstructure:"obs-max-reconnect-interval"`
	// Timeout is the connection timeout duration
	Timeout time.Duration `mapstructure:"obs-timeout"`
	// Enabled controls whether OBS integration is active
	Enabled bool `mapstructure:"obs-enabled"`
}

// DefaultConfig returns the default OBS configuration
func DefaultConfig() Config {
	return Config{
		Host:                 "localhost",
		Port:                 4455,
		Password:             "",
		AutoReconnect:        true,
		ReconnectInterval:    time.Second,
		MaxReconnectInterval: 30 * time.Second,
		Timeout:              10 * time.Second,
		Enabled:              true,
	}
}

// SceneInfo represents information about an OBS scene
type SceneInfo struct {
	// Name is the unique name of the scene
	Name string `json:"name"`
	// Index is the scene's position in the scene list
	Index int `json:"index"`
	// IsCurrent indicates if this is the currently active program scene
	IsCurrent bool `json:"is_current"`
	// IsPreview indicates if this is the currently active preview scene (studio mode)
	IsPreview bool `json:"is_preview"`
	// Sources contains the list of sources in this scene (optional)
	Sources []SourceInfo `json:"sources,omitempty"`
}

// SourceInfo represents information about an OBS source/scene item
type SourceInfo struct {
	// Name is the name of the source
	Name string `json:"name"`
	// ID is the unique scene item ID
	ID int `json:"id"`
	// Type is the source type (e.g., "browser_source", "image_source")
	Type string `json:"type"`
	// Visible indicates if the source is currently visible
	Visible bool `json:"visible"`
	// Locked indicates if the source is locked from interaction
	Locked bool `json:"locked"`
	// PositionX is the X position of the source
	PositionX float64 `json:"position_x"`
	// PositionY is the Y position of the source
	PositionY float64 `json:"position_y"`
	// Width is the base width of the source
	Width float64 `json:"width"`
	// Height is the base height of the source
	Height float64 `json:"height"`
	// Rotation is the rotation angle in degrees
	Rotation float64 `json:"rotation"`
	// ScaleX is the horizontal scale factor
	ScaleX float64 `json:"scale_x"`
	// ScaleY is the vertical scale factor
	ScaleY float64 `json:"scale_y"`
	// BoundsType is the bounding box type
	BoundsType string `json:"bounds_type,omitempty"`
	// BoundsWidth is the bounding box width
	BoundsWidth float64 `json:"bounds_width,omitempty"`
	// BoundsHeight is the bounding box height
	BoundsHeight float64 `json:"bounds_height,omitempty"`
}

// SourceTransform contains transform properties for a source
type SourceTransform struct {
	// PositionX is the X position
	PositionX *float64 `json:"position_x,omitempty"`
	// PositionY is the Y position
	PositionY *float64 `json:"position_y,omitempty"`
	// Rotation is the rotation angle in degrees
	Rotation *float64 `json:"rotation,omitempty"`
	// ScaleX is the horizontal scale factor
	ScaleX *float64 `json:"scale_x,omitempty"`
	// ScaleY is the vertical scale factor
	ScaleY *float64 `json:"scale_y,omitempty"`
	// BoundsType is the bounding box type
	BoundsType *string `json:"bounds_type,omitempty"`
	// BoundsWidth is the bounding box width
	BoundsWidth *float64 `json:"bounds_width,omitempty"`
	// BoundsHeight is the bounding box height
	BoundsHeight *float64 `json:"bounds_height,omitempty"`
}

// FilterInfo represents information about an OBS filter
type FilterInfo struct {
	// Name is the filter name
	Name string `json:"name"`
	// Type is the filter type identifier
	Type string `json:"type"`
	// Index is the filter's position in the filter list
	Index int `json:"index"`
	// Enabled indicates if the filter is currently enabled
	Enabled bool `json:"enabled"`
	// Settings contains the filter's configuration settings
	Settings map[string]interface{} `json:"settings,omitempty"`
}

// StreamStatus represents the current streaming state
type StreamStatus struct {
	// Active indicates if streaming is currently active
	Active bool `json:"active"`
	// Reconnecting indicates if the stream is attempting to reconnect
	Reconnecting bool `json:"reconnecting"`
	// TimecodeString is the stream duration as a timecode string (HH:MM:SS)
	TimecodeString string `json:"timecode"`
	// Duration is the stream duration
	Duration time.Duration `json:"duration"`
	// BytesSent is the total bytes sent
	BytesSent int64 `json:"bytes_sent"`
	// KbitsPerSec is the current bitrate in kilobits per second
	KbitsPerSec int64 `json:"kbits_per_sec"`
	// DroppedFrames is the number of dropped frames
	DroppedFrames int64 `json:"dropped_frames"`
	// TotalFrames is the total number of frames
	TotalFrames int64 `json:"total_frames"`
	// RenderSkippedFrames is the number of skipped render frames
	RenderSkippedFrames int64 `json:"render_skipped_frames"`
	// OutputSkippedFrames is the number of skipped output frames
	OutputSkippedFrames int64 `json:"output_skipped_frames"`
}

// RecordingStatus represents the current recording state
type RecordingStatus struct {
	// Active indicates if recording is currently active
	Active bool `json:"active"`
	// Paused indicates if recording is currently paused
	Paused bool `json:"paused"`
	// TimecodeString is the recording duration as a timecode string (HH:MM:SS)
	TimecodeString string `json:"timecode"`
	// Duration is the recording duration
	Duration time.Duration `json:"duration"`
	// BytesWritten is the total bytes written to disk
	BytesWritten int64 `json:"bytes_written"`
	// OutputPath is the path to the recording file
	OutputPath string `json:"output_path"`
}

// OBSStats represents general OBS statistics
type OBSStats struct {
	// CPUUsage is the current CPU usage percentage
	CPUUsage float64 `json:"cpu_usage"`
	// MemoryUsage is the current memory usage in MB
	MemoryUsage float64 `json:"memory_usage"`
	// FreeDiskSpace is the available disk space in MB
	FreeDiskSpace float64 `json:"free_disk_space"`
	// ActiveFPS is the current FPS
	ActiveFPS float64 `json:"active_fps"`
	// AverageFrameTime is the average frame render time in ms
	AverageFrameTime float64 `json:"average_frame_time"`
	// RenderSkippedFrames is the total render skipped frames
	RenderSkippedFrames int64 `json:"render_skipped_frames"`
	// RenderTotalFrames is the total render frames
	RenderTotalFrames int64 `json:"render_total_frames"`
	// OutputSkippedFrames is the total output skipped frames
	OutputSkippedFrames int64 `json:"output_skipped_frames"`
	// OutputTotalFrames is the total output frames
	OutputTotalFrames int64 `json:"output_total_frames"`
	// WebSocketSessionIncomingMessages is the count of incoming WebSocket messages
	WebSocketSessionIncomingMessages int64 `json:"ws_incoming_messages"`
	// WebSocketSessionOutgoingMessages is the count of outgoing WebSocket messages
	WebSocketSessionOutgoingMessages int64 `json:"ws_outgoing_messages"`
}

// EventType represents the type of OBS event
type EventType string

// OBS event type constants
const (
	// Scene events
	EventSceneChanged         EventType = "scene_changed"
	EventSceneListChanged     EventType = "scene_list_changed"
	EventSceneNameChanged     EventType = "scene_name_changed"
	EventSceneCreated         EventType = "scene_created"
	EventSceneRemoved         EventType = "scene_removed"

	// Source/Scene item events
	EventSourceVisibilityChanged EventType = "source_visibility_changed"
	EventSourceLockChanged       EventType = "source_lock_changed"
	EventSourceTransformChanged  EventType = "source_transform_changed"
	EventSourceCreated           EventType = "source_created"
	EventSourceRemoved           EventType = "source_removed"
	EventSourceRenamed           EventType = "source_renamed"

	// Filter events
	EventFilterEnabled      EventType = "filter_enabled"
	EventFilterDisabled     EventType = "filter_disabled"
	EventFilterListChanged  EventType = "filter_list_changed"
	EventFilterNameChanged  EventType = "filter_name_changed"
	EventFilterCreated      EventType = "filter_created"
	EventFilterRemoved      EventType = "filter_removed"

	// Streaming events
	EventStreamStarting   EventType = "stream_starting"
	EventStreamStarted    EventType = "stream_started"
	EventStreamStopping   EventType = "stream_stopping"
	EventStreamStopped    EventType = "stream_stopped"
	EventStreamReconnect  EventType = "stream_reconnect"

	// Recording events
	EventRecordingStarting EventType = "recording_starting"
	EventRecordingStarted  EventType = "recording_started"
	EventRecordingStopping EventType = "recording_stopping"
	EventRecordingStopped  EventType = "recording_stopped"
	EventRecordingPaused   EventType = "recording_paused"
	EventRecordingResumed  EventType = "recording_resumed"

	// General events
	EventExiting         EventType = "exiting"
	EventStudioModeChanged EventType = "studio_mode_changed"
)

// Event represents an OBS event
type Event struct {
	// Type is the event type
	Type EventType `json:"type"`
	// Timestamp is when the event occurred
	Timestamp time.Time `json:"timestamp"`
	// Data contains event-specific data
	Data map[string]interface{} `json:"data,omitempty"`
}

// EventCallback is a function that handles OBS events
type EventCallback func(event Event)

// SubscriptionID is a unique identifier for an event subscription
type SubscriptionID string

// ConnectionInfo represents information about the OBS connection
type ConnectionInfo struct {
	// State is the current connection state
	State ConnectionState `json:"state"`
	// OBSVersion is the connected OBS version
	OBSVersion string `json:"obs_version,omitempty"`
	// WebSocketVersion is the obs-websocket version
	WebSocketVersion string `json:"websocket_version,omitempty"`
	// Platform is the operating system OBS is running on
	Platform string `json:"platform,omitempty"`
	// ConnectedAt is when the connection was established
	ConnectedAt *time.Time `json:"connected_at,omitempty"`
	// DisconnectedAt is when the connection was lost
	DisconnectedAt *time.Time `json:"disconnected_at,omitempty"`
	// ReconnectAttempts is the number of reconnection attempts since last disconnect
	ReconnectAttempts int `json:"reconnect_attempts,omitempty"`
	// LastError is the last error message
	LastError string `json:"last_error,omitempty"`
}

// Error types for OBS operations
var (
	ErrNotConnected     = &OBSError{Code: "not_connected", Message: "not connected to OBS"}
	ErrConnectionFailed = &OBSError{Code: "connection_failed", Message: "failed to connect to OBS"}
	ErrAuthFailed       = &OBSError{Code: "auth_failed", Message: "authentication failed"}
	ErrSceneNotFound    = &OBSError{Code: "scene_not_found", Message: "scene not found"}
	ErrSourceNotFound   = &OBSError{Code: "source_not_found", Message: "source not found"}
	ErrFilterNotFound   = &OBSError{Code: "filter_not_found", Message: "filter not found"}
	ErrOperationFailed  = &OBSError{Code: "operation_failed", Message: "operation failed"}
	ErrTimeout          = &OBSError{Code: "timeout", Message: "operation timed out"}
)

// OBSError represents an OBS operation error
type OBSError struct {
	// Code is the error code
	Code string `json:"code"`
	// Message is the error message
	Message string `json:"message"`
	// Details contains additional error details
	Details string `json:"details,omitempty"`
}

// Error implements the error interface
func (e *OBSError) Error() string {
	if e.Details != "" {
		return e.Code + ": " + e.Message + " - " + e.Details
	}
	return e.Code + ": " + e.Message
}

// NewOBSError creates a new OBS error with details
func NewOBSError(base *OBSError, details string) *OBSError {
	return &OBSError{
		Code:    base.Code,
		Message: base.Message,
		Details: details,
	}
}
