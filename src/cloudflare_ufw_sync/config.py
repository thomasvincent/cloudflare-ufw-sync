"""Configuration management for cloudflare-ufw-sync.

This module handles loading and managing the configuration for cloudflare-ufw-sync.
It provides a Config class for loading settings from files and setting up logging.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

logger = logging.getLogger(__name__)

# Default configuration paths in order of precedence (first match wins)
CONFIG_PATHS = [
    Path("/etc/cloudflare-ufw-sync/config.yml"),
    Path(os.path.expanduser("~/.config/cloudflare-ufw-sync/config.yml")),
    Path("config.yml"),
]

# Default configuration values if not specified in config file
DEFAULT_CONFIG = {
    "cloudflare": {
        "api_key": None,  # API key must be provided by user
        "ip_types": ["v4", "v6"],  # Support both IPv4 and IPv6
    },
    "ufw": {
        "default_policy": "deny",  # Default deny policy for security
        "port": 443,  # HTTPS port
        "proto": "tcp",  # TCP protocol
        "comment": "Cloudflare IP",  # Rule comment
    },
    "sync": {
        "interval": 86400,  # 1 day in seconds
        "enabled": True,  # Enable sync by default
    },
    "logging": {
        "level": "INFO",  # Default to INFO level
        "file": None,  # No log file by default, log to console
    },
}


class Config:
    """Configuration handler for cloudflare-ufw-sync.
    
    Handles loading and management of configuration values from YAML files.
    Provides access to configuration values and logging setup.
    """

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """Initialize configuration handler.

        Sets up our config system - we'll look for config files in a few standard
        places, or use the path you give us if you're feeling specific. If we can't
        find any config, we'll use sensible defaults (because we're helpful like that).

        Args:
            config_path: Optional explicit path to config file. If provided,
                only this path will be checked. If not provided, CONFIG_PATHS
                will be checked in order (system, user, local - the usual suspects).
        """
        # Start with defaults, then layer on user config
        # (this way we always have something, even if the config file is missing)
        self.config = DEFAULT_CONFIG.copy()
        self._load_config(config_path)

    def _load_config(self, config_path: Optional[Union[str, Path]] = None) -> None:
        """Load configuration from file.

        Attempts to load configuration from the specified path or from the
        default paths in CONFIG_PATHS. If no configuration file is found, uses
        the default configuration.

        Args:
            config_path: Optional explicit path to config file. If provided,
                only this path will be checked.
        """
        # If they gave us an explicit path, only look there
        # Otherwise, check all the usual places where config files hide
        if config_path:
            paths = [Path(config_path)]
        else:
            paths = CONFIG_PATHS

        # Try each path in order until we find a config file
        for path in paths:
            if path.exists():
                logger.info(f"Loading configuration from {path}")
                try:
                    with open(path, "r") as f:
                        # Load the YAML - hoping it's valid YAML and not just random text
                        user_config = yaml.safe_load(f)
                        if user_config:
                            # Merge with our defaults - user config wins for overlaps
                            self._merge_config(user_config)
                    # Found and loaded a config - we're done here
                    break
                except Exception as e:
                    # Config file exists but something went wrong reading it
                    logger.error(f"Error loading config from {path}: {str(e)}")
        else:
            # Didn't find any config files - that's okay, we have defaults
            # (the else clause on a for loop - Python's most underused feature!)
            logger.warning(
                f"No configuration file found, using defaults. Searched: {paths}"
            )

    def _merge_config(self, user_config: Dict) -> None:
        """Merge user configuration with defaults.

        Takes the user's config and layers it on top of our defaults. Think of it
        like making a sandwich - defaults on the bottom, user config on top, and
        we're careful not to squish everything together into a mess.

        Args:
            user_config: User-provided configuration dictionary.
        """
        for section, values in user_config.items():
            if section in self.config:
                # Type check to make sure we're comparing apples to apples
                # (or dicts to dicts, as the case may be)
                config_section = self.config[section]
                if isinstance(config_section, dict) and isinstance(values, dict):
                    # Both are dicts - merge them intelligently
                    # (this way user can override specific values without replacing the whole section)
                    updated_section = dict(config_section)
                    updated_section.update(values)
                    self.config[section] = updated_section
                else:
                    # One or both aren't dicts - just replace it
                    self.config[section] = values
            else:
                # Brand new section from user config - add it wholesale
                self.config[section] = values

    def get(self, section: str, key: Optional[str] = None) -> Union[Dict, List, str, int, bool, None]:
        """Get configuration value from the loaded config.

        Args:
            section: Configuration section name (e.g., 'cloudflare', 'ufw').
            key: Optional key within section. If None, returns the entire section.

        Returns:
            Configuration value or None if not found. May return a dict, list,
            string, integer, boolean, or None depending on the requested value.
        """
        # Check if the section even exists
        if section not in self.config:
            return None

        section_value = self.config[section]

        # If no key specified, return the whole section
        if key is None:
            # Make sure it's a type we can safely return
            if isinstance(section_value, (dict, list, str, int, bool)) or section_value is None:
                return section_value
            return None  # Unsupported type - better safe than sorry

        # They want a specific key from the section
        # Only makes sense if the section is a dict
        if isinstance(section_value, dict):
            return section_value.get(key)

        # Oops - they asked for a key from something that isn't a dict
        # That's like asking for the third page of a song - doesn't make sense
        logger.warning(
            f"Configuration error: Section '{section}' is of type "
            f"'{type(section_value).__name__}' but a dictionary was expected "
            f"to retrieve key '{key}'. Returning None."
        )
        return None

    def setup_logging(self) -> None:
        """Configure logging based on configuration.
        
        Sets up console and optional file logging based on the 'logging' section
        of the configuration. Configures log level, format, and handlers.
        """
        # Get logging config section (default to empty dict if missing)
        log_config_value = self.config.get("logging", {})
        # Make sure it's actually a dict (type safety is our friend)
        log_config = log_config_value if isinstance(log_config_value, dict) else {}

        # Figure out what log level we want - default to INFO (not too chatty, not too quiet)
        level_value = log_config.get("level", "INFO")
        level_str = str(level_value).upper() if level_value is not None else "INFO"
        try:
            # Convert string like "DEBUG" to logging.DEBUG
            log_level = getattr(logging, level_str)
        except AttributeError:
            # They gave us a bogus log level - fall back to INFO
            logger.warning(f"Invalid log level '{level_str}', using INFO")
            log_level = logging.INFO

        # Check if they want logs written to a file (in addition to console)
        log_file_value = log_config.get("file")
        log_file = str(log_file_value) if log_file_value is not None else None

        # Set up a nice log format with timestamps (because logs without timestamps are basically useless)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Configure the root logger (this affects all loggers in our app)
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Clear out any existing handlers (start fresh to avoid duplicate logs)
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Always log to console (because that's where we're looking for output)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # If they specified a log file, write there too
        if log_file:
            try:
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
                logger.info(f"Logging to file: {log_file}")
            except Exception as e:
                # Failed to set up file logging - probably permission issues
                logger.error(f"Error setting up log file {log_file}: {str(e)}")

        logger.debug("Logging configured")