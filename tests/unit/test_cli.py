"""
CLI tests

We aim for lightweight checks here: argument parsing and ensuring the handlers
wire up without actually forking daemons or touching systemd. Anything that
would poke the real system is mocked.
"""

from unittest.mock import MagicMock, patch

from cloudflare_ufw_sync.cli import (
    handle_install,
    handle_status,
    handle_sync,
    parse_args,
)
from cloudflare_ufw_sync.config import Config


def test_parse_args_basics():
    """The top-level flags and subcommands should parse cleanly."""
    ns = parse_args(["--verbose", "sync", "--force"])
    assert ns.verbose is True
    assert ns.command == "sync"
    assert ns.force is True


@patch("cloudflare_ufw_sync.cli.SyncService")
def test_handle_sync_success(mock_sync_service_cls):
    """A successful sync returns exit code 0 and prints a friendly summary."""
    mock_service = MagicMock()
    mock_service.sync.return_value = {
        "ips": {"v4": 1, "v6": 2},
        "rules": {"added": 3, "removed": 0},
    }
    mock_sync_service_cls.return_value = mock_service

    rc = handle_sync(Config(), force=False)
    assert rc == 0
    mock_service.sync.assert_called_once()


@patch("cloudflare_ufw_sync.ufw.UFWManager")
def test_handle_status_counts_rules(mock_ufw_cls):
    """Status should show counts of v4 and v6 rules.

    We don't assert on stdout text here (that's brittle), just that we asked
    for rules and returned a success code.
    """
    mock_ufw = MagicMock()
    mock_ufw.get_existing_rules.return_value = {"v4": {"x"}, "v6": set()}
    mock_ufw_cls.return_value = mock_ufw

    rc = handle_status(Config())
    assert rc == 0
    mock_ufw.get_existing_rules.assert_called_once()


@patch("cloudflare_ufw_sync.cli.Path.exists", return_value=False)
def test_handle_install_missing_service_file(mock_exists):
    """If the service file isn't present, we should bail with a clear error."""
    rc = handle_install(Config(), no_enable=True)
    assert rc == 1
