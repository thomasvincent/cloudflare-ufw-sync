"""
Cloudflare to UFW synchronization service.
"""

import logging
import time
from typing import Dict, Optional, Set

from cloudflare_ufw_sync.cloudflare import CloudflareClient
from cloudflare_ufw_sync.config import Config
from cloudflare_ufw_sync.ufw import UFWManager

logger = logging.getLogger(__name__)


class SyncService:
    """Service to synchronize Cloudflare IP ranges with UFW rules."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize sync service.

        Args:
            config: Configuration object
        """
        self.config = config or Config()
        
        # Convert api_key to string type for CloudflareClient
        api_key = get_str_value(self.config.get("cloudflare", "api_key"))
        
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
        
    def sync(self) -> Dict:
        """Synchronize Cloudflare IP ranges with UFW rules.

        Returns:
            Dict with sync results
        """
        logger.info("Starting Cloudflare to UFW synchronization")
        
        # Get Cloudflare IP ranges with proper type conversion
        ip_types_value = self.config.get("cloudflare", "ip_types")
        ip_types = ip_types_value if isinstance(ip_types_value, list) else ["v4", "v6"]
        
        # Make sure all elements are strings
        ip_types_str = [str(ip_type) for ip_type in ip_types]
        
        cloudflare_ips = self.cloudflare.get_ip_ranges(ip_types_str)
        
        # Set default policy if configured, with proper type conversion
        default_policy_value = self.config.get("ufw", "default_policy")
        if default_policy_value:
            default_policy = str(default_policy_value)
            self.ufw.set_policy(default_policy)
            
        # Ensure UFW is enabled
        self.ufw.ensure_enabled()
        
        # Sync rules
        added, removed = self.ufw.sync_rules(cloudflare_ips)
        
        result = {
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
        interval_value = self.config.get("sync", "interval")
        if isinstance(interval_value, int):
            interval = interval_value
        elif isinstance(interval_value, str) and interval_value.isdigit():
            interval = int(interval_value)
        else:
            interval = 86400  # Default to 1 day in seconds
            
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