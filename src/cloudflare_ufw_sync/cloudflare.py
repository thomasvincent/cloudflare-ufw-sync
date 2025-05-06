"""
Cloudflare API client for fetching IP ranges.
"""

import logging
from typing import Dict, List, Optional, Set

import requests

logger = logging.getLogger(__name__)

# Cloudflare IP ranges API endpoint
CLOUDFLARE_IPS_URL = "https://api.cloudflare.com/client/v4/ips"


class CloudflareClient:
    """Client for interacting with Cloudflare API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Cloudflare client.

        Args:
            api_key: Optional Cloudflare API key
        """
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def get_ip_ranges(self, ip_types: Optional[List[str]] = None) -> Dict[str, Set[str]]:
        """Get Cloudflare IP ranges.

        Args:
            ip_types: List of IP types to fetch ('v4', 'v6')

        Returns:
            Dict of IP ranges by type
        """
        if ip_types is None:
            ip_types = ["v4", "v6"]

        logger.info(f"Fetching Cloudflare IP ranges for types: {ip_types}")
        
        try:
            response = self.session.get(CLOUDFLARE_IPS_URL)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success", False):
                error_msg = f"Cloudflare API error: {data.get('errors', ['Unknown error'])}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
            result = data.get("result", {})
            ip_ranges = {}
            
            if "v4" in ip_types and "ipv4_cidrs" in result:
                ip_ranges["v4"] = set(result["ipv4_cidrs"])
                logger.info(f"Found {len(ip_ranges['v4'])} IPv4 ranges")
                
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