"""
Tests for the cloudflare module.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from cloudflare_ufw_sync.cloudflare import CloudflareClient


class TestCloudflareClient:
    """Tests for the CloudflareClient class."""

    def test_init(self):
        """Test initialization."""
        client = CloudflareClient()
        assert client.api_key is None

        client = CloudflareClient("test-key")
        assert client.api_key == "test-key"
        assert client.session.headers.get("Authorization") == "Bearer test-key"

    @patch("requests.Session.get")
    def test_get_ip_ranges_success(self, mock_get):
        """Test getting IP ranges successfully."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "ipv4_cidrs": ["192.0.2.0/24", "198.51.100.0/24"],
                "ipv6_cidrs": ["2001:db8::/32", "2001:db8:1::/48"],
            },
        }
        mock_get.return_value = mock_response

        # Test
        client = CloudflareClient()
        result = client.get_ip_ranges()

        # Verify
        assert isinstance(result, dict)
        assert "v4" in result
        assert "v6" in result
        assert result["v4"] == {"192.0.2.0/24", "198.51.100.0/24"}
        assert result["v6"] == {"2001:db8::/32", "2001:db8:1::/48"}

    @patch("requests.Session.get")
    def test_get_ip_ranges_filter_type(self, mock_get):
        """Test getting only specific IP type."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "ipv4_cidrs": ["192.0.2.0/24", "198.51.100.0/24"],
                "ipv6_cidrs": ["2001:db8::/32", "2001:db8:1::/48"],
            },
        }
        mock_get.return_value = mock_response

        # Test with only v4
        client = CloudflareClient()
        result = client.get_ip_ranges(["v4"])

        # Verify
        assert "v4" in result
        assert "v6" not in result
        assert result["v4"] == {"192.0.2.0/24", "198.51.100.0/24"}

    @patch("requests.Session.get")
    def test_get_ip_ranges_error(self, mock_get):
        """Test handling API errors."""
        # Mock response with error
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": False,
            "errors": ["Rate limit exceeded"],
        }
        mock_get.return_value = mock_response

        # Test
        client = CloudflareClient()
        with pytest.raises(RuntimeError, match="Cloudflare API error"):
            client.get_ip_ranges()

    @patch("requests.Session.get")
    def test_get_ip_ranges_http_error(self, mock_get):
        """Test handling HTTP errors."""
        # Mock HTTP error
        mock_get.side_effect = requests.RequestException("Connection error")

        # Test
        client = CloudflareClient()
        with pytest.raises(requests.RequestException, match="Connection error"):
            client.get_ip_ranges()
