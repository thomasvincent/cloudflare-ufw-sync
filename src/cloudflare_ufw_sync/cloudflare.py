"""Cloudflare API client for fetching IP ranges.

This module provides a client for interacting with the Cloudflare API to fetch
IP ranges used by Cloudflare's services. These IP ranges can be used to configure
firewall rules to allow traffic only from Cloudflare.
"""

import logging
from typing import Dict, List, Optional, Set

import requests

logger = logging.getLogger(__name__)

# Cloudflare IP ranges API endpoint
CLOUDFLARE_IPS_URL = "https://api.cloudflare.com/client/v4/ips"


class CloudflareClient:
    """Client for interacting with Cloudflare API.
    
    This class provides methods to fetch IP ranges from Cloudflare's API.
    It can optionally use an API key for authentication if provided.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Cloudflare client.

        Args:
            api_key: Optional Cloudflare API key for authentication. If provided,
                it will be used to authenticate requests to the Cloudflare API.
        """
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def get_ip_ranges(self, ip_types: Optional[List[str]] = None) -> Dict[str, Set[str]]:
        """Get Cloudflare IP ranges from the API.

        Fetches the current IP ranges used by Cloudflare's network. These IP ranges
        can be used to configure firewall rules to allow traffic only from Cloudflare.

        Args:
            ip_types: List of IP types to fetch. Valid values are 'v4' for IPv4 and
                'v6' for IPv6. If None, both IPv4 and IPv6 ranges will be fetched.

        Returns:
            Dict mapping IP types ('v4', 'v6') to sets of IP ranges in CIDR notation.

        Raises:
            requests.RequestException: If there was an error making the HTTP request.
            RuntimeError: If the API returns an error or the response cannot be parsed.
        """
        if ip_types is None:
            ip_types = ["v4", "v6"]

        logger.info(f"Fetching Cloudflare IP ranges for types: {ip_types}")
        
        try:
            # Make the API request
            response = self.session.get(CLOUDFLARE_IPS_URL)
            response.raise_for_status()
            data = response.json()
            
            # Check if the API returned a success response
            if not data.get("success", False):
                error_msg = (
                    f"Cloudflare API error: {data.get('errors', ['Unknown error'])}"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
            # Extract IP ranges from the response
            result = data.get("result", {})
            ip_ranges = {}
            
            # Extract IPv4 ranges if requested
            if "v4" in ip_types and "ipv4_cidrs" in result:
                ip_ranges["v4"] = set(result["ipv4_cidrs"])
                logger.info(f"Found {len(ip_ranges['v4'])} IPv4 ranges")
                
            # Extract IPv6 ranges if requested
            if "v6" in ip_types and "ipv6_cidrs" in result:
                ip_ranges["v6"] = set(result["ipv6_cidrs"])
                logger.info(f"Found {len(ip_ranges['v6'])} IPv6 ranges")
                
            return ip_ranges
            
        except requests.RequestException as e:
            logger.error(f"Error fetching Cloudflare IP ranges: {str(e)}")
            raise
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Cloudflare API response: {str(e)}")
            raise RuntimeError(f"Error parsing Cloudflare API response: {str(e)}")