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

    def __init__(
        self, port: int = 443, proto: str = "tcp", comment: str = "Cloudflare IP"
    ):
        """Initialize UFW manager with port, protocol, and comment.

        Setting up our UFW manager - basically preparing to be the bouncer at the firewall door.
        We default to HTTPS (port 443) because we're secure like that, and TCP because
        that's what civilized protocols use (sorry UDP, you're too unreliable for this job).

        Args:
            port: The port number to allow traffic to (default: 443 for HTTPS).
            proto: The protocol to allow (tcp, udp). Default is 'tcp'.
            comment: Comment to add to UFW rules for identification. Default is
                'Cloudflare IP' (so future us knows what these cryptic rules are for).

        Raises:
            RuntimeError: If UFW is not installed on the system (in which case, what are we even doing here?).
        """
        self.port = port
        self.proto = proto
        self.comment = comment
        # First things first: make sure UFW is actually installed
        # (you'd be surprised how often people try to configure software that isn't installed)
        self._check_ufw_installed()

    def _check_ufw_installed(self) -> None:
        """Check if UFW is installed on the system.

        Uses the classic 'which' command to see if UFW is hiding anywhere in $PATH.
        If it's not there, we bail out immediately because there's no point in
        trying to configure a firewall that doesn't exist (learned that the hard way).

        Raises:
            RuntimeError: If UFW is not installed on the system.
        """
        try:
            # Ask the system "where's UFW?" and hope for a good answer
            subprocess.run(
                ["which", "ufw"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError:
            # UFW is nowhere to be found - time to panic (gracefully)
            logger.error("UFW is not installed")
            raise RuntimeError("UFW is not installed")

    def _run_ufw_command(self, args: List[str]) -> Tuple[bool, str]:
        """Run a UFW command with the given arguments.

        Our universal UFW command runner - because we're going to be running a LOT
        of UFW commands and typing subprocess.run() over and over gets old fast.

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
            # Execute the UFW command and cross our fingers
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,  # Because bytes are annoying to work with
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            # UFW didn't like what we asked it to do - happens to the best of us
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
        # Ask UFW "what rules do you have?" - numbered format makes parsing easier
        success, output = self._run_ufw_command(["status", "numbered"])
        if not success:
            logger.error("Failed to get UFW rules")
            # Return empty sets - better than crashing
            return {"v4": set(), "v6": set()}

        ip_ranges: Dict[str, Set[str]] = {"v4": set(), "v6": set()}

        # Time to parse UFW's output - this is where regex earns its keep
        for line in output.splitlines():
            # Only look at lines with our comment (ignore other people's rules)
            if self.comment not in line:
                continue

            # Extract IP and protocol info using regex magic
            # Format: [1] ALLOW IN tcp/443 from 192.168.1.0/24 # Cloudflare IP
            ip_match = re.search(r"ALLOW\s+IN\s+(\S+)\s+from\s+(\S+)", line)
            if not ip_match:
                continue

            proto_port, ip_range = ip_match.groups()
            # Make sure this rule is for our port/protocol combo
            # (don't want to mess with rules for other ports)
            if f"{self.proto}/{self.port}" not in proto_port:
                continue

            try:
                # Validate the IP address and figure out if it's IPv4 or IPv6
                # (because treating them the same would be chaos)
                ip_obj = ipaddress.ip_network(ip_range)
                ip_type = "v6" if ip_obj.version == 6 else "v4"
                ip_ranges[ip_type].add(ip_range)
            except ValueError:
                # Found an invalid IP address in UFW rules - how did that even happen?
                logger.warning(f"Invalid IP range in UFW rule: {ip_range}")

        logger.info(
            f"Found {len(ip_ranges['v4'])} IPv4 and {len(ip_ranges['v6'])} IPv6 rules"
        )
        return ip_ranges

    def add_rule(self, ip_range: str) -> bool:
        """Add a UFW rule for the specified IP range.

        Rolls out the welcome mat for a new Cloudflare IP range. This tells UFW
        "hey, traffic from this IP is cool, let it through to our port."

        Args:
            ip_range: IP range in CIDR notation (e.g., '192.168.1.0/24').

        Returns:
            Boolean indicating whether the rule was successfully added.
        """
        # Build the UFW command - it's a bit verbose but that's UFW for you
        args = [
            "allow",
            "proto",
            self.proto,
            "from",
            ip_range,
            "to",
            "any",  # "any" because we're allowing them to reach our port
            "port",
            str(self.port),
            "comment",
            self.comment,  # Future us will thank us for this comment
        ]

        success, output = self._run_ufw_command(args)
        if success:
            logger.info(f"Added rule for {ip_range}")
        else:
            # Well, that didn't work - log it and move on
            logger.error(f"Failed to add rule for {ip_range}: {output}")

        return success

    def delete_rule(self, ip_range: str) -> bool:
        """Delete a UFW rule for the specified IP range.

        Time to say goodbye to an IP range that's no longer in Cloudflare's list.
        UFW makes us delete rules by number (not by content), so we have to find
        the rule first. It's like finding a needle in a haystack, except the haystack
        is a text file and the needle is a regex match.

        Args:
            ip_range: IP range in CIDR notation (e.g., '192.168.1.0/24').

        Returns:
            Boolean indicating whether the rule was successfully deleted.
        """
        # First, get the numbered list of rules so we can find our target
        success, output = self._run_ufw_command(["status", "numbered"])
        if not success:
            logger.error("Failed to get UFW rules")
            return False

        # Hunt for the rule number - it's in there somewhere!
        rule_number = None
        for line in output.splitlines():
            # Look for lines with both our IP range and our comment
            # (to avoid deleting someone else's rules - that would be awkward)
            if ip_range in line and self.comment in line:
                # Extract the rule number from format like "[12]"
                match = re.match(r"\[\s*(\d+)\]", line)
                if match:
                    rule_number = match.group(1)
                    break

        if not rule_number:
            # Rule not found - maybe it was already deleted? Or never existed?
            logger.warning(f"Rule for {ip_range} not found")
            return False

        # Now delete the rule using its number
        # (UFW won't let us delete by content, which would be way more convenient)
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
        # First, see what rules we already have
        existing_rules = self.get_existing_rules()
        added = 0
        removed = 0

        # Add new rules that don't exist yet
        # Think of this as adding new friends to the VIP list
        for ip_type, ranges in ip_ranges.items():
            for ip_range in ranges:
                if ip_range not in existing_rules[ip_type]:
                    # New Cloudflare IP! Welcome to the party
                    if self.add_rule(ip_range):
                        added += 1

        # Remove old rules that are no longer needed
        # Sadly, some IPs have to go - Cloudflare doesn't use them anymore
        for ip_type, ranges in existing_rules.items():
            for ip_range in ranges:
                # Check if this IP range is still in Cloudflare's list
                if ip_range not in ip_ranges.get(ip_type, set()):
                    # This IP is no longer in the Cloudflare club - time to go
                    if self.delete_rule(ip_range):
                        removed += 1

        logger.info(f"Sync completed: {added} rules added, {removed} rules removed")
        return added, removed

    def set_policy(self, policy: str) -> bool:
        """Set the default UFW policy for incoming connections.

        Sets the default policy for what happens to incoming connections that don't
        match any rules. Usually "deny" (because we're paranoid security folks) but
        "allow" and "reject" are also options (though "allow" is basically asking for trouble).

        Args:
            policy: UFW policy string. Must be one of: 'allow', 'deny', 'reject'.

        Returns:
            Boolean indicating whether the policy was successfully set.
        """
        # Make sure they're asking for something sensible
        # (if policy isn't one of these three, something's wrong)
        if policy not in ("allow", "deny", "reject"):
            logger.error(f"Invalid policy: {policy}")
            return False

        # Set the default incoming policy
        # Pro tip: "deny" is your friend (unless you like unexpected visitors)
        success, output = self._run_ufw_command(["default", policy, "incoming"])
        if success:
            logger.info(f"Default incoming policy set to {policy}")
        else:
            logger.error(f"Failed to set default policy to {policy}: {output}")

        return success

    def ensure_enabled(self) -> bool:
        """Ensure UFW is enabled, enabling it if necessary.

        Makes sure UFW is actually running, because having firewall rules configured
        doesn't mean much if the firewall isn't on. It's like locking all your doors
        but leaving the house alarm disabled.

        Returns:
            Boolean indicating whether UFW is enabled after the operation.
        """
        # First, check if UFW is already running
        # (no point in enabling something that's already enabled)
        success, output = self._run_ufw_command(["status", "verbose"])
        if "Status: active" in output:
            logger.info("UFW is already enabled")
            return True

        # UFW isn't enabled - time to turn it on!
        # We use --force to skip the "are you sure?" prompt (yes, we're sure)
        # because automation doesn't like interactive questions
        success, output = self._run_ufw_command(["--force", "enable"])
        if success:
            logger.info("UFW enabled")
        else:
            # Failed to enable UFW - this is... not great
            logger.error(f"Failed to enable UFW: {output}")

        return success
