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
	@bash scripts/lint.sh

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
	@bash scripts/security-scan.sh

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
