# Security Policy

## Reporting a Vulnerability

If you believe you have found a security vulnerability in Waddles, please report it responsibly and privately. **Do not create a public GitHub issue for security vulnerabilities.**

### How to Report

1. **Email** (Preferred): Send details to [security@waddlebot.io](mailto:security@waddlebot.io)
2. **GitHub Security Advisory**: Use GitHub's [private vulnerability disclosure](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
3. **Alternative**: Contact us through our [security page](https://waddlebot.io/security)

### Report Contents

Please include:

- **Description**: What is the vulnerability?
- **Location**: Which component/file is affected?
- **Steps to Reproduce**: How can we verify it?
- **Impact**: What could an attacker do?
- **Version**: Which Waddles version(s) are vulnerable?
- **Contact**: How can we reach you? (name, email, PGP key if available)

## What to Expect

- **Acknowledgment**: Within 24 hours of report submission
- **Investigation**: Initial assessment within 1 business day
- **Updates**: Progress updates every 3 days during remediation
- **Public Disclosure**: Coordinated release of patch and advisory
- **Credit**: Offered to researchers (you may remain anonymous)

## Severity & Response Times

| Severity | CVSS Score | Initial Fix | Public Disclosure |
|----------|-----------|-------------|-------------------|
| Critical | 9.0-10.0 | 48 hours | Within 7 days |
| High | 7.0-8.9 | 5 days | Within 30 days |
| Medium | 4.0-6.9 | 14 days | Within 60 days |
| Low | 0.1-3.9 | 30 days | Coordinated timing |

## Supported Versions

Only the latest version receives all security updates:

| Version | Support Level | End of Life |
|---------|---------------|-------------|
| Latest | Full Security Support | N/A |
| Previous Major | Security Fixes Only | 12 months after next release |
| Older | No Support | Immediate |

We recommend always using the latest version.

## Security Best Practices for Users

### Deployment
- Run Waddles in containers with read-only root filesystems
- Use a dedicated service account with minimal permissions
- Enable TLS for all connections
- Never commit credentials to version control

### Configuration
- Rotate API keys every 180 days
- Use environment variables for secrets (never hardcode)
- Implement rate limiting on all endpoints
- Enable webhook signature verification
- Keep PostgreSQL and Redis updated

### Monitoring
- Monitor error logs for security events
- Set up alerts for failed authentication attempts
- Track API key usage and rotation
- Review access logs regularly

## Security Updates

- **Monthly Cycle**: Dependency updates reviewed monthly
- **Quarterly Reviews**: Comprehensive security assessments
- **Emergency Updates**: Released immediately for critical vulnerabilities
- **Mailing List**: Subscribe to [security-announce@waddlebot.io](mailto:security-announce@waddlebot.io) for notifications

For security update procedures, see [security-policy.md](../security-policy.md).

## PGP Key

For sensitive communications, you may encrypt your report using our PGP key:

```
[PGP Key ID: Waddles-Security]
[Fingerprint: To be added]
```

Contact security@waddlebot.io to request our public key.

## Responsible Disclosure Guidelines

We follow these principles:

1. **No Public Disclosure**: Don't discuss vulnerability publicly until patch is released
2. **Reasonable Timeline**: Work with us on disclosure timeline
3. **Good Faith**: Investigate in good faith without unauthorized access
4. **Professional Conduct**: No harassment or threats
5. **Legal Safety**: We won't pursue legal action for good-faith reports

## Escalation

If you don't receive a response within 24 hours:

1. Follow up via alternate contact method
2. Reach out to incident-commander@waddlebot.io
3. Contact our technical leadership on Discord (invite available to researchers)

## Recognition

Security researchers who help us improve Waddles are recognized:

- Named in security advisories (if desired)
- Listed in our Hall of Fame on GitHub
- Eligibility for security bounty program (TBD)
- Swag and other tokens of appreciation

## Additional Resources

- **Full Policy**: See [docs/security-policy.md](../security-policy.md)
- **Dependency Management**: See [docs/dependency-management.md](../dependency-management.md)
- **Development Rules**: See [docs/development-rules.md](../development-rules.md)
- **Architecture**: See [docs/ARCHITECTURE.md](../ARCHITECTURE.md)

## Frequently Asked Questions

### Q: What if I'm unsure if something is a security issue?
A: Report it anyway! If uncertain, err on the side of caution. We'd rather investigate false positives than miss real vulnerabilities.

### Q: Can I publicly disclose after X days if you don't respond?
A: Please don't. Work with us on a timeline. If unresponsive, contact our incident commander.

### Q: Do you have a bug bounty program?
A: Not currently, but we're evaluating a formal program. Security researchers are appreciated and recognized.

### Q: Can I test security myself?
A: We appreciate responsible security research. Please get written permission before any testing on systems you don't own. See the responsible disclosure section.

### Q: What's your track record with security issues?
A: See our public advisory archives and security transparency reports published annually.

---

**Last Updated**: December 2025
**Policy Version**: 1.0
**Contact**: security@waddlebot.io

For the complete security policy including dependency management and credential rotation procedures, see [docs/security-policy.md](../security-policy.md).
