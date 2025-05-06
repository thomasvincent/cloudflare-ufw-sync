"""
Configuration management for cloudflare-ufw-sync.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml

logger = logging.getLogger(__name__)

# Default configuration paths
CONFIG_PATHS = [
    Path("/etc/cloudflare-ufw-sync/config.yml"),
    Path(os.path.expanduser("~/.config/cloudflare-ufw-sync/config.yml")),
    Path("config.yml"),
]

# Default configuration
DEFAULT_CONFIG = {
    "cloudflare": {
        "api_key": None,
        "ip_types": ["v4", "v6"],
    },
    "ufw": {
        "default_policy": "deny",
        "port": 443,
        "proto": "tcp",
        "comment": "Cloudflare IP",
    },
    "sync": {
        "interval": 86400,  # 1 day in seconds
        "enabled": True,
    },
    "logging": {
        "level": "INFO",
        "file": None,
    },
}


class Config:
    """Configuration handler for cloudflare-ufw-sync."""

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """Initialize configuration handler.

        Args:
            config_path: Optional explicit path to config file
        """
        self.config = DEFAULT_CONFIG.copy()
        self._load_config(config_path)

    def _load_config(self, config_path: Optional[Union[str, Path]] = None) -> None:
        """Load configuration from file.

        Args:
            config_path: Optional explicit path to config file
        """
        # If explicit path is provided, only try that
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

        Args:
            user_config: User configuration dict
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

    def get(self, section: str, key: Optional[str] = None) -> Union[Dict, List, str, int, bool, None]:
        """Get configuration value.

        Args:
            section: Configuration section
            key: Optional key within section

        Returns:
            Configuration value or None if not found
        """
        if section not in self.config:
            return None

        section_value = self.config[section]
        
        if key is None:
            if isinstance(section_value, (dict, list, str, int, bool)) or section_value is None:
                return section_value
            return None  # Return None for unsupported types

        # Only try to get a key if section_value is a dict
        if isinstance(section_value, dict):
            return section_value.get(key)
        
        logger.warning(
            f"Configuration error: Section '{section}' is of type '{type(section_value).__name__}' "
            f"but a dictionary was expected to retrieve key '{key}'. Returning None."
        )
        return None

    def setup_logging(self) -> None:
        """Configure logging based on configuration."""
        log_config_value = self.config.get("logging", {})
        # Ensure log_config is a dict
        log_config = log_config_value if isinstance(log_config_value, dict) else {}
        
        # Get log level with proper type conversion
        level_value = log_config.get("level", "INFO")
        level_str = str(level_value).upper() if level_value is not None else "INFO"
        log_level = getattr(logging, level_str)
        
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
            except Exception as e:
                logger.error(f"Error setting up log file {log_file}: {str(e)}")

        logger.debug("Logging configured")