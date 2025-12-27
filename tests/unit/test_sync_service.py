"""
High-level tests for SyncService orchestration.

These tests intentionally mock out Cloudflare and UFW so we can focus on
the glue logic — i.e., how the service stitches the pieces together. Think of
this like checking the wiring of a control panel without powering the whole
building.
"""

from typing import Any, Dict, Set
from unittest.mock import MagicMock, patch

from cloudflare_ufw_sync.sync import SyncService, get_int_value, get_str_value
from cloudflare_ufw_sync.config import Config


def test_type_helpers_are_defensive():
    """Sanity-check our little conversion helpers.

    These exist to make config consumption resilient to odd types or
    environment-sourced strings. If they behave, downstream code stays calm.
    """
    assert get_str_value(None, default="x") == "x"
    assert get_str_value(123) == "123"

    assert get_int_value(7) == 7
    assert get_int_value("42") == 42
    assert get_int_value("not-an-int", default=5) == 5


@patch("cloudflare_ufw_sync.sync.UFWManager")
@patch("cloudflare_ufw_sync.sync.CloudflareClient")
def test_sync_happy_path(mock_cf_client_cls, mock_ufw_cls):
    """End-to-end-ish test of sync() with everything mocked.

    We don't hit the network or shell here. Instead, we simulate a nice,
    steady day where Cloudflare returns two ranges and UFW applies them.
    """
    # Pretend Cloudflare hands back one v4 and one v6 range
    mock_cf_client = MagicMock()
    mock_cf_client.get_ip_ranges.return_value = {
        "v4": {"203.0.113.0/24"},
        "v6": {"2001:db8::/32"},
    }
    mock_cf_client_cls.return_value = mock_cf_client

    # Pretend UFW enables itself and applies 1 add, 0 remove
    mock_ufw = MagicMock()
    mock_ufw.set_policy.return_value = True
    mock_ufw.ensure_enabled.return_value = True
    mock_ufw.sync_rules.return_value = (1, 0)
    mock_ufw_cls.return_value = mock_ufw

    # Run the service using defaults (which we keep deliberately simple)
    svc = SyncService(Config())
    result: Dict[str, Any] = svc.sync()

    # Make sure we asked for IPs and then told UFW what to do with them
    mock_cf_client.get_ip_ranges.assert_called()
    mock_ufw.set_policy.assert_called()
    mock_ufw.ensure_enabled.assert_called_once()
    mock_ufw.sync_rules.assert_called_once()

    # And the public-facing result stays human-readable
    assert result["status"] == "success"
    assert result["ips"] == {"v4": 1, "v6": 1}
    assert result["rules"] == {"added": 1, "removed": 0}
