# Cloudflare UFW Sync

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests](https://github.com/thomasvincent/cloudflare-ufw-sync/actions/workflows/tests.yml/badge.svg)](https://github.com/thomasvincent/cloudflare-ufw-sync/actions/workflows/tests.yml)
[![GitHub release](https://img.shields.io/github/v/release/thomasvincent/cloudflare-ufw-sync)](https://github.com/thomasvincent/cloudflare-ufw-sync/releases)

Enterprise-grade Cloudflare IP synchronization for UFW.

## Overview

`cloudflare-ufw-sync` is a robust tool designed to automatically synchronize Cloudflare's IP ranges with your UFW (Uncomplicated Firewall) rules. This ensures that only traffic coming from Cloudflare's network is allowed to access your web server.

## Features

- 🔄 Automatic synchronization of Cloudflare IP ranges with UFW rules
- 🔒 Securely manages UFW rules with proper permission handling
- 🛠️ Supports both IPv4 and IPv6 address ranges
- 🔍 Detailed logging for audit and troubleshooting
- 🔧 Customizable configuration
- 🧪 Comprehensive test suite

## Installation

### From Source

```bash
git clone https://github.com/thomasvincent/cloudflare-ufw-sync.git
cd cloudflare-ufw-sync
pip install .
```

## Configuration

Create a configuration file at `/etc/cloudflare-ufw-sync/config.yml` or `~/.config/cloudflare-ufw-sync/config.yml`:

```yaml
cloudflare:
  api_key: your-api-key  # Optional: Only needed if using authenticated endpoints
  ip_types:
    - v4  # IPv4 addresses
    - v6  # IPv6 addresses

ufw:
  default_policy: deny
  port: 443  # The port to allow access to
  proto: tcp  # Protocol (tcp, udp, or both)
  comment: "Cloudflare IP"  # Comment for UFW rules

sync:
  interval: 86400  # Sync interval in seconds (default: 1 day)
  enabled: true
```

## Usage

### Command Line

```bash
# Run a sync operation
cloudflare-ufw-sync sync

# Run in daemon mode
cloudflare-ufw-sync daemon

# View current status
cloudflare-ufw-sync status
```

### As a Service

A systemd service file is provided to run the synchronization as a service:

```bash
sudo cp scripts/cloudflare-ufw-sync.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cloudflare-ufw-sync
sudo systemctl start cloudflare-ufw-sync
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/thomasvincent/cloudflare-ufw-sync.git
cd cloudflare-ufw-sync

# Set up a virtual environment
python -m venv venv
source venv/bin/activate

# Install dev dependencies
pip install -e ".[dev]"
```

### Testing and Linting with Tox

The project includes a `tox.ini` file that sets up environments for testing, linting, and type checking. This allows you to run the same checks locally that are performed in the CI pipeline before committing your changes.

```bash
# Install tox
pip install tox

# Run all tests and checks on all supported Python versions
tox

# Run tests for a specific Python version
tox -e py38  # For Python 3.8
tox -e py39  # For Python 3.9
tox -e py310 # For Python 3.10
tox -e py311 # For Python 3.11
tox -e py312 # For Python 3.12

# Run only linting checks
tox -e lint

# Run only type checking
tox -e mypy

# Format code
tox -e format
```

### Manual Testing

If you prefer to run tests and linting manually:

```bash
# Run tests
pytest

# Run linting
black .
isort .
flake8

# Run type checking
mypy src
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Security

See [SECURITY.md](SECURITY.md) for security policy and reporting vulnerabilities.

## Requirements

- Python 3.8 or higher
- Linux with UFW (Uncomplicated Firewall) installed
- Root/sudo access for managing firewall rules
- Internet connectivity to fetch Cloudflare IP ranges

## How It Works

1. **Fetches IP Ranges**: The tool connects to Cloudflare's API to retrieve the latest IP ranges (both IPv4 and IPv6)
2. **Manages UFW Rules**: It automatically adds UFW rules to allow traffic from Cloudflare IPs on specified ports
3. **Synchronization**: Removes outdated rules and adds new ones as Cloudflare's IP ranges change
4. **Daemon Mode**: Can run continuously to keep rules updated automatically

## Use Cases

- **Web Servers**: Ensure only Cloudflare can access your origin server
- **API Endpoints**: Protect API servers behind Cloudflare's proxy
- **Load Balancers**: Secure load balancers that should only accept Cloudflare traffic
- **Security Compliance**: Meet security requirements for IP whitelisting

## Troubleshooting

If you encounter issues:

1. **Check UFW is installed**: `sudo ufw status`
2. **Verify Python version**: `python3 --version` (must be 3.8+)
3. **Test Cloudflare API access**: `curl https://api.cloudflare.com/client/v4/ips`
4. **Check logs**: The tool provides detailed logging for debugging

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

- **Issues**: [GitHub Issues](https://github.com/thomasvincent/cloudflare-ufw-sync/issues)
- **Discussions**: [GitHub Discussions](https://github.com/thomasvincent/cloudflare-ufw-sync/discussions)