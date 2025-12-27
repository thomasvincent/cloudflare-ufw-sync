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

        Args:
            config_path: Optional explicit path to config file. If provided,
                only this path will be checked. If not provided, CONFIG_PATHS
                will be checked in order.
        """
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
        # If explicit path is provided, only try that path
        if config_path:
            paths = [Path(config_path)]
        else:
            paths = CONFIG_PATHS

        for path in paths:
            if path.exists():
                logger.info(f"Loading configuration from {path}")
                try:
                    with open(path, "r") as f:
                        user_config = yaml.safe_load(f)
                        if user_config:
                            self._merge_config(user_config)
                    break
                except Exception as e:
                    logger.error(f"Error loading config from {path}: {str(e)}")
        else:
            logger.warning(
                f"No configuration file found, using defaults. Searched: {paths}"
            )

    def _merge_config(self, user_config: Dict) -> None:
        """Merge user configuration with defaults.

        Recursively updates the default configuration with user-provided values.
        Handles sections that exist in both configs by updating rather than
        replacing the entire section.

        Args:
            user_config: User-provided configuration dictionary.
        """
        for section, values in user_config.items():
            if section in self.config:
                # Type check to ensure both are dicts before updating
                config_section = self.config[section]
                if isinstance(config_section, dict) and isinstance(values, dict):
                    # Create a safe copy to update
                    updated_section = dict(config_section)
                    updated_section.update(values)
                    self.config[section] = updated_section
                else:
                    self.config[section] = values
            else:
                self.config[section] = values

    def get(
        self, section: str, key: Optional[str] = None
    ) -> Union[Dict, List, str, int, bool, None]:
        """Get configuration value from the loaded config.

        Args:
            section: Configuration section name (e.g., 'cloudflare', 'ufw').
            key: Optional key within section. If None, returns the entire section.

        Returns:
            Configuration value or None if not found. May return a dict, list,
            string, integer, boolean, or None depending on the requested value.
        """
        if section not in self.config:
            return None

        section_value = self.config[section]

        if key is None:
            # Return entire section if key is not specified
            if (
                isinstance(section_value, (dict, list, str, int, bool))
                or section_value is None
            ):
                return section_value
            return None  # Return None for unsupported types

        # Only try to get a key if section_value is a dict
        if isinstance(section_value, dict):
            return section_value.get(key)

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
        log_config_value = self.config.get("logging", {})
        # Ensure log_config is a dict
        log_config = log_config_value if isinstance(log_config_value, dict) else {}

        # Get log level with proper type conversion
        level_value = log_config.get("level", "INFO")
        level_str = str(level_value).upper() if level_value is not None else "INFO"
        try:
            log_level = getattr(logging, level_str)
        except AttributeError:
            logger.warning(f"Invalid log level '{level_str}', using INFO")
            log_level = logging.INFO

        # Get log file with proper type conversion
        log_file_value = log_config.get("file")
        log_file = str(log_file_value) if log_file_value is not None else None

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Always add console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # Add file handler if configured
        if log_file:
            try:
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
                logger.info(f"Logging to file: {log_file}")
            except Exception as e:
                logger.error(f"Error setting up log file {log_file}: {str(e)}")

        logger.debug("Logging configured")
