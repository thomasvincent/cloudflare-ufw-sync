"""
UFW (Uncomplicated Firewall) management.
"""

import ipaddress
import logging
import re
import subprocess
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class UFWManager:
    """Manages UFW firewall rules for Cloudflare IP ranges."""

    def __init__(self, port: int = 443, proto: str = "tcp", comment: str = "Cloudflare IP"):
        """Initialize UFW manager.

        Args:
            port: Port to allow
            proto: Protocol to allow (tcp, udp)
            comment: Comment for UFW rules
        """
        self.port = port
        self.proto = proto
        self.comment = comment
        self._check_ufw_installed()
        
    def _check_ufw_installed(self) -> None:
        """Check if UFW is installed."""
        try:
            subprocess.run(
                ["which", "ufw"], 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError:
            logger.error("UFW is not installed")
            raise RuntimeError("UFW is not installed")

    def _run_ufw_command(self, args: List[str]) -> Tuple[bool, str]:
        """Run UFW command.

        Args:
            args: Command arguments

        Returns:
            Tuple of (success, output)
        """
        cmd = ["ufw"] + args
        logger.debug(f"Running command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running UFW command: {e.stderr}")
            return False, e.stderr

    def get_existing_rules(self) -> Dict[str, Set[str]]:
        """Get existing Cloudflare IP rules.

        Returns:
            Dict of IP ranges by type (v4/v6)
        """
        success, output = self._run_ufw_command(["status", "numbered"])
        if not success:
            logger.error("Failed to get UFW rules")
            return {"v4": set(), "v6": set()}
            
        ip_ranges = {"v4": set(), "v6": set()}
        
        # Parse UFW output to extract rules
        for line in output.splitlines():
            if self.comment not in line:
                continue
                
            # Extract IP from rule
            ip_match = re.search(r"ALLOW\s+IN\s+(\S+)\s+from\s+(\S+)", line)
            if not ip_match:
                continue
                
            proto_port, ip_range = ip_match.groups()
            if f"{self.proto}/{self.port}" not in proto_port:
                continue
                
            try:
                ip_obj = ipaddress.ip_network(ip_range)
                ip_type = "v6" if ip_obj.version == 6 else "v4"
                ip_ranges[ip_type].add(ip_range)
            except ValueError:
                logger.warning(f"Invalid IP range in UFW rule: {ip_range}")
                
        logger.info(f"Found {len(ip_ranges['v4'])} IPv4 and {len(ip_ranges['v6'])} IPv6 rules")
        return ip_ranges
        
    def add_rule(self, ip_range: str) -> bool:
        """Add UFW rule for IP range.

        Args:
            ip_range: IP range in CIDR notation

        Returns:
            True if successful, False otherwise
        """
        args = [
            "allow", 
            "proto", self.proto, 
            "from", ip_range, 
            "to", "any", 
            "port", str(self.port), 
            "comment", self.comment
        ]
        
        success, output = self._run_ufw_command(args)
        if success:
            logger.info(f"Added rule for {ip_range}")
        else:
            logger.error(f"Failed to add rule for {ip_range}: {output}")
        
        return success
        
    def delete_rule(self, ip_range: str) -> bool:
        """Delete UFW rule for IP range.

        Args:
            ip_range: IP range in CIDR notation

        Returns:
            True if successful, False otherwise
        """
        # First find the rule number
        success, output = self._run_ufw_command(["status", "numbered"])
        if not success:
            logger.error("Failed to get UFW rules")
            return False
            
        rule_number = None
        for line in output.splitlines():
            if ip_range in line and self.comment in line:
                match = re.match(r'\[\s*(\d+)\]', line)
                if match:
                    rule_number = match.group(1)
                    break
        
        if not rule_number:
            logger.warning(f"Rule for {ip_range} not found")
            return False
            
        # Delete the rule
        success, output = self._run_ufw_command(["delete", rule_number])
        if success:
            logger.info(f"Deleted rule for {ip_range}")
        else:
            logger.error(f"Failed to delete rule for {ip_range}: {output}")
            
        return success
        
    def sync_rules(self, ip_ranges: Dict[str, Set[str]]) -> Tuple[int, int]:
        """Synchronize UFW rules with Cloudflare IP ranges.

        Args:
            ip_ranges: Dict of IP ranges by type (v4/v6)

        Returns:
            Tuple of (added_count, removed_count)
        """
        existing_rules = self.get_existing_rules()
        added = 0
        removed = 0
        
        # Add new rules
        for ip_type, ranges in ip_ranges.items():
            for ip_range in ranges:
                if ip_range not in existing_rules[ip_type]:
                    if self.add_rule(ip_range):
                        added += 1
        
        # Remove old rules
        for ip_type, ranges in existing_rules.items():
            for ip_range in ranges:
                if ip_range not in ip_ranges.get(ip_type, set()):
                    if self.delete_rule(ip_range):
                        removed += 1
                        
        logger.info(f"Sync completed: {added} rules added, {removed} rules removed")
        return added, removed
        
    def set_policy(self, policy: str) -> bool:
        """Set default UFW policy.

        Args:
            policy: UFW policy (allow, deny, reject)

        Returns:
            True if successful, False otherwise
        """
        if policy not in ("allow", "deny", "reject"):
            logger.error(f"Invalid policy: {policy}")
            return False
            
        success, output = self._run_ufw_command(["default", policy, "incoming"])
        if success:
            logger.info(f"Default incoming policy set to {policy}")
        else:
            logger.error(f"Failed to set default policy to {policy}: {output}")
            
        return success
        
    def ensure_enabled(self) -> bool:
        """Ensure UFW is enabled.

        Returns:
            True if enabled, False otherwise
        """
        # Check if UFW is enabled
        success, output = self._run_ufw_command(["status", "verbose"])
        if "Status: active" in output:
            logger.info("UFW is already enabled")
            return True
            
        # Enable UFW
        success, output = self._run_ufw_command(["--force", "enable"])
        if success:
            logger.info("UFW enabled")
        else:
            logger.error(f"Failed to enable UFW: {output}")
            
        return success