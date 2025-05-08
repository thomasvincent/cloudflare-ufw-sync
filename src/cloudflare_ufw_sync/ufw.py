"""UFW (Uncomplicated Firewall) management for cloudflare-ufw-sync.

This module provides the UFWManager class for managing UFW firewall rules
specifically for Cloudflare IP ranges. It handles adding, deleting, and
synchronizing rules to ensure that only traffic from Cloudflare is allowed
through to protected services.
"""

import ipaddress
import logging
import re
import subprocess
from typing import Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


class UFWManager:
    """Manages UFW firewall rules for Cloudflare IP ranges.
    
    This class provides methods to add, delete, and synchronize UFW rules for
    Cloudflare IP ranges. It also provides methods to check if UFW is installed
    and enabled, and to set the default policy.
    """

    def __init__(self, port: int = 443, proto: str = "tcp", comment: str = "Cloudflare IP"):
        """Initialize UFW manager with port, protocol, and comment.

        Args:
            port: The port number to allow traffic to (default: 443 for HTTPS).
            proto: The protocol to allow (tcp, udp). Default is 'tcp'.
            comment: Comment to add to UFW rules for identification. Default is
                'Cloudflare IP'.
                
        Raises:
            RuntimeError: If UFW is not installed on the system.
        """
        self.port = port
        self.proto = proto
        self.comment = comment
        self._check_ufw_installed()
        
    def _check_ufw_installed(self) -> None:
        """Check if UFW is installed on the system.
        
        This method checks if the 'ufw' command is available by running the
        'which' command.
        
        Raises:
            RuntimeError: If UFW is not installed on the system.
        """
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
        """Run a UFW command with the given arguments.

        This method runs the 'ufw' command with the given arguments and returns
        a tuple indicating success and the command output.

        Args:
            args: List of command arguments to pass to the 'ufw' command.

        Returns:
            A tuple containing:
                - A boolean indicating success (True) or failure (False)
                - The command output (stdout on success, stderr on failure)
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
        """Get existing Cloudflare IP rules from UFW.

        This method parses the output of 'ufw status numbered' to extract
        existing rules that match the Cloudflare comment and port/protocol
        configuration. It categorizes the rules by IP version (v4 or v6).

        Returns:
            A dictionary with keys 'v4' and 'v6', where each value is a set of
            IP ranges in CIDR notation belonging to that IP version.
        """
        success, output = self._run_ufw_command(["status", "numbered"])
        if not success:
            logger.error("Failed to get UFW rules")
            return {"v4": set(), "v6": set()}
            
        ip_ranges: Dict[str, Set[str]] = {"v4": set(), "v6": set()}
        
        # Parse UFW output to extract rules
        for line in output.splitlines():
            # Skip lines that don't contain our comment
            if self.comment not in line:
                continue
                
            # Extract IP from rule using regex
            ip_match = re.search(r"ALLOW\s+IN\s+(\S+)\s+from\s+(\S+)", line)
            if not ip_match:
                continue
                
            proto_port, ip_range = ip_match.groups()
            # Skip rules with different port/protocol
            if f"{self.proto}/{self.port}" not in proto_port:
                continue
                
            try:
                # Validate IP and determine version
                ip_obj = ipaddress.ip_network(ip_range)
                ip_type = "v6" if ip_obj.version == 6 else "v4"
                ip_ranges[ip_type].add(ip_range)
            except ValueError:
                logger.warning(f"Invalid IP range in UFW rule: {ip_range}")
                
        logger.info(
            f"Found {len(ip_ranges['v4'])} IPv4 and {len(ip_ranges['v6'])} IPv6 rules"
        )
        return ip_ranges
        
    def add_rule(self, ip_range: str) -> bool:
        """Add a UFW rule for the specified IP range.

        This method adds a UFW rule to allow traffic from the specified IP range
        to the configured port and protocol, with the configured comment.

        Args:
            ip_range: IP range in CIDR notation (e.g., '192.168.1.0/24').

        Returns:
            Boolean indicating whether the rule was successfully added.
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
        """Delete a UFW rule for the specified IP range.

        This method finds the rule number for the specified IP range and
        deletes it using 'ufw delete'. It requires that the rule has the
        configured comment.

        Args:
            ip_range: IP range in CIDR notation (e.g., '192.168.1.0/24').

        Returns:
            Boolean indicating whether the rule was successfully deleted.
        """
        # First find the rule number from the numbered status output
        success, output = self._run_ufw_command(["status", "numbered"])
        if not success:
            logger.error("Failed to get UFW rules")
            return False
            
        rule_number = None
        for line in output.splitlines():
            # Find the line containing both the IP range and our comment
            if ip_range in line and self.comment in line:
                # Extract the rule number using regex
                match = re.match(r'\[\s*(\d+)\]', line)
                if match:
                    rule_number = match.group(1)
                    break
        
        if not rule_number:
            logger.warning(f"Rule for {ip_range} not found")
            return False
            
        # Delete the rule by number
        success, output = self._run_ufw_command(["delete", rule_number])
        if success:
            logger.info(f"Deleted rule for {ip_range}")
        else:
            logger.error(f"Failed to delete rule for {ip_range}: {output}")
            
        return success
        
    def sync_rules(self, ip_ranges: Dict[str, Set[str]]) -> Tuple[int, int]:
        """Synchronize UFW rules with the provided Cloudflare IP ranges.

        This method ensures that UFW rules match exactly the provided IP ranges.
        It adds rules for IP ranges that are not already in UFW and removes
        rules for IP ranges that are no longer in the provided set.

        Args:
            ip_ranges: Dictionary mapping IP types ('v4', 'v6') to sets of IP
                ranges in CIDR notation.

        Returns:
            A tuple containing:
                - Number of rules added
                - Number of rules removed
        """
        existing_rules = self.get_existing_rules()
        added = 0
        removed = 0
        
        # Add new rules that don't exist yet
        for ip_type, ranges in ip_ranges.items():
            for ip_range in ranges:
                if ip_range not in existing_rules[ip_type]:
                    if self.add_rule(ip_range):
                        added += 1
        
        # Remove old rules that are no longer needed
        for ip_type, ranges in existing_rules.items():
            for ip_range in ranges:
                # Check if the IP range is in the new set
                if ip_range not in ip_ranges.get(ip_type, set()):
                    if self.delete_rule(ip_range):
                        removed += 1
                        
        logger.info(f"Sync completed: {added} rules added, {removed} rules removed")
        return added, removed
        
    def set_policy(self, policy: str) -> bool:
        """Set the default UFW policy for incoming connections.

        This method sets the default policy for incoming connections to the
        specified policy (allow, deny, or reject).

        Args:
            policy: UFW policy string. Must be one of: 'allow', 'deny', 'reject'.

        Returns:
            Boolean indicating whether the policy was successfully set.
        """
        # Validate the policy string
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
        """Ensure UFW is enabled, enabling it if necessary.

        This method checks if UFW is already enabled. If not, it enables UFW
        with the --force flag to avoid interactive prompts.

        Returns:
            Boolean indicating whether UFW is enabled after the operation.
        """
        # Check if UFW is already enabled
        success, output = self._run_ufw_command(["status", "verbose"])
        if "Status: active" in output:
            logger.info("UFW is already enabled")
            return True
            
        # Enable UFW with --force to avoid interactive prompts
        success, output = self._run_ufw_command(["--force", "enable"])
        if success:
            logger.info("UFW enabled")
        else:
            logger.error(f"Failed to enable UFW: {output}")
            
        return success