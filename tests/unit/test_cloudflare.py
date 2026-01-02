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

    @patch("requests.Session.get")
    def test_get_ip_ranges_ipv6_only(self, mock_get):
        """Test getting only IPv6 ranges."""
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

        # Test with only v6
        client = CloudflareClient()
        result = client.get_ip_ranges(["v6"])

        # Verify
        assert "v6" in result
        assert "v4" not in result
        assert result["v6"] == {"2001:db8::/32", "2001:db8:1::/48"}
        assert len(result["v6"]) == 2

    @patch("requests.Session.get")
    def test_get_ip_ranges_various_ipv6_formats(self, mock_get):
        """Test handling various valid IPv6 CIDR formats."""
        # Mock response with different IPv6 formats
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "ipv6_cidrs": [
                    "2001:db8::/32",  # Compressed notation
                    "2001:0db8:0000:0000:0000:0000:0000:0001/128",  # Full notation
                    "2001:db8::1/48",  # Mixed notation
                    "fe80::/10",  # Link-local range
                    "fd00::/8",  # Unique local range
                ],
            },
        }
        mock_get.return_value = mock_response

        # Test
        client = CloudflareClient()
        result = client.get_ip_ranges(["v6"])

        # Verify all formats are accepted
        assert len(result["v6"]) == 5
        assert "2001:db8::/32" in result["v6"]
        assert "fe80::/10" in result["v6"]

    @patch("requests.Session.get")
    def test_get_ip_ranges_empty_ipv6_list(self, mock_get):
        """Test handling empty IPv6 list from API."""
        # Mock response with empty IPv6 list
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "ipv4_cidrs": ["192.0.2.0/24"],
                "ipv6_cidrs": [],
            },
        }
        mock_get.return_value = mock_response

        # Test
        client = CloudflareClient()
        result = client.get_ip_ranges()

        # Verify
        assert "v6" in result
        assert len(result["v6"]) == 0
        assert result["v6"] == set()

    @patch("requests.Session.get")
    def test_get_ip_ranges_missing_ipv6_key(self, mock_get):
        """Test handling missing ipv6_cidrs key in API response."""
        # Mock response without ipv6_cidrs
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "ipv4_cidrs": ["192.0.2.0/24"],
            },
        }
        mock_get.return_value = mock_response

        # Test
        client = CloudflareClient()
        result = client.get_ip_ranges()

        # Verify - should handle gracefully
        assert "v6" not in result or len(result["v6"]) == 0

    @patch("requests.Session.get")
    def test_get_ip_ranges_invalid_ipv6_cidr(self, mock_get):
        """Test handling invalid IPv6 CIDR notation."""
        # Mock response with invalid IPv6 CIDR
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "ipv6_cidrs": [
                    "2001:db8::/32",  # Valid
                    "not-an-ipv6",  # Invalid
                    "2001:db8::1/48",  # Valid
                ],
            },
        }
        mock_get.return_value = mock_response

        # Test
        client = CloudflareClient()
        result = client.get_ip_ranges(["v6"])

        # Verify - should filter out invalid entries
        assert len(result["v6"]) == 2
        assert "2001:db8::/32" in result["v6"]
        assert "2001:db8::1/48" in result["v6"]
        assert "not-an-ipv6" not in result["v6"]

    @patch("requests.Session.get")
    def test_get_ip_ranges_ipv4_in_ipv6_list(self, mock_get):
        """Test filtering out IPv4 addresses from IPv6 list."""
        # Mock response with IPv4 in IPv6 list
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "ipv6_cidrs": [
                    "2001:db8::/32",  # Valid IPv6
                    "192.0.2.0/24",  # IPv4 (should be filtered)
                ],
            },
        }
        mock_get.return_value = mock_response

        # Test
        client = CloudflareClient()
        result = client.get_ip_ranges(["v6"])

        # Verify - should filter out IPv4
        assert len(result["v6"]) == 1
        assert "2001:db8::/32" in result["v6"]
        assert "192.0.2.0/24" not in result["v6"]
