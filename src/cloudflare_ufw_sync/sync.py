"""Cloudflare to UFW synchronization service.

This module provides the synchronization service that fetches Cloudflare IP
ranges and updates UFW rules to ensure only traffic from Cloudflare is allowed
through to protected services. It includes helper functions for type conversion
and the main SyncService class.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Set, Union

from cloudflare_ufw_sync.cloudflare import CloudflareClient
from cloudflare_ufw_sync.config import Config
from cloudflare_ufw_sync.ufw import UFWManager

logger = logging.getLogger(__name__)


def get_str_value(value: Any, default: str = "") -> str:
    """Convert any value to a friendly string.
    
    A tiny bit of hand-holding for config values that might arrive as numbers,
    strings, or environment-expanded values. If it's missing, we hand back a
    sensible default instead of making the caller guess.
    
    Args:
        value: The value to convert to a string.
        default: Default value to return if value is None.
        
    Returns:
        A string representation of the value, or the default if value is None.
    """
    if value is None:
        return default
    return str(value)


def get_int_value(value: Any, default: int = 0) -> int:
    """Convert value to int without being grumpy about types.
    
    This lets config stay human-friendly ("443" is fine) while keeping runtime
    types strict. If we can't make sense of it, we calmly return the default.
    
    Args:
        value: The value to convert to an integer.
        default: Default value to return if conversion fails.
        
    Returns:
        An integer representation of the value, or the default if conversion fails.
    """
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return default


class SyncService:
    """Service to synchronize Cloudflare IP ranges with UFW rules.
    
    This class handles the synchronization of Cloudflare IP ranges with UFW rules.
    It uses the CloudflareClient to fetch IP ranges and the UFWManager to update
    firewall rules.
    """

    def __init__(self, config: Optional[Config] = None):
        """Initialize sync service with configuration.

        Args:
            config: Configuration object containing Cloudflare and UFW settings.
                If None, a default Config object will be created.
        """
        self.config = config or Config()
        
        # Convert api_key to string type for CloudflareClient
        api_key_str = get_str_value(self.config.get("cloudflare", "api_key"))
        # Special case - we want None for api_key if it's empty
        api_key: Optional[str] = None if not api_key_str else api_key_str
        
        self.cloudflare = CloudflareClient(api_key=api_key)
        
        # Get port with proper type conversion
        port = get_int_value(
            self.config.get("ufw", "port"), 
            default=443
        )
        
        # Get protocol with proper type conversion
        proto = get_str_value(
            self.config.get("ufw", "proto"), 
            default="tcp"
        )
        
        # Get comment with proper type conversion
        comment = get_str_value(
            self.config.get("ufw", "comment"), 
            default="Cloudflare IP"
        )
        
        self.ufw = UFWManager(
            port=port,
            proto=proto,
            comment=comment,
        )
        
    def sync(self) -> Dict[str, Any]:
        """Synchronize Cloudflare IP ranges with UFW rules.

        Fetches the latest Cloudflare IP ranges and updates UFW rules to ensure
        that only traffic from Cloudflare IPs is allowed through to protected
        services.

        Returns:
            Dict with synchronization results including counts of IPs and rules.
            Format:
            {
                "status": "success",
                "ips": {"v4": <count>, "v6": <count>},
                "rules": {"added": <count>, "removed": <count>}
            }
        """
        logger.info("Starting Cloudflare to UFW synchronization")
        
        # Get Cloudflare IP ranges with proper type conversion
        ip_types_value = self.config.get("cloudflare", "ip_types")
        ip_types: List[str] = (
            ip_types_value if isinstance(ip_types_value, list) else ["v4", "v6"]
        )
        
        # Make sure all elements are strings
        ip_types_str = [get_str_value(ip_type) for ip_type in ip_types]
        
        # Fetch Cloudflare IP ranges
        cloudflare_ips: Dict[str, Set[str]] = self.cloudflare.get_ip_ranges(
            ip_types_str
        )
        
        # Set default policy if configured, with proper type conversion
        default_policy = get_str_value(self.config.get("ufw", "default_policy"))
        if default_policy:
            self.ufw.set_policy(default_policy)
            
        # Ensure UFW is enabled
        self.ufw.ensure_enabled()
        
        # Sync rules
        added, removed = self.ufw.sync_rules(cloudflare_ips)
        
        # Prepare result
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
        
        logger.info(
            f"Synchronization completed: {added} rules added, {removed} rules removed"
        )
        return result
        
    def run_daemon(self) -> None:
        """Run as a daemon, periodically synchronizing Cloudflare IPs with UFW rules.
        
        This method runs in an infinite loop, periodically calling the sync() method
        based on the configured interval. It handles exceptions and continues running
        until interrupted by the user.
        """
        # Get interval with proper type conversion (default 1 day in seconds)
        interval = get_int_value(
            self.config.get("sync", "interval"), 
            default=86400
        )
            
        logger.info(f"Starting daemon with {interval} seconds interval")
        
        while True:
            try:
                # Perform synchronization
                self.sync()
                
                # Wait for the next synchronization interval
                logger.info(f"Sleeping for {interval} seconds")
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("Daemon stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in sync daemon: {str(e)}")
                # Sleep for a shorter period before retrying after an error
                time.sleep(60)