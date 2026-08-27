.PHONY: dev test test-unit test-integration test-e2e test-functional test-security \
        smoke-test lint build docker-build docker-push deploy-dev deploy-prod \
        seed-mock-data clean pre-commit run-ai-local

dev:
	docker-compose up

build:
	docker-compose build

docker-build: build

docker-push:
	$(error docker-push is CI-only — beta/prod images built by GitHub Actions from release branches)

lint:
	@echo "=== Linting ==="
	@if command -v flake8 >/dev/null 2>&1; then echo "-- flake8 --"; python3 -m flake8 . --max-line-length=120 --exclude=.git,__pycache__,venv,node_modules || true; fi
	@if command -v black >/dev/null 2>&1; then echo "-- black --"; black --check . --exclude '/(\.git|venv|__pycache__|node_modules)/' || true; fi
	@if command -v isort >/dev/null 2>&1; then echo "-- isort --"; isort --check-only . || true; fi
	@if command -v mypy >/dev/null 2>&1; then echo "-- mypy --"; python3 -m mypy . --ignore-missing-imports || true; fi
	@if command -v golangci-lint >/dev/null 2>&1; then echo "-- golangci-lint --"; find . -name "go.mod" -not -path "*/.git/*" -not -path "*/vendor/*" | xargs -I{} dirname {} | xargs -I{} sh -c 'cd {} && golangci-lint run || true'; fi
	@if command -v hadolint >/dev/null 2>&1; then echo "-- hadolint --"; find . -name "Dockerfile*" -not -path "*/.git/*" | xargs hadolint || true; fi
	@if command -v shellcheck >/dev/null 2>&1; then echo "-- shellcheck --"; find . -name "*.sh" -not -path "*/.git/*" | xargs shellcheck || true; fi

test:
	@$(MAKE) test-unit

test-unit:
	@echo "Running unit tests..."
	@bash tests/k8s/alpha/05-unit-tests.sh

test-integration:
	@echo "Running integration tests..."
	@[ -d tests/integration ] || $(error tests/integration directory not found)
	@bash scripts/test-api-all.sh

test-e2e:
	@echo "Running e2e tests..."
	@[ -f scripts/e2e-test-alpha.sh ] || $(error scripts/e2e-test-alpha.sh not found)
	@bash scripts/e2e-test-alpha.sh

test-functional:
	$(error test-functional is not yet implemented — add pytest tests/functional/ -v after creating tests/functional directory)

test-security:
	@echo "=== Security Scans ==="
	@if command -v bandit >/dev/null 2>&1; then echo "-- bandit --"; bandit -r . -x ./tests,./venv,./.git --quiet || true; fi
	@if command -v pip-audit >/dev/null 2>&1; then echo "-- pip-audit --"; find . -name "requirements.txt" -not -path "*/.git/*" -not -path "*/venv/*" | xargs -I{} pip-audit -r {} 2>/dev/null || true; fi
	@if command -v gosec >/dev/null 2>&1; then echo "-- gosec --"; find . -name "go.mod" -not -path "*/.git/*" -not -path "*/vendor/*" | xargs -I{} dirname {} | xargs -I{} sh -c 'cd {} && gosec ./... || true'; fi
	@if command -v govulncheck >/dev/null 2>&1; then echo "-- govulncheck --"; find . -name "go.mod" -not -path "*/.git/*" -not -path "*/vendor/*" | xargs -I{} dirname {} | xargs -I{} sh -c 'cd {} && govulncheck ./... || true'; fi
	@find . -name "package.json" -not -path "*/.git/*" -not -path "*/node_modules/*" -maxdepth 3 | xargs -I{} dirname {} | xargs -I{} sh -c 'cd {} && npm audit 2>/dev/null || true'
	@if command -v gitleaks >/dev/null 2>&1; then echo "-- gitleaks --"; gitleaks detect --source . --no-git 2>/dev/null || true; fi

smoke-test:
	@echo "Running smoke tests..."
	@[ -f tests/alpha-smoke-test.sh ] || $(error tests/alpha-smoke-test.sh not found)
	@bash tests/alpha-smoke-test.sh

seed-mock-data:
	@echo "Seeding mock data..."
	@[ -f scripts/seed-admin.sh ] || $(error scripts/seed-admin.sh not found)
	@bash scripts/seed-admin.sh

clean:
	docker-compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

deploy-dev:
	@echo "Deploy to dev/alpha environment..."
	@[ -f scripts/deploy-alpha.sh ] || $(error scripts/deploy-alpha.sh not found)
	@bash scripts/deploy-alpha.sh

deploy-prod:
	$(error deploy-prod requires CI — tag a release to trigger the production pipeline)

run-ai-local: ## Run ai_interaction_module container locally (standalone, 1 worker)
	docker build -f action/interactive/ai_interaction_module/Dockerfile -t waddlebot/ai-interaction:local . && \
	docker run --rm \
	  --name ai-interaction-local \
	  --add-host=host.docker.internal:host-gateway \
	  --env-file action/interactive/ai_interaction_module/.env.local \
	  -e HYPERCORN_WORKERS=1 \
	  -p 8005:8005 \
	  waddlebot/ai-interaction:local

pre-commit:
	@echo "=== Pre-commit checks ==="
	@$(MAKE) lint
	@$(MAKE) test-security
	@$(MAKE) test
	@echo "=== Pre-commit complete ==="
