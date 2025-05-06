#!/bin/bash
set -e

# Cloudflare UFW Sync Uninstaller
# This script uninstalls cloudflare-ufw-sync from the system

# Ensure script is run as root
if [[ $EUID -ne 0 ]]; then
  echo "This script must be run as root" 
  exit 1
fi

echo "Uninstalling Cloudflare UFW Sync..."

# Stop and disable service
if systemctl is-active --quiet cloudflare-ufw-sync; then
  systemctl stop cloudflare-ufw-sync
  echo "Service stopped"
fi

if systemctl is-enabled --quiet cloudflare-ufw-sync 2>/dev/null; then
  systemctl disable cloudflare-ufw-sync
  echo "Service disabled"
fi

# Remove service file
if [[ -f "/etc/systemd/system/cloudflare-ufw-sync.service" ]]; then
  rm -f /etc/systemd/system/cloudflare-ufw-sync.service
  systemctl daemon-reload
  echo "Service file removed"
fi

# Prompt before removing configuration
read -p "Do you want to remove configuration files? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  rm -rf /etc/cloudflare-ufw-sync
  echo "Configuration files removed"
fi

# Prompt before removing log files
read -p "Do you want to remove log files? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  rm -f /var/log/cloudflare-ufw-sync.log
  rmdir --ignore-fail-on-non-empty /var/log/cloudflare-ufw-sync 2>/dev/null || true
  echo "Log files removed"
fi

# Uninstall Python package
pip3 uninstall -y cloudflare-ufw-sync
echo "Python package uninstalled"

echo "Uninstallation complete!"