"""
Command line interface for cloudflare-ufw-sync.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

from cloudflare_ufw_sync import __version__
from cloudflare_ufw_sync.config import Config
from cloudflare_ufw_sync.sync import SyncService

logger = logging.getLogger(__name__)


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        args: Command line arguments

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Cloudflare IP synchronization for UFW"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to configuration file",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Synchronize Cloudflare IPs with UFW")
    sync_parser.add_argument(
        "--force", "-f", action="store_true", help="Force synchronization"
    )

    # Daemon command
    daemon_parser = subparsers.add_parser("daemon", help="Run as a daemon")
    daemon_parser.add_argument(
        "--foreground", action="store_true", help="Run in foreground"
    )

    # Status command
    subparsers.add_parser("status", help="Show status")

    # Install command
    install_parser = subparsers.add_parser("install", help="Install as a service")
    install_parser.add_argument(
        "--no-enable", action="store_true", help="Don't enable service"
    )

    # Uninstall command
    subparsers.add_parser("uninstall", help="Uninstall service")

    return parser.parse_args(args)


def handle_sync(config: Config, force: bool = False) -> int:
    """Handle sync command.

    Args:
        config: Configuration object
        force: Force synchronization

    Returns:
        Exit code
    """
    sync_service = SyncService(config)
    try:
        result = sync_service.sync()
        print(f"Synchronization completed:")
        print(f"  IPv4 ranges: {result['ips']['v4']}")
        print(f"  IPv6 ranges: {result['ips']['v6']}")
        print(f"  Rules added: {result['rules']['added']}")
        print(f"  Rules removed: {result['rules']['removed']}")
        return 0
    except Exception as e:
        logger.error(f"Synchronization failed: {str(e)}")
        return 1


def handle_daemon(config: Config, foreground: bool = False) -> int:
    """Handle daemon command.

    Args:
        config: Configuration object
        foreground: Run in foreground

    Returns:
        Exit code
    """
    if not foreground and os.fork() > 0:
        # Parent process
        return 0

    # Child process
    try:
        sync_service = SyncService(config)
        sync_service.run_daemon()
        return 0
    except Exception as e:
        logger.error(f"Daemon failed: {str(e)}")
        return 1


def handle_status(config: Config) -> int:
    """Handle status command.

    Args:
        config: Configuration object

    Returns:
        Exit code
    """
    # Check if UFW is enabled
    try:
        from cloudflare_ufw_sync.ufw import UFWManager
        ufw = UFWManager()
        existing_rules = ufw.get_existing_rules()
        print("Cloudflare UFW Sync Status:")
        print(f"  IPv4 rules: {len(existing_rules['v4'])}")
        print(f"  IPv6 rules: {len(existing_rules['v6'])}")
        return 0
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        return 1


def handle_install(config: Config, no_enable: bool = False) -> int:
    """Handle install command.

    Args:
        config: Configuration object
        no_enable: Don't enable service

    Returns:
        Exit code
    """
    # Get the script directory
    script_dir = Path(__file__).resolve().parent.parent.parent / "scripts"
    
    if not (script_dir / "cloudflare-ufw-sync.service").exists():
        logger.error("Service file not found")
        return 1
        
    try:
        import shutil
        import subprocess
        
        # Copy service file
        dest = Path("/etc/systemd/system/cloudflare-ufw-sync.service")
        shutil.copy(script_dir / "cloudflare-ufw-sync.service", dest)
        print(f"Service file installed at {dest}")
        
        # Reload systemd
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        print("Systemd daemon reloaded")
        
        if not no_enable:
            # Enable and start service
            subprocess.run(["systemctl", "enable", "cloudflare-ufw-sync"], check=True)
            print("Service enabled")
            subprocess.run(["systemctl", "start", "cloudflare-ufw-sync"], check=True)
            print("Service started")
            
        return 0
    except Exception as e:
        logger.error(f"Installation failed: {str(e)}")
        return 1


def handle_uninstall(config: Config) -> int:
    """Handle uninstall command.

    Args:
        config: Configuration object

    Returns:
        Exit code
    """
    try:
        import subprocess
        
        # Stop and disable service
        subprocess.run(["systemctl", "stop", "cloudflare-ufw-sync"], check=False)
        print("Service stopped")
        subprocess.run(["systemctl", "disable", "cloudflare-ufw-sync"], check=False)
        print("Service disabled")
        
        # Remove service file
        service_file = Path("/etc/systemd/system/cloudflare-ufw-sync.service")
        if service_file.exists():
            service_file.unlink()
            print(f"Service file removed: {service_file}")
            
        # Reload systemd
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        print("Systemd daemon reloaded")
        
        return 0
    except Exception as e:
        logger.error(f"Uninstallation failed: {str(e)}")
        return 1


def main(args: Optional[List[str]] = None) -> int:
    """Main entry point.

    Args:
        args: Command line arguments

    Returns:
        Exit code
    """
    parsed_args = parse_args(args)
    
    # Initialize configuration
    config = Config(parsed_args.config)
    
    # Setup logging
    if parsed_args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        config.setup_logging()
        
    # Handle commands
    if parsed_args.command == "sync":
        return handle_sync(config, parsed_args.force)
    elif parsed_args.command == "daemon":
        return handle_daemon(config, parsed_args.foreground)
    elif parsed_args.command == "status":
        return handle_status(config)
    elif parsed_args.command == "install":
        return handle_install(config, parsed_args.no_enable)
    elif parsed_args.command == "uninstall":
        return handle_uninstall(config)
    else:
        print("No command specified. Use --help for usage information.")
        return 1


if __name__ == "__main__":
    sys.exit(main())