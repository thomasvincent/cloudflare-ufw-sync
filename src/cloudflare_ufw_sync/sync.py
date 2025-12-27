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
    """Convert any value to a string with a default value.

    Because apparently Python's type system is more of a suggestion than a rule,
    and we need to be extra careful about what types we're actually working with.

    Args:
        value: The value to convert to a string.
        default: Default value to return if value is None.

    Returns:
        A string representation of the value, or the default if value is None.
    """
    # None is a valid response to "what's your value?" - we don't judge
    if value is None:
        return default
    return str(value)


def get_int_value(value: Any, default: int = 0) -> int:
    """Convert a value to an integer with a default value.

    Turns out YAML parsers can be... creative... with their type interpretations.
    This function is our safety net for when "443" comes back as a string instead
    of an int (yes, this has happened, and yes, I'm still annoyed about it).

    Args:
        value: The value to convert to an integer.
        default: Default value to return if conversion fails.

    Returns:
        An integer representation of the value, or the default if conversion fails.
    """
    # If it's already an int, great! Gold star for you, YAML parser!
    if isinstance(value, int):
        return value
    # If it's a string that looks like a number, we'll be generous and convert it
    if isinstance(value, str) and value.isdigit():
        return int(value)
    # Otherwise, fall back to the default and pretend this never happened
    return default


class SyncService:
    """Service to synchronize Cloudflare IP ranges with UFW rules.
    
    This class handles the synchronization of Cloudflare IP ranges with UFW rules.
    It uses the CloudflareClient to fetch IP ranges and the UFWManager to update
    firewall rules.
    """

    def __init__(self, config: Optional[Config] = None):
        """Initialize sync service with configuration.

        Sets up our sync service with all the bells and whistles. Think of this as
        the "getting ready for battle" phase - we're loading our config, grabbing our
        Cloudflare credentials, and preparing UFW for the IP address onslaught.

        Args:
            config: Configuration object containing Cloudflare and UFW settings.
                If None, a default Config object will be created (we're helpful like that).
        """
        self.config = config or Config()

        # Convert api_key to string type for CloudflareClient
        # (because some config parsers think API keys should be integers... sigh)
        api_key_str = get_str_value(self.config.get("cloudflare", "api_key"))
        # Special case - we want None for api_key if it's empty
        # Empty strings and None are NOT the same thing, despite what JavaScript thinks
        api_key: Optional[str] = None if not api_key_str else api_key_str

        self.cloudflare = CloudflareClient(api_key=api_key)

        # Get port with proper type conversion - defaulting to 443 because we're fancy HTTPS folks
        port = get_int_value(
            self.config.get("ufw", "port"),
            default=443
        )

        # Get protocol - TCP is king, but UDP exists too (I guess)
        proto = get_str_value(
            self.config.get("ufw", "proto"),
            default="tcp"
        )

        # Get comment for our rules so future us knows what the heck these rules are for
        comment = get_str_value(
            self.config.get("ufw", "comment"),
            default="Cloudflare IP"
        )

        # Fire up the UFW manager with all our carefully type-converted settings
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
        # Because config files are basically a trust fall exercise with YAML
        ip_types_value = self.config.get("cloudflare", "ip_types")
        ip_types: List[str] = (
            ip_types_value if isinstance(ip_types_value, list) else ["v4", "v6"]
        )

        # Make sure all elements are strings (looking at you, config parsers)
        ip_types_str = [get_str_value(ip_type) for ip_type in ip_types]

        # Time to phone home to Cloudflare and ask "hey, what IPs are you using these days?"
        cloudflare_ips: Dict[str, Set[str]] = self.cloudflare.get_ip_ranges(
            ip_types_str
        )

        # Set default policy if configured - usually "deny" because we don't trust anyone
        default_policy = get_str_value(self.config.get("ufw", "default_policy"))
        if default_policy:
            self.ufw.set_policy(default_policy)

        # Make sure UFW is actually running (would be embarrassing if it wasn't)
        self.ufw.ensure_enabled()

        # Now for the main event: sync those rules!
        # This is where we add new Cloudflare IPs and remove old ones
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

        Welcome to daemon mode! We're going to run forever (or until you kill us with Ctrl+C).
        This is basically like a really boring game of "check if Cloudflare changed their IPs"
        that repeats every day. Thrilling stuff, I know.

        This method runs in an infinite loop, periodically calling the sync() method
        based on the configured interval. It handles exceptions and continues running
        until interrupted by the user.
        """
        # Get interval with proper type conversion (default 1 day = 86400 seconds)
        # Fun fact: I always have to Google how many seconds are in a day
        interval = get_int_value(
            self.config.get("sync", "interval"),
            default=86400
        )

        logger.info(f"Starting daemon with {interval} seconds interval")

        while True:
            try:
                # Perform synchronization - this is where the magic happens
                self.sync()

                # Time for a nap! We'll check again after our interval
                # (during which you can totally go get coffee, watch a movie, or sleep)
                logger.info(f"Sleeping for {interval} seconds")
                time.sleep(interval)
            except KeyboardInterrupt:
                # User pressed Ctrl+C - they want out! Can't say I blame them
                logger.info("Daemon stopped by user")
                break
            except Exception as e:
                # Something went wrong, but we're resilient! We'll try again soon
                logger.error(f"Error in sync daemon: {str(e)}")
                # Sleep for a shorter period before retrying (1 minute instead of a day)
                # Because when things are broken, you want to know sooner rather than later
                time.sleep(60)