# Waddles Contribution Guide

Welcome to the Waddles project! We're excited that you're interested in contributing. This guide will help you understand our contribution process, code standards, and best practices.

## Table of Contents

- [Getting Started](#getting-started)
- [Contribution Philosophy](#contribution-philosophy)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing Requirements](#testing-requirements)
- [Module Development](#module-development)
- [Documentation Standards](#documentation-standards)
- [Security Guidelines](#security-guidelines)
- [License and Legal](#license-and-legal)

## Getting Started

### Who Can Contribute?

Waddles is an open-source project under GPL-3.0 license. We welcome contributions from:

- Individual developers
- Community members
- Corporate contributors
- Students and researchers

### What Can You Contribute?

- **Bug fixes**: Fix issues and improve stability
- **New features**: Add functionality to existing modules
- **New modules**: Create entirely new interaction modules
- **Documentation**: Improve guides, tutorials, and API docs
- **Testing**: Add tests and improve coverage
- **Performance**: Optimize code and reduce resource usage
- **Security**: Identify and fix vulnerabilities

### Before You Start

1. **Read the Documentation**
   - [Architecture Guide](ARCHITECTURE.md)
   - [Development Standards](STANDARDS.md)
   - [API Reference](reference/api-reference.md)

2. **Set Up Your Environment**
   - Follow the [Quick Start Guide](QUICKSTART.md)
   - Set up development tools (see below)

3. **Check Existing Issues**
   - Browse [GitHub Issues](https://github.com/waddlebot/waddlebot/issues)
   - Look for issues tagged `good first issue` or `help wanted`
   - Comment on issues you'd like to work on

## Contribution Philosophy

### Safe, Stable, and Feature-Complete

**We prioritize quality over speed.** All contributions must:

- ✅ Be thoroughly tested
- ✅ Follow security best practices
- ✅ Include complete error handling
- ✅ Have comprehensive documentation
- ✅ Pass all CI/CD checks

### What We Don't Accept

- ❌ Quick fixes without proper testing
- ❌ Partial implementations with TODOs
- ❌ Code with hardcoded credentials
- ❌ Features that bypass security checks
- ❌ Changes that break existing functionality
- ❌ Code that fails linting or security scans

## Development Setup

### Local Development Environment

#### 1. Clone the Repository

```bash
git clone https://github.com/waddlebot/waddlebot.git
cd waddlebot
```

#### 2. Create Feature Branch

```bash
# Create branch from main
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# Branch naming convention:
# - feature/feature-name  (new features)
# - fix/bug-description   (bug fixes)
# - docs/documentation     (documentation)
# - refactor/description   (code refactoring)
```

#### 3. Install Development Tools

**Python Development:**

```bash
# Install Python 3.13
# See: https://www.python.org/downloads/

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

**Node.js Development (for frontend):**

```bash
# Install Node.js 18+
# See: https://nodejs.org/

# Install dependencies
cd admin/hub_module/frontend
npm install
```

**Linting and Quality Tools:**

```bash
# Python
pip install black flake8 isort mypy bandit pytest pytest-asyncio

# JavaScript/TypeScript
npm install -g eslint prettier

# Docker
# Install hadolint: https://github.com/hadolint/hadolint

# YAML
pip install yamllint

# Shell scripts
# Install shellcheck: https://github.com/koalaman/shellcheck
```

#### 4. Set Up Local Development Environment

```bash
# Create .env file
cp .env.example .env

# Edit with development configuration
# Use secure passwords for local development too!

# Start development stack
docker-compose up -d
```

### IDE Configuration

#### VS Code (Recommended)

Install recommended extensions:

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "ms-python.flake8",
    "ms-python.mypy-type-checker",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "redhat.vscode-yaml",
    "ms-azuretools.vscode-docker"
  ]
}
```

Configure settings (`.vscode/settings.json`):

```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.linting.mypyEnabled": true,
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "[javascript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

## Pull Request Process

### 1. Before Creating PR

**Run all quality checks:**

```bash
# Python linting
black .
isort .
flake8 .
mypy .
bandit -r .

# JavaScript linting (if applicable)
npm run lint
npm run format

# Security checks
pip-audit
npm audit

# Run tests
pytest
npm test

# Docker build test
docker build -t test-build .
```

### 2. Create Pull Request

**PR Title Format:**

```
<type>(<scope>): <subject>

Examples:
feat(loyalty): Add reputation-weighted giveaways
fix(router): Resolve race condition in command processing
docs(quickstart): Update Docker setup instructions
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Build/tooling changes
- `perf`: Performance improvements
- `security`: Security fixes

**PR Description Template:**

```markdown
## Description
Brief description of changes

## Motivation
Why is this change needed?

## Changes Made
- List of specific changes
- Affected modules
- Breaking changes (if any)

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed
- [ ] All tests pass locally

## Security
- [ ] No hardcoded credentials
- [ ] Input validation implemented
- [ ] Security scan passed
- [ ] No new vulnerabilities introduced

## Documentation
- [ ] Code comments added
- [ ] API documentation updated
- [ ] User-facing documentation updated
- [ ] CHANGELOG.md updated

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] No console.log or debug code
- [ ] Breaking changes documented
- [ ] Backward compatible (or migration guide provided)

## Screenshots (if applicable)
Add screenshots for UI changes

## Related Issues
Fixes #123
Relates to #456
```

### 3. Code Review Process

**What Reviewers Look For:**

1. **Code Quality**
   - Follows coding standards
   - Clean, readable code
   - Appropriate comments
   - No code smells

2. **Testing**
   - Adequate test coverage
   - Tests are meaningful
   - Edge cases covered
   - Tests pass in CI

3. **Security**
   - No vulnerabilities introduced
   - Proper input validation
   - Secure credential handling
   - OWASP compliance

4. **Documentation**
   - Code is documented
   - API changes documented
   - User guide updated
   - Clear commit messages

**Review Timeline:**

- **Initial Review**: Within 2-3 business days
- **Follow-up Reviews**: Within 1-2 business days
- **Merge Decision**: After approval from 2+ maintainers

### 4. Addressing Feedback

```bash
# Make requested changes
git add .
git commit -m "refactor: address review feedback"
git push origin feature/your-feature-name

# If major changes requested
git commit -m "fix: implement suggested changes

- Changed X to Y per review
- Added validation as requested
- Updated tests based on feedback"
```

### 5. Merge Requirements

**Before merge, PR must:**

- ✅ Have 2+ approvals from maintainers
- ✅ Pass all CI/CD checks
- ✅ Have no merge conflicts
- ✅ Be up-to-date with main branch
- ✅ Include updated CHANGELOG.md
- ✅ Have passing security scans

## Code Style Guidelines

### Python Code Style

**Follow PEP 8 with these specific rules:**

```python
# Use black formatter (line length: 88)
# Use isort for import sorting

# Example module structure
"""
Module docstring describing purpose.

This module implements X functionality for Y.
"""

import os
import sys
from typing import Dict, List, Optional

from flask import Flask, request
from flask_core.auth import require_api_key
from flask_core.logging import get_logger

logger = get_logger(__name__)


class MyClass:
    """Class docstring with clear description."""

    def __init__(self, config: Dict[str, str]):
        """Initialize with configuration.

        Args:
            config: Configuration dictionary
        """
        self.config = config

    async def process(self, data: Dict) -> Optional[Dict]:
        """Process data and return results.

        Args:
            data: Input data dictionary

        Returns:
            Processed results or None on failure

        Raises:
            ValueError: If data is invalid
        """
        if not self._validate(data):
            raise ValueError("Invalid data format")

        try:
            result = await self._do_processing(data)
            logger.info(f"Processing completed: {result}")
            return result
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return None

    def _validate(self, data: Dict) -> bool:
        """Private method for validation."""
        return bool(data)


# Module-level functions
async def helper_function(param: str) -> str:
    """Helper function with clear purpose."""
    return param.upper()
```

**Type Hints:**

```python
# Always use type hints
from typing import Dict, List, Optional, Union, Any

def process_user(user_id: str, data: Dict[str, Any]) -> Optional[Dict]:
    """Type hints make code self-documenting."""
    pass
```

### JavaScript/TypeScript Code Style

```javascript
// Use Prettier formatting
// Use ESLint for quality

// Example component
import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';

/**
 * Component for displaying user profile
 * @param {Object} props - Component props
 * @param {string} props.userId - User ID to display
 * @returns {JSX.Element} Profile component
 */
const UserProfile = ({ userId }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await fetch(`/api/users/${userId}`);
        const data = await response.json();
        setUser(data);
      } catch (error) {
        console.error('Failed to fetch user:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, [userId]);

  if (loading) return <div>Loading...</div>;
  if (!user) return <div>User not found</div>;

  return (
    <div className="user-profile">
      <h2>{user.name}</h2>
      <p>{user.email}</p>
    </div>
  );
};

UserProfile.propTypes = {
  userId: PropTypes.string.isRequired,
};

export default UserProfile;
```

### Docker Best Practices

```dockerfile
# Use specific versions
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install dependencies first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Testing Requirements

### Test Coverage Requirements

**Minimum Coverage:**
- Unit tests: 80%+ coverage
- Integration tests: Key workflows covered
- E2E tests: Critical user paths tested

### Writing Unit Tests

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Test file: test_{module_name}.py

@pytest.mark.asyncio
async def test_process_command_success():
    """Test successful command processing."""
    # Arrange
    mock_db = AsyncMock()
    processor = CommandProcessor(mock_db)
    command = {"user_id": "discord:123", "command": "!hello"}

    # Act
    result = await processor.process(command)

    # Assert
    assert result["success"] is True
    assert "message" in result
    mock_db.save.assert_called_once()


@pytest.mark.asyncio
async def test_process_command_invalid_input():
    """Test command processing with invalid input."""
    processor = CommandProcessor(AsyncMock())

    with pytest.raises(ValueError):
        await processor.process({"invalid": "data"})


@pytest.fixture
async def test_db():
    """Fixture for test database."""
    db = await create_test_database()
    yield db
    await db.cleanup()
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_router.py

# Run specific test
pytest tests/test_router.py::test_process_command_success

# Run with verbose output
pytest -v

# Run integration tests only
pytest -m integration

# Run unit tests only
pytest -m unit
```

## Module Development

### Creating a New Module

See [Development Standards](STANDARDS.md) for detailed module development guidelines.

**Basic Module Structure:**

```
your_module/
├── Dockerfile
├── requirements.txt
├── main.py
├── config.py
├── models.py
├── handlers/
│   ├── __init__.py
│   └── commands.py
├── services/
│   ├── __init__.py
│   └── business_logic.py
├── tests/
│   ├── test_handlers.py
│   └── test_services.py
└── README.md
```

**Module Checklist:**

- [ ] Health check endpoint (`/health`)
- [ ] Metrics endpoint (`/metrics`)
- [ ] API authentication
- [ ] Input validation
- [ ] Error handling
- [ ] Logging (AAA format)
- [ ] Unit tests (80%+ coverage)
- [ ] Integration tests
- [ ] Documentation
- [ ] Docker build succeeds

## Documentation Standards

### Code Documentation

```python
def process_payment(
    user_id: str,
    amount: int,
    currency: str = "USD"
) -> Dict[str, Any]:
    """Process payment for user.

    This function validates the payment, checks user balance,
    and processes the transaction through the payment gateway.

    Args:
        user_id: Unique user identifier in format 'platform:id'
        amount: Payment amount in smallest currency unit (cents)
        currency: ISO 4217 currency code, defaults to USD

    Returns:
        Dictionary containing transaction details:
        {
            "transaction_id": str,
            "status": "success" | "failed",
            "amount": int,
            "currency": str,
            "timestamp": str
        }

    Raises:
        ValueError: If user_id format is invalid
        InsufficientFundsError: If user balance is too low
        PaymentGatewayError: If payment processing fails

    Example:
        >>> result = process_payment("discord:123", 1000, "USD")
        >>> print(result["status"])
        'success'
    """
    pass
```

### API Documentation

Document all API endpoints:

```python
"""
POST /api/v1/loyalty/transfer
---
summary: Transfer loyalty points between users
tags:
  - Loyalty
parameters:
  - name: X-API-Key
    in: header
    required: true
    schema:
      type: string
requestBody:
  required: true
  content:
    application/json:
      schema:
        type: object
        properties:
          from_user_id:
            type: string
            example: "discord:123"
          to_user_id:
            type: string
            example: "twitch:456"
          amount:
            type: integer
            minimum: 1
            example: 100
responses:
  200:
    description: Transfer successful
    content:
      application/json:
        schema:
          type: object
          properties:
            success:
              type: boolean
            transaction_id:
              type: string
  400:
    description: Invalid input
  401:
    description: Unauthorized
"""
```

## Security Guidelines

### Input Validation

```python
from flask_core.validation import validate_input, ValidationError

@app.route('/api/v1/command', methods=['POST'])
async def execute_command():
    try:
        data = await validate_input(
            await request.json(),
            {
                'user_id': {
                    'type': 'string',
                    'required': True,
                    'pattern': r'^[a-z]+:\d+$'
                },
                'command': {
                    'type': 'string',
                    'required': True,
                    'max_length': 255,
                    'min_length': 1
                },
                'args': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'max_items': 10
                }
            }
        )
    except ValidationError as e:
        return error_response(400, str(e))

    return await process_command(data)
```

### Credential Management

**Never commit secrets:**

```python
# ✅ CORRECT
DB_PASSWORD = os.getenv('DB_PASSWORD')
API_KEY = os.getenv('API_KEY')

# ❌ WRONG - Never do this!
DB_PASSWORD = 'hardcoded_password'
API_KEY = 'sk-abc123def456'
```

**Use .env files for local development:**

```bash
# .env (add to .gitignore!)
DB_PASSWORD=local_dev_password
API_KEY=dev_api_key_12345
```

### Security Checklist

Before submitting PR:

- [ ] No hardcoded credentials
- [ ] All inputs validated
- [ ] SQL injection prevented (parameterized queries)
- [ ] XSS prevention (output encoding)
- [ ] CSRF protection enabled
- [ ] Authentication required on sensitive endpoints
- [ ] Authorization checks implemented
- [ ] Secrets in environment variables
- [ ] Security scan passed (`bandit`, `npm audit`)
- [ ] Dependencies have no known vulnerabilities

## License and Legal

### License Agreement

By contributing to Waddles, you agree that:

1. Your contributions will be licensed under GPL-3.0
2. You have the right to submit the contribution
3. You understand the license terms
4. Your employer (if applicable) has approved the contribution

### Contributor Employer Exception

Companies employing contributors receive perpetual GPL-2.0 access to versions their employees contributed to. See [LICENSE.md](LICENSE.md) for details.

### Signing Commits

We require signed commits for security:

```bash
# Configure GPG signing
git config --global user.signingkey YOUR_GPG_KEY
git config --global commit.gpgsign true

# Sign commits
git commit -S -m "feat: add new feature"
```

## Getting Help

### Resources

- **Documentation**: Browse `/docs` directory
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Standards**: [STANDARDS.md](STANDARDS.md)
- **GitHub Issues**: Ask questions with `question` label

### Community

- **GitHub Discussions**: For general questions
- **Discord**: Coming soon
- **Email**: support@waddlebot.com

### Reporting Bugs

Use this template:

```markdown
**Describe the bug**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
What you expected to happen

**Screenshots**
If applicable

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Docker version: [e.g., 20.10.21]
- Waddles version: [e.g., 0.2.0]

**Additional context**
Any other relevant information
```

---

**Thank you for contributing to Waddles!** Your contributions help make Waddles better for everyone in the community.
