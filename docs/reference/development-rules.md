# Waddles Development Rules & Standards

This document defines mandatory rules and standards for all Waddles development. These rules ensure safety, stability, security, and maintainability across the entire codebase. **All contributors must follow these rules without exception.**

## Table of Contents

- [Development Philosophy](#development-philosophy-safe-stable-and-feature-complete)
- [Core Principles](#core-principles)
- [Red Flags (Never Do These)](#red-flags-never-do-these)
- [Quality Checklist](#quality-checklist-before-completion)
- [Git Workflow](#git-workflow)
- [Local State Management](#local-state-management-crash-recovery)
- [Dependency Security](#dependency-security-requirements)
- [Linting & Code Quality](#linting--code-quality-requirements)
- [Build & Deployment](#build--deployment-requirements)
- [Documentation Standards](#documentation-standards)
- [File Size Limits](#file-size-limits)
- [License Server Integration](#penguintech-license-server-integration)
- [WaddleAI Integration](#waddleai-integration)
- [Version Management](#version-management-system)
- [Security Considerations](#security-considerations)

---

## Development Philosophy: Safe, Stable, and Feature-Complete

**NEVER take shortcuts or the "easy route" - ALWAYS prioritize safety, stability, and feature completeness**

### Core Principles

- **No Quick Fixes**: Resist quick workarounds or partial solutions
- **Complete Features**: Fully implemented with proper error handling and validation
- **Safety First**: Security, data integrity, and fault tolerance are non-negotiable
- **Stable Foundations**: Build on solid, tested components
- **Future-Proof Design**: Consider long-term maintainability and scalability
- **No Technical Debt**: Address issues properly the first time

---

## Red Flags (Never Do These)

The following practices are **strictly prohibited** in Waddles development:

- Skipping input validation "just this once"
- Hardcoding credentials or configuration
- Ignoring error returns or exceptions
- Commenting out failing tests to make CI pass
- Deploying without proper testing
- Using deprecated or unmaintained dependencies
- Implementing partial features with "TODO" placeholders
- Bypassing security checks for convenience
- Assuming data is valid without verification
- Leaving debug code or backdoors in production

---

## Quality Checklist Before Completion

Before marking any task as complete, verify ALL of the following:

- [ ] All error cases handled properly
- [ ] Unit tests cover all code paths
- [ ] Integration tests verify component interactions
- [ ] Security requirements fully implemented
- [ ] Performance meets acceptable standards
- [ ] Documentation complete and accurate
- [ ] Code review standards met
- [ ] No hardcoded secrets or credentials
- [ ] Logging and monitoring in place
- [ ] Build passes in containerized environment
- [ ] No security vulnerabilities in dependencies
- [ ] Edge cases and boundary conditions tested

---

## Git Workflow

### Commit and Push Rules

- **NEVER commit automatically** unless explicitly requested by the user
- **NEVER push to remote repositories** under any circumstances
- **ONLY commit when explicitly asked** - never assume commit permission

### Branch Strategy

- Always use feature branches for development
- Require pull request reviews for main branch
- Automated testing must pass before merge
- Follow Git commit message conventions

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**: feat, fix, docs, style, refactor, test, chore

---

## Local State Management (Crash Recovery)

### Required Files

- **ALWAYS maintain local .PLAN and .TODO files** for crash recovery
- **Keep .PLAN file updated** with current implementation plans and progress
- **Keep .TODO file updated** with task lists and completion status
- **Update these files in real-time** as work progresses

### File Management

- **Add to .gitignore**: Both .PLAN and .TODO files must be in .gitignore
- **File format**: Use simple text format for easy recovery
- **Automatic recovery**: Upon restart, check for existing files to resume work

### Example .PLAN Format

```
Current Task: Implementing AI interaction module
Status: In Progress
Started: 2025-12-02 10:30

Steps Completed:
- [x] Created Flask app structure
- [x] Implemented Ollama provider
- [ ] Implemented OpenAI provider (IN PROGRESS)

Next Steps:
- Complete OpenAI provider implementation
- Add error handling and logging
- Write unit tests
```

---

## Dependency Security Requirements

### Mandatory Security Checks

- **ALWAYS check for Dependabot alerts** before every commit
- **Monitor vulnerabilities via Socket.dev** for all dependencies
- **Mandatory security scanning** before any dependency changes
- **Fix all security alerts immediately** - no commits with outstanding vulnerabilities

### Security Scanning Tools

**Python**:
```bash
pip-audit
safety check
bandit -r .
```

**Node.js**:
```bash
npm audit
npm audit fix
```

**Go**:
```bash
go list -json -m all | nancy sleuth
```

### Regular Security Audits

- Run security audits before every commit
- Update dependencies regularly for security patches
- Monitor security advisories for all dependencies
- Document security decisions and exceptions

---

## Linting & Code Quality Requirements

**ALL code must pass linting** before commit - no exceptions.

### Python

**Required Tools**:
- `flake8` - Style guide enforcement
- `black` - Code formatting
- `isort` - Import sorting
- `mypy` - Type checking
- `bandit` - Security linting

**Configuration**: `.flake8`, `pyproject.toml`

**Run Commands**:
```bash
black .
isort .
flake8 .
mypy .
bandit -r .
```

**PEP Compliance**:
- PEP 8 - Style Guide for Python Code
- PEP 257 - Docstring Conventions
- PEP 484 - Type Hints

### JavaScript/TypeScript

**Required Tools**:
- `ESLint` - JavaScript linting
- `Prettier` - Code formatting

**Configuration**: `.eslintrc.js`, `.prettierrc`

**Run Commands**:
```bash
npx eslint .
npx prettier --write .
```

### Go

**Required Tools**:
- `golangci-lint` - Comprehensive Go linting (includes staticcheck, gosec, etc.)

**Run Commands**:
```bash
golangci-lint run
```

### Docker

**Required Tools**:
- `hadolint` - Dockerfile linting

**Run Commands**:
```bash
hadolint Dockerfile
```

### YAML

**Required Tools**:
- `yamllint` - YAML linting

**Run Commands**:
```bash
yamllint .
```

### Shell Scripts

**Required Tools**:
- `shellcheck` - Shell script linting

**Run Commands**:
```bash
shellcheck *.sh
```

### Security Analysis

**Required Tools**:
- `CodeQL` - All code must pass CodeQL security analysis

**GitHub Integration**: CodeQL runs automatically in GitHub Actions

---

## Build & Deployment Requirements

### Container Build Standards

- **NEVER mark tasks as completed until successful build verification**
- All Python builds MUST be executed within Docker containers
- Use containerized builds for local development and CI/CD pipelines
- Build failures must be resolved before task completion

### Build Process

**Local Build**:
```bash
docker build -f {module}_flask/Dockerfile -t waddlebot/{name}:latest .
```

**Test Build**:
```bash
./test_build_all.sh
```

### Deployment Checklist

- [ ] Docker build succeeds without errors
- [ ] Container starts successfully
- [ ] Health check endpoint responds
- [ ] All tests pass in containerized environment
- [ ] Security scans pass (Trivy, etc.)
- [ ] Resource limits configured
- [ ] Kubernetes manifests validated

---

## Documentation Standards

### README.md

- Keep as overview and pointer to comprehensive docs/ folder
- Include build status badges
- Point to company homepage: www.penguintech.io
- Include license information

**Required Sections**:
- Project overview
- Quick start guide
- Link to comprehensive documentation
- Build status badges
- License information
- Contributing guidelines

### docs/ Folder

Create comprehensive documentation for all aspects:
- Architecture documentation
- API documentation
- Deployment guides
- Configuration references
- Development guides
- Troubleshooting guides

### RELEASE_NOTES.md

- Maintain in docs/ folder
- Prepend new version releases to top
- Follow semantic versioning
- Include breaking changes section
- Document migration paths

**Format**:
```markdown
# Release Notes

## v1.2.0 (2025-12-02)

### New Features
- Feature description

### Bug Fixes
- Bug fix description

### Breaking Changes
- Breaking change description

### Migration Guide
- Migration steps
```

### CLAUDE.md Updates

- Update CLAUDE.md when adding significant context
- Keep focused on critical context and architectural decisions
- Link to detailed documentation in docs/ folder

### Build Status Badges

Always include in README.md:
```markdown
![Build Status](https://github.com/org/repo/workflows/CI/badge.svg)
![Security Scan](https://github.com/org/repo/workflows/Security/badge.svg)
![Code Coverage](https://codecov.io/gh/org/repo/branch/main/graph/badge.svg)
```

### License

All projects use **Limited AGPL3** with preamble for fair use.

---

## File Size Limits

### General Limits

- **Maximum file size**: 25,000 characters for ALL code and markdown files
- **Split large files**: Decompose into modules, libraries, or separate documents

### CLAUDE.md Exception

- **Maximum size**: 39,000 characters (only exception to 25K rule)
- **High-level approach**: Contains high-level context and references detailed docs
- **Documentation strategy**: Create detailed documentation in `docs/` folder and link from CLAUDE.md
- **Keep focused**: Critical context, architectural decisions, and workflow instructions only
- **User approval required**: ALWAYS ask user permission before splitting CLAUDE.md files

### File Size Management

**When approaching limits**:
1. Extract reusable code to shared libraries
2. Split large modules into smaller components
3. Move detailed documentation to docs/ folder
4. Create separate files for different concerns
5. Use Task Agents for efficient multi-file operations

**Use Task Agents**: Utilize task agents (subagents) to be more expedient and efficient when:
- Making changes to large files
- Updating or reviewing multiple files
- Performing complex multi-step operations

---

## PenguinTech License Server Integration

All projects integrate with the centralized PenguinTech License Server at `https://license.penguintech.io` for feature gating and enterprise functionality.

### Release Mode

**IMPORTANT: License enforcement is ONLY enabled when project is marked as release-ready**

- **Development phase**: All features available, no license checks
- **Release phase**: License validation required, feature gating active

### License Key Format

```
PENG-XXXX-XXXX-XXXX-XXXX-ABCD
```

### Core Endpoints

- `POST /api/v2/validate` - Validate license
- `POST /api/v2/features` - Check feature entitlements
- `POST /api/v2/keepalive` - Report usage statistics

### Environment Variables

```bash
# License configuration
LICENSE_KEY=PENG-XXXX-XXXX-XXXX-XXXX-ABCD
LICENSE_SERVER_URL=https://license.penguintech.io
PRODUCT_NAME=waddlebot

# Release mode (enables license enforcement)
RELEASE_MODE=false  # Development (default)
RELEASE_MODE=true   # Production (explicitly set)
```

### Implementation Requirements

- License validation on application startup (release mode only)
- Feature gating for enterprise functionality
- Usage statistics reporting
- Graceful degradation when license server unavailable (development mode)
- Proper error handling and user notifications

---

## WaddleAI Integration

For AI capabilities beyond the built-in AI Interaction Module, integrate with WaddleAI located at `~/code/WaddleAI`.

### When to Use WaddleAI

- Advanced natural language processing (NLP)
- Custom machine learning model inference
- AI-powered automation beyond chat responses
- Intelligent data analysis and recommendations

### Integration Pattern

- WaddleAI runs as separate microservice container
- Communicate via REST API or gRPC
- Environment variable configuration for API endpoints
- License-gate advanced AI features as enterprise functionality

### Environment Variables

```bash
# WaddleAI Integration
WADDLEAI_API_URL=http://waddleai:8080
WADDLEAI_API_KEY=your_api_key
WADDLEAI_TIMEOUT=30
```

---

## Version Management System

### Version Format

```
vMajor.Minor.Patch.build
```

**Components**:
- **Major**: Breaking changes, API changes, removed features
- **Minor**: Significant new features and functionality additions
- **Patch**: Minor updates, bug fixes, security patches
- **Build**: Epoch64 timestamp of build time

### Update Commands

```bash
# Increment build timestamp
./scripts/version/update-version.sh

# Increment patch version
./scripts/version/update-version.sh patch

# Increment minor version
./scripts/version/update-version.sh minor

# Increment major version
./scripts/version/update-version.sh major
```

### Semantic Versioning Rules

**Major Version (X.0.0)**:
- Breaking API changes
- Removed functionality
- Major architectural changes
- Incompatible with previous versions

**Minor Version (0.X.0)**:
- New features (backwards compatible)
- New functionality
- Deprecations (with warnings)
- Compatible with previous minor versions

**Patch Version (0.0.X)**:
- Bug fixes
- Security patches
- Performance improvements
- Documentation updates
- Fully backwards compatible

---

## Security Considerations

### Webhook Security

- **All webhooks must verify signatures** (HMAC-SHA256 for Twitch)
- Implement signature verification for all platform webhooks
- Use constant-time comparison for signature validation
- Log all webhook verification failures

**Example (Python)**:
```python
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
```

### OAuth Token Management

- OAuth tokens stored securely with automatic refresh
- Never log or expose OAuth tokens
- Use secure token storage (encrypted at rest)
- Implement automatic token refresh before expiration
- Revoke tokens on user logout or account deletion

### Credentials Management

- Database credentials in Kubernetes secrets
- No hardcoded credentials in code or configuration files
- Use environment variables for all secrets
- Rotate credentials regularly
- Use secret management systems (Vault, Kubernetes Secrets)

### Container Security

- Non-root containers with read-only filesystems
- Minimal base images (python:3.13-slim, alpine)
- No unnecessary packages or dependencies
- Security scanning with Trivy
- Regular base image updates

**Dockerfile Security**:
```dockerfile
# Use non-root user
RUN useradd -m -u 1000 waddlebot
USER waddlebot

# Read-only filesystem
VOLUME ["/tmp", "/var/log/waddlebotlog"]
```

### Rate Limiting

- Rate limiting on ingress
- Per-user, per-endpoint rate limits
- Implement sliding window rate limiting
- Return proper HTTP 429 responses
- Log rate limit violations

### Network Security

- HTTPS/TLS termination at ingress level
- Internal service-to-service communication over secure network
- Network policies for pod-to-pod communication
- Firewall rules for external access
- VPN for administrative access

### Database Security

- Use parameterized queries (prevent SQL injection)
- Implement proper access controls
- Enable database audit logging
- Encrypt data at rest and in transit
- Regular database backups with encryption

### API Security

- API Key authentication for all services
- Role-based access control (RBAC)
- Input validation and sanitization
- Output encoding to prevent XSS
- CORS configuration for web applications

### Monitoring and Alerting

- Comprehensive AAA logging (Authentication, Authorization, Auditing)
- Security event monitoring and alerting
- Failed authentication attempt tracking
- Suspicious activity detection
- Regular security audit reviews

---

## Compliance and Best Practices

### OWASP Top 10

Address all OWASP Top 10 security risks:
1. Broken Access Control
2. Cryptographic Failures
3. Injection
4. Insecure Design
5. Security Misconfiguration
6. Vulnerable and Outdated Components
7. Identification and Authentication Failures
8. Software and Data Integrity Failures
9. Security Logging and Monitoring Failures
10. Server-Side Request Forgery (SSRF)

### Security Headers

Implement security headers for web applications:
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'
Referrer-Policy: strict-origin-when-cross-origin
```

### Regular Security Reviews

- Quarterly security audits
- Penetration testing for major releases
- Code review focus on security
- Dependency vulnerability scanning
- Security training for all developers

---

## Conclusion

These development rules and standards are mandatory for all Waddles development. They ensure that we maintain a secure, stable, and high-quality codebase that can scale to support thousands of communities and millions of users.

**Remember**: Safe, stable, and feature-complete development is not optional - it's the foundation of Waddles's success.

For questions or clarifications on these rules, consult the project maintainers or refer to the comprehensive documentation in the `docs/` folder.

---

**Document Version**: 1.0.0
**Last Updated**: 2025-12-02
**Maintainer**: Waddles Development Team
**Company**: PenguinTech - www.penguintech.io
**License**: Limited AGPL3
