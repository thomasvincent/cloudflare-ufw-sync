#!/bin/bash
set -e

# Cloudflare UFW Sync Installer
# This script installs cloudflare-ufw-sync as a system service

# Ensure script is run as root
if [[ $EUID -ne 0 ]]; then
  echo "This script must be run as root" 
  exit 1
fi

echo "Installing Cloudflare UFW Sync..."

# Install dependencies
if command -v apt-get &> /dev/null; then
  echo "Detected Debian/Ubuntu, installing dependencies..."
  apt-get update
  apt-get install -y python3 python3-pip ufw
elif command -v dnf &> /dev/null; then
  echo "Detected RHEL/Fedora, installing dependencies..."
  dnf install -y python3 python3-pip ufw
elif command -v yum &> /dev/null; then
  echo "Detected older RHEL/CentOS, installing dependencies..."
  yum install -y python3 python3-pip ufw
else
  echo "Unsupported distribution. Please install Python 3, pip, and UFW manually."
  exit 1
fi

# Create configuration directory
CONFIG_DIR="/etc/cloudflare-ufw-sync"
mkdir -p $CONFIG_DIR

# Create log directory
mkdir -p /var/log/cloudflare-ufw-sync

# Copy configuration if it doesn't exist
if [[ ! -f "$CONFIG_DIR/config.yml" ]]; then
  cp "$(dirname "$0")/../config/default.yml" "$CONFIG_DIR/config.yml"
  echo "Default configuration installed at $CONFIG_DIR/config.yml"
  echo "Please edit this file to configure your Cloudflare API key and other settings."
fi

# Install the Python package
pip3 install -e "$(dirname "$0")/.."
echo "Python package installed"

# Create systemd service
cat > /etc/systemd/system/cloudflare-ufw-sync.service << EOF
[Unit]
Description=Cloudflare IP Synchronization for UFW
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/cloudflare-ufw-sync daemon --foreground
Restart=on-failure
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable and start the service
systemctl enable cloudflare-ufw-sync
systemctl start cloudflare-ufw-sync

echo "Installation complete!"
echo "Service status: $(systemctl is-active cloudflare-ufw-sync)"
echo "You can check logs with: journalctl -u cloudflare-ufw-sync"