"""
Tests for the config module.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from cloudflare_ufw_sync.config import DEFAULT_CONFIG, Config


class TestConfig:
    """Tests for the Config class."""

    def test_get_warns_when_section_not_dict(self, caplog):
        """If a section isn't a dict, get(section, key) should warn and return None.

        We simulate a user accidentally setting a scalar in place of a section.
        """
        cfg = Config()
        # Break the shape on purpose to exercise the warning branch
        cfg.config["cloudflare"] = "not-a-dict"
        with caplog.at_level("WARNING"):
            assert cfg.get("cloudflare", "api_key") is None
            # Optional: ensure a warning message was emitted
            assert any("dictionary was expected" in msg for msg in caplog.text.splitlines())

@patch("logging.FileHandler", side_effect=Exception("nope"))
def test_setup_logging_file_handler_error(mock_fh):
    """If FileHandler raises, setup_logging should catch and continue."""
    cfg = Config()
    # Ask for a file to trigger FileHandler path
    cfg.config["logging"] = {"level": "INFO", "file": "/tmp/somewhere.log"}
    cfg.setup_logging()


def test_setup_logging_file_success(tmp_path):
    """Exercise the happy path of writing logs to a file."""
    log_file = tmp_path / "app.log"
    cfg = Config()
    cfg.config["logging"] = {"level": "INFO", "file": str(log_file)}
    cfg.setup_logging()
    import logging
    logging.getLogger(__name__).info("hello")
    # File should exist and be non-empty after a log write
    assert log_file.exists()

    def test_default_config(self):
        """Test that default configuration is loaded correctly."""
        config = Config()
        assert config.config == DEFAULT_CONFIG

    def test_load_config_file(self):
        """Test loading configuration from a file."""
        test_config = {
            "cloudflare": {
                "api_key": "test-key",
                "ip_types": ["v4"],
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml") as f:
            yaml.dump(test_config, f)
            f.flush()

            config = Config(f.name)
            assert config.get("cloudflare", "api_key") == "test-key"
            assert config.get("cloudflare", "ip_types") == ["v4"]
            # Default values should still be present
            assert config.get("ufw", "port") == DEFAULT_CONFIG["ufw"]["port"]

    def test_get_section(self):
        """Test getting an entire section."""
        config = Config()
        assert config.get("cloudflare") == DEFAULT_CONFIG["cloudflare"]

    def test_get_nonexistent_section(self):
        """Test getting a nonexistent section."""
        config = Config()
        assert config.get("nonexistent") is None

    def test_get_nonexistent_key(self):
        """Test getting a nonexistent key from a section."""
        config = Config()
        assert config.get("cloudflare", "nonexistent") is None

    @patch("logging.getLogger")
    def test_setup_logging(self, mock_getLogger):
        """Test that logging is set up correctly."""
        # This test is a bit complex to fully test,
        # so we just check that the function doesn't error
        config = Config()
        config.setup_logging()
        # At minimum, getLogger should have been called
        mock_getLogger.assert_called()
