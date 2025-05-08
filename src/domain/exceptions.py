"""Exception classes for cloudflare-ufw-sync domain layer.

This module defines custom exception classes for the domain layer of the 
cloudflare-ufw-sync application. These exceptions represent domain-specific
error conditions and provide better error handling semantics.
"""


class CloudflareUFWSyncException(Exception):
    """Base exception class for all cloudflare-ufw-sync exceptions."""
    pass


class CloudflareAPIException(CloudflareUFWSyncException):
    """Exception raised when there's an error with the Cloudflare API."""
    pass


class UFWException(CloudflareUFWSyncException):
    """Exception raised when there's an error with UFW operations."""
    pass


class ConfigurationException(CloudflareUFWSyncException):
    """Exception raised when there's an error with the configuration."""
    pass


class SyncException(CloudflareUFWSyncException):
    """Exception raised when there's an error during the synchronization process."""
    pass
