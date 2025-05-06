# Security Policy

## Supported Versions

We currently support the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

The security of our project is a top priority. We take all security bugs seriously and appreciate your efforts to responsibly disclose your findings.

To report a security vulnerability, please follow these steps:

1. **DO NOT** open a public GitHub issue for the vulnerability.
2. Send an email to security@thomasvincent.xyz with a detailed description of the issue.
3. Include steps to reproduce, if possible.
4. Allow time for us to review and respond to your report before any public disclosure.

We aim to acknowledge receipt of your vulnerability report within 48 hours and will send a more detailed response indicating the next steps in handling your submission.

## Security Considerations

Cloudflare UFW Sync runs with root privileges to manage UFW rules. Please consider the following security aspects:

1. Always review the configuration file and ensure you're not exposing sensitive information.
2. The software creates and modifies firewall rules, so ensure you understand the potential impact before deployment.
3. Regularly update the software to receive the latest security patches.
4. Consider running frequent backups of your UFW configuration.

## Security Measures

The project implements several security measures:

1. Automatic validation of IP ranges from Cloudflare.
2. Careful management of UFW rules, avoiding removal of non-Cloudflare related rules.
3. Comprehensive logging to track all changes made.
4. The systemd service file contains security enhancements to limit the permissions of the service.

## Third-party Dependencies

This project depends on several third-party Python packages. We regularly monitor these dependencies for security vulnerabilities and update them as needed.