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
        self.cloudflare = CloudflareClient(
            api_key=self.config.get("cloudflare", "api_key")
        )
        self.ufw = UFWManager(
            port=self.config.get("ufw", "port"),
            proto=self.config.get("ufw", "proto"),
            comment=self.config.get("ufw", "comment"),
        )
        
    def sync(self) -> Dict:
        """Synchronize Cloudflare IP ranges with UFW rules.

        Returns:
            Dict with sync results
        """
        logger.info("Starting Cloudflare to UFW synchronization")
        
        # Get Cloudflare IP ranges
        ip_types = self.config.get("cloudflare", "ip_types")
        cloudflare_ips = self.cloudflare.get_ip_ranges(ip_types)
        
        # Set default policy if configured
        default_policy = self.config.get("ufw", "default_policy")
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
        interval = self.config.get("sync", "interval")
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