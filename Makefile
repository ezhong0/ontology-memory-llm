.PHONY: help install test lint format typecheck run clean docker-up docker-down db-migrate db-rollback db-reset seed check-all test-prod test-demo check-demo-isolation check-demo

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m  # No Color

help: ## Show this help message
	@echo "$(BLUE)Memory System - Development Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# Installation
install: ## Install dependencies with Poetry
	@echo "$(BLUE)Installing dependencies...$(NC)"
	poetry install
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

install-dev: ## Install with all dev dependencies
	@echo "$(BLUE)Installing all dependencies including dev...$(NC)"
	poetry install --with dev,docs
	@echo "$(GREEN)✓ All dependencies installed$(NC)"

# Docker Management
docker-up: ## Start PostgreSQL and Redis (development)
	@echo "$(BLUE)Starting infrastructure services...$(NC)"
	docker-compose up -d postgres
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 3
	@docker-compose ps

docker-up-all: ## Start all services including Phase 2 services
	@echo "$(BLUE)Starting all infrastructure services...$(NC)"
	docker-compose --profile phase2 up -d
	@echo "$(GREEN)✓ All services started$(NC)"

docker-down: ## Stop all infrastructure services
	@echo "$(BLUE)Stopping infrastructure services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

docker-clean: ## Stop and remove all containers and volumes (⚠️  destroys data)
	@echo "$(RED)WARNING: This will destroy all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		echo "$(GREEN)✓ Containers and volumes removed$(NC)"; \
	else \
		echo "Cancelled"; \
	fi

# Database Management
db-migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	poetry run alembic upgrade head
	@echo "$(GREEN)✓ Migrations complete$(NC)"

db-rollback: ## Rollback last migration
	@echo "$(YELLOW)Rolling back last migration...$(NC)"
	poetry run alembic downgrade -1
	@echo "$(GREEN)✓ Rollback complete$(NC)"

db-create-migration: ## Create new migration (use: make db-create-migration MSG="description")
	@if [ -z "$(MSG)" ]; then \
		echo "$(RED)Error: MSG variable required$(NC)"; \
		echo "Usage: make db-create-migration MSG='add new field'"; \
		exit 1; \
	fi
	@echo "$(BLUE)Creating migration: $(MSG)$(NC)"
	poetry run alembic revision --autogenerate -m "$(MSG)"
	@echo "$(GREEN)✓ Migration created - review before applying!$(NC)"

db-reset: docker-down docker-up db-migrate seed ## Reset database (⚠️  destroys data)
	@echo "$(GREEN)✓ Database reset complete$(NC)"

db-shell: ## Open psql shell to database
	@docker exec -it memory-system-postgres psql -U memoryuser -d memorydb

seed: ## Seed database with test data
	@echo "$(BLUE)Seeding database with test data...$(NC)"
	@if [ -f scripts/seed_data.py ]; then \
		poetry run python scripts/seed_data.py; \
		echo "$(GREEN)✓ Database seeded$(NC)"; \
	else \
		echo "$(YELLOW)⚠ seed_data.py not found - skipping$(NC)"; \
	fi

# Development Server
run: ## Start development server with auto-reload
	@echo "$(BLUE)Starting development server...$(NC)"
	@echo "API will be available at: http://localhost:8000"
	@echo "OpenAPI docs: http://localhost:8000/docs"
	poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

run-prod: ## Start production server (no reload)
	@echo "$(BLUE)Starting production server...$(NC)"
	poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4

# Testing
test: ## Run all tests
	@echo "$(BLUE)Running all tests...$(NC)"
	poetry run pytest -v

test-unit: ## Run unit tests only (fast)
	@echo "$(BLUE)Running unit tests...$(NC)"
	poetry run pytest -v -m unit

test-integration: ## Run integration tests (requires DB)
	@echo "$(BLUE)Running integration tests...$(NC)"
	docker-compose --profile test up -d postgres-test
	@sleep 2
	poetry run pytest -v -m integration
	docker-compose --profile test down

test-e2e: ## Run end-to-end tests
	@echo "$(BLUE)Running end-to-end tests...$(NC)"
	poetry run pytest -v -m e2e

test-watch: ## Run tests in watch mode (re-run on changes)
	@echo "$(BLUE)Starting test watcher...$(NC)"
	poetry run ptw -- -v

test-cov: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	poetry run pytest --cov=src --cov-report=term-missing --cov-report=html
	@echo "$(GREEN)✓ Coverage report generated$(NC)"
	@echo "Open htmlcov/index.html to view detailed report"

test-cov-min: ## Check if coverage meets minimum threshold (80%)
	@echo "$(BLUE)Checking coverage threshold...$(NC)"
	poetry run pytest --cov=src --cov-fail-under=80 -q

test-prod: ## Run production tests only (excludes demo tests)
	@echo "$(BLUE)Running production tests only...$(NC)"
	DEMO_MODE_ENABLED=false poetry run pytest tests/unit tests/integration --ignore=tests/demo -v
	@echo "$(GREEN)✓ Production tests passed$(NC)"

test-demo: ## Run demo tests only
	@echo "$(BLUE)Running demo tests only...$(NC)"
	DEMO_MODE_ENABLED=true poetry run pytest tests/demo -v
	@echo "$(GREEN)✓ Demo tests passed$(NC)"

# Code Quality
lint: ## Run linting checks
	@echo "$(BLUE)Running linting checks...$(NC)"
	poetry run ruff check src/ tests/
	@echo "$(GREEN)✓ Linting passed$(NC)"

lint-fix: ## Auto-fix linting issues where possible
	@echo "$(BLUE)Auto-fixing linting issues...$(NC)"
	poetry run ruff check --fix src/ tests/
	@echo "$(GREEN)✓ Linting fixes applied$(NC)"

format: ## Format code with Ruff
	@echo "$(BLUE)Formatting code...$(NC)"
	poetry run ruff format src/ tests/
	@echo "$(GREEN)✓ Code formatted$(NC)"

format-check: ## Check code formatting without changes
	@echo "$(BLUE)Checking code formatting...$(NC)"
	poetry run ruff format --check src/ tests/

typecheck: ## Run type checking with mypy
	@echo "$(BLUE)Running type checking...$(NC)"
	poetry run mypy src/
	@echo "$(GREEN)✓ Type checking passed$(NC)"

security: ## Run security checks
	@echo "$(BLUE)Running security checks...$(NC)"
	poetry run bandit -r src/
	poetry run pip-audit
	@echo "$(GREEN)✓ Security checks passed$(NC)"

check-demo-isolation: ## Verify demo code doesn't contaminate production
	@echo "$(BLUE)Checking demo isolation rules...$(NC)"
	@# Check for demo imports in production code
	@if grep -r "from src.demo" src/domain src/infrastructure src/api 2>/dev/null; then \
		echo "$(RED)✗ ERROR: Production code imports from demo!$(NC)"; \
		exit 1; \
	fi
	@# Check for demo files outside demo directory
	@if find src/domain src/infrastructure src/api -name "*demo*" -type f 2>/dev/null | grep -q .; then \
		echo "$(RED)✗ ERROR: Demo code found outside src/demo/$(NC)"; \
		exit 1; \
	fi
	@# Check domain models haven't been modified with demo fields
	@if grep -E "(is_demo|demo_data|scenario_id)" src/infrastructure/database/models.py 2>/dev/null; then \
		echo "$(YELLOW)⚠ WARNING: Possible demo contamination in production models$(NC)"; \
		echo "$(YELLOW)  Review src/infrastructure/database/models.py$(NC)"; \
	fi
	@echo "$(GREEN)✓ Demo isolation verified!$(NC)"

check-demo: check-demo-isolation test-prod test-demo ## Run all demo safety checks
	@echo "$(GREEN)✓ All demo safety checks passed!$(NC)"

check-all: lint typecheck test-cov-min ## Run all quality checks (CI/CD)
	@echo "$(GREEN)✓ All checks passed!$(NC)"

# Cleanup
clean: ## Remove generated files and caches
	@echo "$(BLUE)Cleaning generated files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

clean-all: clean docker-clean ## Remove all generated files and Docker volumes
	@echo "$(GREEN)✓ Deep cleanup complete$(NC)"

# Documentation
docs-serve: ## Serve documentation locally
	@echo "$(BLUE)Starting documentation server...$(NC)"
	@if [ -d docs ]; then \
		cd docs && poetry run mkdocs serve; \
	else \
		echo "$(YELLOW)⚠ docs/ directory not found$(NC)"; \
	fi

# Utility
check-env: ## Verify environment variables are set
	@echo "$(BLUE)Checking environment configuration...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)✗ .env file not found$(NC)"; \
		echo "  Run: cp .env.example .env"; \
		exit 1; \
	fi
	@echo "$(GREEN)✓ .env file exists$(NC)"
	@poetry run python -c "from src.config.settings import Settings; Settings()" 2>/dev/null && \
		echo "$(GREEN)✓ Environment variables valid$(NC)" || \
		echo "$(RED)✗ Environment validation failed$(NC)"

logs: ## View Docker logs
	@docker-compose logs -f

ps: ## Show running containers
	@docker-compose ps

shell: ## Start Python shell with project context
	@poetry run ipython

# CI/CD simulation
ci: install check-all ## Simulate CI/CD pipeline locally
	@echo "$(GREEN)✓ CI pipeline simulation complete!$(NC)"

# First-time setup
setup: install docker-up db-migrate seed check-env ## Complete first-time setup
	@echo ""
	@echo "$(GREEN)======================================$(NC)"
	@echo "$(GREEN)  Setup Complete! 🎉$(NC)"
	@echo "$(GREEN)======================================$(NC)"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Review .env file configuration"
	@echo "  2. Run: make run"
	@echo "  3. Visit: http://localhost:8000/docs"
	@echo ""

# Development cycle
dev: docker-up run ## Start development environment (Docker + API server)

# Show project stats
stats: ## Show project statistics
	@echo "$(BLUE)Project Statistics$(NC)"
	@echo ""
	@echo "Lines of code (src/):"
	@find src -name "*.py" | xargs wc -l | tail -1
	@echo ""
	@echo "Lines of tests (tests/):"
	@find tests -name "*.py" | xargs wc -l 2>/dev/null | tail -1 || echo "  0 (tests not yet created)"
	@echo ""
	@echo "Total Python files:"
	@find . -name "*.py" -not -path "./.venv/*" | wc -l
