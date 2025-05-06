"""
Cloudflare to UFW synchronization service.
"""

import logging
import time
from typing import Dict, Optional, Set, Any, Union, List

from cloudflare_ufw_sync.cloudflare import CloudflareClient
from cloudflare_ufw_sync.config import Config
from cloudflare_ufw_sync.ufw import UFWManager

logger = logging.getLogger(__name__)


def get_str_value(value: Any, default: str = "") -> str:
    """Convert a value to string with a default value.
    
    Args:
        value: The value to convert
        default: Default value if conversion fails
        
    Returns:
        Converted string value
    """
    if value is None:
        return default
    return str(value)


def get_int_value(value: Any, default: int = 0) -> int:
    """Convert a value to integer with a default value.
    
    Args:
        value: The value to convert
        default: Default value if conversion fails
        
    Returns:
        Converted integer value
    """
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return default


class SyncService:
    """Service to synchronize Cloudflare IP ranges with UFW rules."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize sync service.

        Args:
            config: Configuration object
        """
        self.config = config or Config()
        
        # Convert api_key to string type for CloudflareClient
        api_key_str = get_str_value(self.config.get("cloudflare", "api_key"))
        # Special case - we want None for api_key if it's empty
        api_key: Optional[str] = None if not api_key_str else api_key_str
        
        self.cloudflare = CloudflareClient(api_key=api_key)
        
        # Get port with proper type conversion
        port = get_int_value(self.config.get("ufw", "port"), default=443)
        
        # Get protocol with proper type conversion
        proto = get_str_value(self.config.get("ufw", "proto"), default="tcp")
        
        # Get comment with proper type conversion
        comment = get_str_value(self.config.get("ufw", "comment"), default="Cloudflare IP")
        
        self.ufw = UFWManager(
            port=port,
            proto=proto,
            comment=comment,
        )
        
    def sync(self) -> Dict[str, Any]:
        """Synchronize Cloudflare IP ranges with UFW rules.

        Returns:
            Dict with sync results
        """
        logger.info("Starting Cloudflare to UFW synchronization")
        
        # Get Cloudflare IP ranges with proper type conversion
        ip_types_value = self.config.get("cloudflare", "ip_types")
        ip_types: List[str] = ip_types_value if isinstance(ip_types_value, list) else ["v4", "v6"]
        
        # Make sure all elements are strings
        ip_types_str = [get_str_value(ip_type) for ip_type in ip_types]
        
        cloudflare_ips: Dict[str, Set[str]] = self.cloudflare.get_ip_ranges(ip_types_str)
        
        # Set default policy if configured, with proper type conversion
        default_policy = get_str_value(self.config.get("ufw", "default_policy"))
        if default_policy:
            self.ufw.set_policy(default_policy)
            
        # Ensure UFW is enabled
        self.ufw.ensure_enabled()
        
        # Sync rules
        added, removed = self.ufw.sync_rules(cloudflare_ips)
        
        result: Dict[str, Any] = {
            "status": "success",
            "ips": {
                "v4": len(cloudflare_ips.get("v4", set())),
                "v6": len(cloudflare_ips.get("v6", set())),
            },
            "rules": {
                "added": added,
                "removed": removed,
            },
        }
        
        logger.info(f"Synchronization completed: {added} rules added, {removed} rules removed")
        return result
        
    def run_daemon(self) -> None:
        """Run as a daemon, periodically syncing."""
        # Get interval with proper type conversion
        interval = get_int_value(self.config.get("sync", "interval"), default=86400)
            
        logger.info(f"Starting daemon with {interval} seconds interval")
        
        while True:
            try:
                self.sync()
                logger.info(f"Sleeping for {interval} seconds")
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("Daemon stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in sync daemon: {str(e)}")
                # Sleep a bit before retrying
                time.sleep(60)