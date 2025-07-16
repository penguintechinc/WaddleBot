# WaddleBot Premium Desktop Bridge

A powerful desktop bridge client that connects your local system to WaddleBot communities, enabling chat commands to trigger local actions and system integrations.

## Features

- **Premium Application**: Requires active WaddleBot Premium subscription
- **WebAuthn Authentication**: Secure authentication using WebAuthn for device registration
- **Community Restricted**: Each bridge instance is restricted to a single community and user
- **Configurable Polling**: Polls server for actions every 30 seconds (configurable, minimum 5 seconds)
- **Module System**: Extensible plugin architecture for local system interactions
- **Multi-Platform**: Native support for macOS Universal and Windows 11
- **Local System Integration**: Execute commands, monitor system resources, and more
- **Real-time Web Interface**: Browser-based configuration and monitoring

## Requirements

- **Operating System**: macOS 10.15+ or Windows 11
- **Premium Subscription**: Active WaddleBot Premium subscription required
- **Go 1.21+**: For building from source
- **WebAuthn Compatible Browser**: Chrome, Firefox, Safari, or Edge

## Installation

### macOS

1. Download the macOS package from releases
2. Extract the archive: `tar -xzf WaddleBot-Bridge-macOS-1.0.0.tar.gz`
3. Navigate to the extracted directory
4. Configure your settings in `config.yaml`
5. Run the bridge: `./start.sh`

### Windows 11

1. Download the Windows package from releases
2. Extract the ZIP file
3. Navigate to the extracted directory
4. Configure your settings in `config.yaml`
5. Run the bridge: `start.bat`

## Configuration

Edit the `config.yaml` file to configure your bridge:

```yaml
# WaddleBot Bridge Configuration
api-url: "https://api.waddlebot.io"
community-id: "your-community-id"
user-id: "your-user-id"
poll-interval: 30
web-port: 8080
web-host: "127.0.0.1"
log-level: "info"
```

### Configuration Options

- `api-url`: WaddleBot API endpoint
- `community-id`: Your community identifier
- `user-id`: Your user identifier
- `poll-interval`: Polling interval in seconds (minimum 5)
- `web-port`: Web interface port
- `web-host`: Web interface host
- `log-level`: Logging level (debug, info, warn, error)

## Web Interface

Access the web interface at `http://localhost:8080` to:

- Authenticate using WebAuthn
- View bridge status
- Monitor system information
- Configure settings

## Module System

The bridge supports a plugin-based module system for extending functionality:

### Built-in Modules

- **System Module**: System information, process management, and command execution
  - `get_info`: Get system information
  - `get_processes`: List running processes
  - `get_memory_info`: Memory usage statistics
  - `get_cpu_info`: CPU usage and information
  - `get_disk_usage`: Disk usage statistics
  - `execute_command`: Execute allowed system commands

### Creating Custom Modules

1. Implement the `ModuleInterface` in Go
2. Build as a plugin: `go build -buildmode=plugin -o module.so module.go`
3. Place the `.so` file in the modules directory
4. Restart the bridge to load the module

Example module structure:

```go
package main

import (
    "context"
    "waddlebot-bridge/internal/modules"
)

type MyModule struct {
    config map[string]string
}

func NewModule() modules.ModuleInterface {
    return &MyModule{}
}

func (m *MyModule) Initialize(config map[string]string) error {
    m.config = config
    return nil
}

func (m *MyModule) ExecuteAction(ctx context.Context, action string, parameters map[string]string) (map[string]interface{}, error) {
    // Implement your action logic here
    return map[string]interface{}{"result": "success"}, nil
}

// ... implement other required methods
```

## Security

- **WebAuthn Authentication**: Uses WebAuthn for secure device registration
- **Community Isolation**: Each bridge is restricted to a single community
- **Command Restrictions**: Only allowed system commands can be executed
- **Encrypted Communication**: All API communication uses HTTPS
- **Session Management**: Secure session handling with automatic expiration

## Building from Source

### Prerequisites

- Go 1.21 or later
- Git

### Build Instructions

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/waddlebot-bridge.git
   cd waddlebot-bridge
   ```

2. Build using the provided script:
   ```bash
   chmod +x scripts/build.sh
   ./scripts/build.sh
   ```

3. Or use the Makefile:
   ```bash
   make build
   ```

### Platform-Specific Builds

- **macOS**: `make build-macos`
- **Windows**: `make build-windows`
- **Linux**: `make build-linux`

## Development

### Running in Development Mode

```bash
make dev
```

### Building Modules

```bash
make build-modules
```

### Running Tests

```bash
make test
```

### Code Formatting

```bash
make fmt
```

## API Integration

The bridge communicates with WaddleBot through the following endpoints:

- `GET /api/bridge/poll` - Poll for actions to execute
- `POST /api/bridge/response` - Send action results
- `POST /api/bridge/register` - Register bridge with server
- `POST /api/bridge/heartbeat` - Send heartbeat

## Troubleshooting

### Common Issues

1. **License Error**: Ensure you have an active WaddleBot Premium subscription
2. **Authentication Failed**: Check your community-id and user-id in config.yaml
3. **Module Loading Error**: Verify module files are in the correct directory
4. **Network Issues**: Check firewall settings and API connectivity

### Debug Mode

Run with debug logging:

```bash
./waddlebot-bridge --log-level debug
```

### Log Files

Logs are written to:
- macOS: `~/Library/Logs/WaddleBot/bridge.log`
- Windows: `%APPDATA%/WaddleBot/bridge.log`

## Support

For support and questions:

- Visit: https://waddlebot.io/support
- Email: support@waddlebot.io
- Discord: https://discord.gg/waddlebot

## License

This software is licensed exclusively to users with active WaddleBot Premium subscriptions. See LICENSE file for details.

## Contributing

This is proprietary software. Contributions are not accepted from external parties.

---

**WaddleBot Premium Desktop Bridge v1.0.0**
© 2024 WaddleBot. All rights reserved.