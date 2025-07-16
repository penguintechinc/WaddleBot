package main

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"strconv"
	"strings"
	"time"

	"github.com/shirou/gopsutil/cpu"
	"github.com/shirou/gopsutil/disk"
	"github.com/shirou/gopsutil/host"
	"github.com/shirou/gopsutil/mem"
	"github.com/shirou/gopsutil/process"
	"waddlebot-bridge/internal/modules"
)

// SystemModule provides system information and control
type SystemModule struct {
	config map[string]string
}

// NewModule creates a new system module instance
func NewModule() modules.ModuleInterface {
	return &SystemModule{}
}

// Initialize initializes the system module
func (m *SystemModule) Initialize(config map[string]string) error {
	m.config = config
	return nil
}

// GetInfo returns module information
func (m *SystemModule) GetInfo() *modules.ModuleInfo {
	return &modules.ModuleInfo{
		Name:        "system",
		Version:     "1.0.0",
		Description: "System information and control module",
		Author:      "WaddleBot",
		Actions: []modules.ActionInfo{
			{
				Name:        "get_info",
				Description: "Get system information",
				Parameters:  map[string]interface{}{},
				ReturnType:  "object",
				Timeout:     10,
				Permissions: []string{"system.read"},
			},
			{
				Name:        "get_processes",
				Description: "Get running processes",
				Parameters: map[string]interface{}{
					"limit": "number",
				},
				ReturnType:  "array",
				Timeout:     15,
				Permissions: []string{"system.read"},
			},
			{
				Name:        "execute_command",
				Description: "Execute a system command",
				Parameters: map[string]interface{}{
					"command": "string",
					"args":    "array",
				},
				ReturnType:  "object",
				Timeout:     30,
				Permissions: []string{"system.execute"},
			},
			{
				Name:        "get_disk_usage",
				Description: "Get disk usage information",
				Parameters: map[string]interface{}{
					"path": "string",
				},
				ReturnType:  "object",
				Timeout:     10,
				Permissions: []string{"system.read"},
			},
			{
				Name:        "get_memory_info",
				Description: "Get memory usage information",
				Parameters:  map[string]interface{}{},
				ReturnType:  "object",
				Timeout:     5,
				Permissions: []string{"system.read"},
			},
			{
				Name:        "get_cpu_info",
				Description: "Get CPU usage information",
				Parameters:  map[string]interface{}{},
				ReturnType:  "object",
				Timeout:     10,
				Permissions: []string{"system.read"},
			},
		},
		Dependencies: []string{},
		Permissions:  []string{"system.read", "system.execute"},
		Config:       map[string]string{},
		Enabled:      true,
		LoadedAt:     time.Now(),
	}
}

// ExecuteAction executes a specific action
func (m *SystemModule) ExecuteAction(ctx context.Context, action string, parameters map[string]string) (map[string]interface{}, error) {
	switch action {
	case "get_info":
		return m.getSystemInfo(ctx)
	case "get_processes":
		return m.getProcesses(ctx, parameters)
	case "execute_command":
		return m.executeCommand(ctx, parameters)
	case "get_disk_usage":
		return m.getDiskUsage(ctx, parameters)
	case "get_memory_info":
		return m.getMemoryInfo(ctx)
	case "get_cpu_info":
		return m.getCPUInfo(ctx)
	default:
		return nil, fmt.Errorf("unknown action: %s", action)
	}
}

// GetActions returns available actions
func (m *SystemModule) GetActions() []modules.ActionInfo {
	return m.GetInfo().Actions
}

// Cleanup cleans up module resources
func (m *SystemModule) Cleanup() error {
	return nil
}

// getSystemInfo returns general system information
func (m *SystemModule) getSystemInfo(ctx context.Context) (map[string]interface{}, error) {
	hostInfo, err := host.Info()
	if err != nil {
		return nil, fmt.Errorf("failed to get host info: %w", err)
	}

	return map[string]interface{}{
		"hostname":        hostInfo.Hostname,
		"os":              hostInfo.OS,
		"platform":        hostInfo.Platform,
		"platform_family": hostInfo.PlatformFamily,
		"platform_version": hostInfo.PlatformVersion,
		"kernel_version":  hostInfo.KernelVersion,
		"kernel_arch":     hostInfo.KernelArch,
		"uptime":          hostInfo.Uptime,
		"boot_time":       hostInfo.BootTime,
		"processes":       hostInfo.Procs,
		"go_version":      runtime.Version(),
		"go_arch":         runtime.GOARCH,
		"go_os":           runtime.GOOS,
		"cpu_count":       runtime.NumCPU(),
		"timestamp":       time.Now().Unix(),
	}, nil
}

// getProcesses returns running processes
func (m *SystemModule) getProcesses(ctx context.Context, parameters map[string]string) (map[string]interface{}, error) {
	limit := 50 // default limit
	if limitStr, ok := parameters["limit"]; ok {
		if parsedLimit, err := strconv.Atoi(limitStr); err == nil && parsedLimit > 0 {
			limit = parsedLimit
		}
	}

	pids, err := process.Pids()
	if err != nil {
		return nil, fmt.Errorf("failed to get process IDs: %w", err)
	}

	processes := make([]map[string]interface{}, 0, limit)
	count := 0

	for _, pid := range pids {
		if count >= limit {
			break
		}

		proc, err := process.NewProcess(pid)
		if err != nil {
			continue
		}

		name, _ := proc.Name()
		status, _ := proc.Status()
		cpuPercent, _ := proc.CPUPercent()
		memInfo, _ := proc.MemoryInfo()
		createTime, _ := proc.CreateTime()

		processInfo := map[string]interface{}{
			"pid":         pid,
			"name":        name,
			"status":      status,
			"cpu_percent": cpuPercent,
			"create_time": createTime,
		}

		if memInfo != nil {
			processInfo["memory_rss"] = memInfo.RSS
			processInfo["memory_vms"] = memInfo.VMS
		}

		processes = append(processes, processInfo)
		count++
	}

	return map[string]interface{}{
		"processes": processes,
		"total":     len(pids),
		"returned":  count,
		"limit":     limit,
	}, nil
}

// executeCommand executes a system command
func (m *SystemModule) executeCommand(ctx context.Context, parameters map[string]string) (map[string]interface{}, error) {
	command, ok := parameters["command"]
	if !ok {
		return nil, fmt.Errorf("command parameter is required")
	}

	// Security check - only allow certain commands
	allowedCommands := []string{"echo", "ls", "pwd", "date", "whoami", "uname"}
	isAllowed := false
	for _, allowed := range allowedCommands {
		if command == allowed {
			isAllowed = true
			break
		}
	}

	if !isAllowed {
		return nil, fmt.Errorf("command '%s' is not allowed", command)
	}

	// Parse arguments
	var args []string
	if argsStr, ok := parameters["args"]; ok {
		args = strings.Split(argsStr, " ")
	}

	// Execute command
	cmd := exec.CommandContext(ctx, command, args...)
	output, err := cmd.CombinedOutput()

	result := map[string]interface{}{
		"command": command,
		"args":    args,
		"output":  string(output),
		"success": err == nil,
	}

	if err != nil {
		result["error"] = err.Error()
	}

	return result, nil
}

// getDiskUsage returns disk usage information
func (m *SystemModule) getDiskUsage(ctx context.Context, parameters map[string]string) (map[string]interface{}, error) {
	path := "/"
	if pathParam, ok := parameters["path"]; ok {
		path = pathParam
	}

	usage, err := disk.Usage(path)
	if err != nil {
		return nil, fmt.Errorf("failed to get disk usage: %w", err)
	}

	return map[string]interface{}{
		"path":        path,
		"total":       usage.Total,
		"free":        usage.Free,
		"used":        usage.Used,
		"used_percent": usage.UsedPercent,
		"inodes_total": usage.InodesTotal,
		"inodes_used":  usage.InodesUsed,
		"inodes_free":  usage.InodesFree,
		"inodes_used_percent": usage.InodesUsedPercent,
	}, nil
}

// getMemoryInfo returns memory usage information
func (m *SystemModule) getMemoryInfo(ctx context.Context) (map[string]interface{}, error) {
	memInfo, err := mem.VirtualMemory()
	if err != nil {
		return nil, fmt.Errorf("failed to get memory info: %w", err)
	}

	swapInfo, err := mem.SwapMemory()
	if err != nil {
		return nil, fmt.Errorf("failed to get swap info: %w", err)
	}

	return map[string]interface{}{
		"virtual": map[string]interface{}{
			"total":       memInfo.Total,
			"available":   memInfo.Available,
			"used":        memInfo.Used,
			"used_percent": memInfo.UsedPercent,
			"free":        memInfo.Free,
			"active":      memInfo.Active,
			"inactive":    memInfo.Inactive,
			"buffers":     memInfo.Buffers,
			"cached":      memInfo.Cached,
		},
		"swap": map[string]interface{}{
			"total":       swapInfo.Total,
			"used":        swapInfo.Used,
			"free":        swapInfo.Free,
			"used_percent": swapInfo.UsedPercent,
		},
	}, nil
}

// getCPUInfo returns CPU usage information
func (m *SystemModule) getCPUInfo(ctx context.Context) (map[string]interface{}, error) {
	cpuInfo, err := cpu.Info()
	if err != nil {
		return nil, fmt.Errorf("failed to get CPU info: %w", err)
	}

	cpuPercent, err := cpu.Percent(time.Second, false)
	if err != nil {
		return nil, fmt.Errorf("failed to get CPU percent: %w", err)
	}

	cpuCount, err := cpu.Counts(true)
	if err != nil {
		return nil, fmt.Errorf("failed to get CPU counts: %w", err)
	}

	result := map[string]interface{}{
		"count":   cpuCount,
		"percent": cpuPercent,
		"info":    []map[string]interface{}{},
	}

	for _, info := range cpuInfo {
		result["info"] = append(result["info"].([]map[string]interface{}), map[string]interface{}{
			"model_name": info.ModelName,
			"family":     info.Family,
			"speed":      info.Mhz,
			"cache_size": info.CacheSize,
			"cores":      info.Cores,
			"vendor_id":  info.VendorID,
		})
	}

	return result, nil
}