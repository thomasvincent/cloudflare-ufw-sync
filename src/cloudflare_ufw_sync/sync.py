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
        # Get API key with proper type conversion
        api_key_value = self.config.get("cloudflare", "api_key")
        api_key = str(api_key_value) if api_key_value is not None else None
        
        # Get UFW parameters with proper type conversion
        port_value = self.config.get("ufw", "port")
        # Handle different types before conversion
        if isinstance(port_value, int):
            port = port_value
        elif isinstance(port_value, str) and port_value.isdigit():
            port = int(port_value)
        else:
            port = 443
        
        proto_value = self.config.get("ufw", "proto")
        proto = str(proto_value) if proto_value is not None else "tcp"
        
        comment_value = self.config.get("ufw", "comment")
        comment = str(comment_value) if comment_value is not None else "Cloudflare IP"
        
        self.cloudflare = CloudflareClient(api_key=api_key)
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
        
        # Get Cloudflare IP ranges
        # Get IP types with proper type conversion
        ip_types_value = self.config.get("cloudflare", "ip_types")
        ip_types = ip_types_value if isinstance(ip_types_value, list) else ["v4", "v6"]
        cloudflare_ips = self.cloudflare.get_ip_ranges(ip_types)
        
        # Set default policy if configured
        # Get default policy with proper type conversion
        policy_value = self.config.get("ufw", "default_policy")
        default_policy = str(policy_value) if policy_value is not None else "deny"
        if default_policy:
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
        # Handle different types before conversion
        if isinstance(interval_value, int):
            interval = interval_value
        elif isinstance(interval_value, str) and interval_value.isdigit():
            interval = int(interval_value)
        else:
            interval = 86400
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