# Pre-Commit Checklist

**CRITICAL: This checklist MUST be followed before every commit.**

## Automated Pre-Commit Script

**Run the automated pre-commit script to execute all checks:**

```bash
./scripts/pre-commit/pre-commit.sh
```

This script will:
1. Run all checks in the correct order
2. Log output to `/tmp/pre-commit-<project>-<epoch>.log`
3. Provide a summary of pass/fail status
4. Echo the log file location for review

**Individual check scripts** (run separately if needed):
- `./scripts/pre-commit/check-python.sh` - Python linting & security
- `./scripts/pre-commit/check-go.sh` - Go linting & security
- `./scripts/pre-commit/check-node.sh` - Node.js/React linting, audit & build
- `./scripts/pre-commit/check-security.sh` - All security scans
- `./scripts/pre-commit/check-secrets.sh` - Secret detection
- `./scripts/pre-commit/check-docker.sh` - Docker build & validation
- `./scripts/pre-commit/check-tests.sh` - Unit tests

## Required Steps (In Order)

Before committing, run in this order (or use `./scripts/pre-commit/pre-commit.sh`):

- [ ] **Linters**: `npm run lint` or `golangci-lint run` or equivalent
- [ ] **Security scans**: `npm audit`, `gosec`, `bandit` (per language)
- [ ] **No secrets**: Verify no credentials, API keys, or tokens in code
- [ ] **Build & Run**: Verify code compiles and containers start successfully
- [ ] **Tests**: `npm test`, `go test ./...`, `pytest` (unit tests only)
- [ ] **Version updates**: Update `.version` if releasing new version
- [ ] **Documentation**: Update docs if adding/changing workflows
- [ ] **Docker builds**: Verify Dockerfile uses debian-slim base (no alpine)

## Language-Specific Commands

### Python
```bash
# Linting
flake8 .
black --check .
isort --check .
mypy .

# Security
bandit -r .
safety check

# Build & Run
python -m py_compile *.py          # Syntax check
pip install -r requirements.txt    # Dependencies
python app.py &                    # Verify it starts (then kill)

# Tests
pytest
```

### Go
```bash
# Linting
golangci-lint run

# Security
gosec ./...

# Build & Run
go build ./...                     # Compile all packages
go run main.go &                   # Verify it starts (then kill)

# Tests
go test ./...
```

### Node.js / JavaScript / TypeScript / ReactJS
```bash
# Linting
npm run lint
# or
npx eslint .

# Security (REQUIRED)
npm audit                          # Check for vulnerabilities
npm audit fix                      # Auto-fix if possible

# Build & Run
npm run build                      # Compile/bundle
npm start &                        # Verify it starts (then kill)
# For React: npm run dev or npm run preview

# Tests
npm test
```

### Docker / Containers
```bash
# Lint Dockerfiles
hadolint Dockerfile

# Verify base image (debian-slim, NOT alpine)
grep -E "^FROM.*slim" Dockerfile

# Build & Run
docker build -t myapp:test .                    # Build image
docker run -d --name test-container myapp:test  # Start container
docker logs test-container                      # Check for errors
docker stop test-container && docker rm test-container  # Cleanup

# Docker Compose (local dev only — see docker-compose.yml at repo root)
docker-compose build     # Build all services
docker-compose up -d     # Start all services
docker-compose logs      # Check for errors
docker-compose down      # Cleanup
```

## Commit Rules

- **NEVER commit automatically** unless explicitly requested by the user
- **NEVER push to remote repositories** under any circumstances
- **ONLY commit when explicitly asked** - never assume commit permission
- **Wait for approval** before running `git commit`

## Security Scanning Requirements

### Before Every Commit
- **Run security audits on all modified packages**:
  - **Go packages**: Run `gosec ./...` on modified Go services
  - **Node.js packages**: Run `npm audit` on modified Node.js services
  - **Python packages**: Run `bandit -r .` and `safety check` on modified Python services
- **Do NOT commit if security vulnerabilities are found** - fix all issues first
- **Document vulnerability fixes** in commit message if applicable

### Vulnerability Response
1. Identify affected packages and severity
2. Update to patched versions immediately
3. Test updated dependencies thoroughly
4. Document security fixes in commit messages
5. Verify no new vulnerabilities introduced

## API Testing Requirements

Before committing changes to container services:

- **Create and run API testing scripts** for each modified container service
- **Testing scope**: All new endpoints and modified functionality
- **Test files location**: `tests/api/` directory with service-specific subdirectories
  - `tests/api/flask-backend/` - Flask backend API tests
  - `tests/api/go-backend/` - Go backend API tests
  - `tests/api/webui/` - WebUI container tests
- **Run before commit**: Each test script should be executable and pass completely
- **Test coverage**: Health checks, authentication, CRUD operations, error cases

## Screenshot Requirements

For UI changes:

- **Run screenshot tool to update UI screenshots in documentation**
  - Run `cd services/webui && npm run screenshots` to capture current UI state
  - This automatically removes old screenshots and captures fresh ones
  - Commit updated screenshots with relevant feature/documentation changes
