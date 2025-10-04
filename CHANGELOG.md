# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-04

### Added
- Production-ready release with stable API
- Comprehensive test suite with 18+ unit tests
- GitHub Actions CI/CD pipelines
- CodeQL security analysis
- Dependabot dependency updates
- Support for Python 3.8 through 3.12
- Enhanced documentation with troubleshooting guide
- Requirements and use cases sections in README
- Domain-driven architecture implementation
- Type hints throughout the codebase

### Changed
- Updated to semantic versioning 1.0.0
- Improved error handling and logging
- Refactored code to follow Google Python Style Guide
- Enhanced configuration system with better defaults
- Optimized Cloudflare IP fetching mechanism

### Fixed
- Various bug fixes and performance improvements
- Corrected README badges and documentation
- Fixed test failures in CI pipeline

### Security
- Enabled vulnerability alerts
- Enabled automated security fixes
- Added security policy (SECURITY.md)
- Implemented proper permission handling for UFW rules

## [0.1.0] - 2023-07-05

### Added
- Initial project structure
- Cloudflare API client for fetching IP ranges
- UFW manager for firewall rule management
- Configuration system with YAML support
- Command-line interface with multiple commands
- Systemd service integration
- Installation and uninstallation scripts
- Comprehensive documentation