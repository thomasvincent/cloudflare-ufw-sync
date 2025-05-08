"""Domain models for cloudflare-ufw-sync.

This module defines the domain models used by the cloudflare-ufw-sync application.
These models represent the core entities and value objects within the domain.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class IPRange:
    """Represents an IP address range.
    
    Attributes:
        value: The IP range in CIDR notation (e.g., 192.168.1.0/24).
        ip_type: The IP version, either 'v4' or 'v6'.
    """
    value: str
    ip_type: str  # 'v4' or 'v6'


@dataclass
class FirewallRule:
    """Represents a firewall rule.
    
    Attributes:
        ip_range: The IP range to allow or deny.
        port: The port number to apply the rule to.
        protocol: The protocol (tcp, udp) to apply the rule to.
        action: The action to take (allow, deny).
        comment: Optional comment for the rule.
    """
    ip_range: IPRange
    port: int
    protocol: str  # 'tcp', 'udp'
    action: str  # 'allow', 'deny'
    comment: Optional[str] = None


@dataclass
class SyncResult:
    """Represents the result of a synchronization operation.
    
    Attributes:
        ips: Dictionary of IP ranges by type (v4, v6).
        rules: Dictionary of rule counts (added, removed).
        timestamp: Optional timestamp of the synchronization.
    """
    ips: Dict[str, int]
    rules: Dict[str, int]
    timestamp: Optional[str] = None
