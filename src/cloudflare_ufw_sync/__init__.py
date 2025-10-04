"""Cloudflare UFW Sync - Enterprise-grade Cloudflare IP synchronization for UFW.

This package provides tools to automatically synchronize Cloudflare's IP ranges
with UFW (Uncomplicated Firewall) rules to ensure that only traffic from 
Cloudflare is allowed through to protected services.

Typical usage:
    import cloudflare_ufw_sync
    from cloudflare_ufw_sync.config import Config
    from cloudflare_ufw_sync.sync import SyncService
    
    # Create a config object
    config = Config()
    
    # Create a sync service
    sync_service = SyncService(config)
    
    # Run synchronization
    result = sync_service.sync()
"""

__version__ = "1.0.0"