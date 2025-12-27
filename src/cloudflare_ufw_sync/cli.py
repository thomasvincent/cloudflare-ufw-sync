"""Command line interface for cloudflare-ufw-sync.

This module provides the command-line interface for the cloudflare-ufw-sync tool.
It handles argument parsing and dispatches to the appropriate handler functions.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from cloudflare_ufw_sync import __version__
from cloudflare_ufw_sync.config import Config
from cloudflare_ufw_sync.sync import SyncService

logger = logging.getLogger(__name__)


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        args: Command line arguments. If None, sys.argv[1:] is used.

    Returns:
        Parsed arguments as an argparse.Namespace object.
    """
    parser = argparse.ArgumentParser(
        description="Cloudflare IP synchronization for UFW"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument("--config", "-c", type=str, help="Path to configuration file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Sync command
    sync_parser = subparsers.add_parser(
        "sync", help="Synchronize Cloudflare IPs with UFW"
    )
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
    """Handle the sync command to synchronize Cloudflare IP ranges with UFW.

    Args:
        config: Configuration object containing sync settings.
        force: Whether to force synchronization even if not needed.

    Returns:
        int: Exit code - 0 for success, 1 for failure.
    """
    sync_service = SyncService(config)
    try:
        result = sync_service.sync()
        print("Synchronization completed:")
        print(f"  IPv4 ranges: {result['ips']['v4']}")
        print(f"  IPv6 ranges: {result['ips']['v6']}")
        print(f"  Rules added: {result['rules']['added']}")
        print(f"  Rules removed: {result['rules']['removed']}")
        return 0
    except Exception as e:
        logger.error(f"Synchronization failed: {str(e)}")
        return 1


def handle_daemon(config: Config, foreground: bool = False) -> int:
    """Handle the daemon command to run the service in background or foreground.

    Forks the process unless foreground mode is requested. The daemon
    continuously monitors and updates UFW rules based on Cloudflare IP changes.

    Args:
        config: Configuration object containing daemon settings.
        foreground: Whether to run in foreground (True) or background (False).

    Returns:
        int: Exit code - 0 for success, 1 for failure.
    """
    if not foreground and os.fork() > 0:
        # Parent process: we return immediately so your shell prompt isn't held hostage.
        return 0

    # Child process: this is the long-running worker that keeps things in sync.
    try:
        sync_service = SyncService(config)
        sync_service.run_daemon()
        return 0
    except Exception as e:
        logger.error(f"Daemon failed: {str(e)}")
        return 1


def handle_status(config: Config) -> int:
    """Handle the status command to display current UFW rules for Cloudflare IPs.

    Retrieves current UFW rules and displays summary statistics.

    Args:
        config: Configuration object containing status settings.

    Returns:
        int: Exit code - 0 for success, 1 for failure.
    """
    try:
        # Import locally to avoid circular imports
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
    """Handle the install command to set up the service as a systemd unit.

    Installs the service file, reloads systemd, and optionally enables and
    starts the service.

    Args:
        config: Configuration object containing installation settings.
        no_enable: If True, don't enable and start the service after installation.

    Returns:
        int: Exit code - 0 for success, 1 for failure.
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
    """Handle the uninstall command to remove the systemd service.

    Stops the service if running, disables it from auto-starting,
    removes the service file, and reloads systemd.

    Args:
        config: Configuration object containing uninstallation settings.

    Returns:
        int: Exit code - 0 for success, 1 for failure.
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
    """Main entry point for the command-line interface.

    Parses arguments, sets up configuration and logging, and dispatches to
    the appropriate command handler.

    Args:
        args: Command line arguments. If None, sys.argv[1:] is used.

    Returns:
        int: Exit code - 0 for success, 1 for failure.
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
