# TerraChatBi Project Makefile
# Supports both backend and frontend operations

# Default environment
ENV ?= development
DOCKER_COMPOSE ?= docker compose

# Directories
BACKEND_DIR := backend
FRONTEND_DIR := frontend

# =============================================================================
# Backend Commands
# =============================================================================

backend-install:
	@echo "Installing backend dependencies..."
	@cd $(BACKEND_DIR) && pip install uv && uv sync

backend-set-env:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make backend-set-env ENV=development|staging|production"; \
		exit 1; \
	fi
	@echo "Setting backend environment to $(ENV)"
	@cd $(BACKEND_DIR) && bash -c "source scripts/set_env.sh $(ENV)"

backend-prod:
	@echo "Starting backend server in production environment"
	@cd $(BACKEND_DIR) && bash -c "source scripts/set_env.sh production && ./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop uvloop"

backend-staging:
	@echo "Starting backend server in staging environment"
	@cd $(BACKEND_DIR) && bash -c "source scripts/set_env.sh staging && ./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop uvloop"

backend-dev:
	@echo "Starting backend server in development environment"
	@cd $(BACKEND_DIR) && bash -c "source scripts/set_env.sh development && uv run uvicorn app.main:app --reload --port 8000 --loop uvloop"

backend-eval:
	@echo "Running evaluation with interactive mode"
	@cd $(BACKEND_DIR) && bash -c "source scripts/set_env.sh ${ENV:-development} && python -m evals.main --interactive"

backend-eval-quick:
	@echo "Running evaluation with default settings"
	@cd $(BACKEND_DIR) && bash -c "source scripts/set_env.sh ${ENV:-development} && python -m evals.main --quick"

backend-eval-no-report:
	@echo "Running evaluation without generating report"
	@cd $(BACKEND_DIR) && bash -c "source scripts/set_env.sh ${ENV:-development} && python -m evals.main --no-report"

backend-lint:
	@echo "Running backend linting..."
	@cd $(BACKEND_DIR) && ruff check .

backend-format:
	@echo "Running backend formatting..."
	@cd $(BACKEND_DIR) && ruff format .

backend-clean:
	@echo "Cleaning backend..."
	@cd $(BACKEND_DIR) && rm -rf .venv __pycache__ .pytest_cache

# Backend Docker commands
backend-docker-build:
	@cd $(BACKEND_DIR) && docker build -t fastapi-langgraph-template .

backend-docker-build-env:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make backend-docker-build-env ENV=development|staging|production"; \
		exit 1; \
	fi
	@cd $(BACKEND_DIR) && ./scripts/build-docker.sh $(ENV)

backend-docker-run:
	@cd $(BACKEND_DIR) && ./scripts/run-docker.sh development

backend-docker-run-env:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make backend-docker-run-env ENV=development|staging|production"; \
		exit 1; \
	fi
	@cd $(BACKEND_DIR) && ./scripts/run-docker.sh $(ENV)

backend-docker-logs:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make backend-docker-logs ENV=development|staging|production"; \
		exit 1; \
	fi
	@cd $(BACKEND_DIR) && ./scripts/logs-docker.sh $(ENV)

backend-docker-stop:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make backend-docker-stop ENV=development|staging|production"; \
		exit 1; \
	fi
	@cd $(BACKEND_DIR) && ./scripts/stop-docker.sh $(ENV)

backend-docker-up:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make backend-docker-up ENV=development|staging|production"; \
		exit 1; \
	fi
	@cd $(BACKEND_DIR) && APP_ENV=$(ENV) $(DOCKER_COMPOSE) up -d

backend-docker-down:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make backend-docker-down ENV=development|staging|production"; \
		exit 1; \
	fi
	@cd $(BACKEND_DIR) && APP_ENV=$(ENV) $(DOCKER_COMPOSE) down

# Backend monitoring stack
backend-monitoring-up:
	@cd $(BACKEND_DIR) && $(DOCKER_COMPOSE) -f docker-compose.monitoring.yml up -d

backend-monitoring-down:
	@cd $(BACKEND_DIR) && $(DOCKER_COMPOSE) -f docker-compose.monitoring.yml down

# =============================================================================
# Frontend Commands
# =============================================================================

frontend-install:
	@echo "Installing frontend dependencies..."
	@cd $(FRONTEND_DIR) && npm install

frontend-dev:
	@echo "Starting frontend development server..."
	@cd $(FRONTEND_DIR) && npm run dev

frontend-build:
	@echo "Building frontend..."
	@cd $(FRONTEND_DIR) && npm run build

frontend-lint:
	@echo "Running frontend linting..."
	@cd $(FRONTEND_DIR) && npm run lint

frontend-docker-build:
	@cd $(FRONTEND_DIR) && docker build -t terrachatbi-frontend .

frontend-docker-up:
	@cd $(FRONTEND_DIR) && $(DOCKER_COMPOSE) up -d

frontend-docker-down:
	@cd $(FRONTEND_DIR) && $(DOCKER_COMPOSE) down

# =============================================================================
# Full Stack Commands
# =============================================================================

install: backend-install frontend-install
	@echo "All dependencies installed"

dev:
	@echo "Starting full stack in development mode..."
	@make backend-docker-up ENV=development &
	@sleep 5
	@make frontend-docker-up

stop:
	@make backend-docker-down ENV=development
	@make frontend-docker-down

# =============================================================================
# Legacy Commands (Backward Compatibility)
# =============================================================================

set-env: backend-set-env
prod: backend-prod
staging: backend-staging
dev-local: backend-dev
eval: backend-eval
eval-quick: backend-eval-quick
eval-no-report: backend-eval-no-report
lint: backend-lint
format: backend-format
clean: backend-clean

# Help
help:
	@echo "TerraChatBi Project Management"
	@echo ""
	@echo "Backend Commands:"
	@echo "  backend-install              - Install backend dependencies"
	@echo "  backend-set-env ENV=xxx      - Set backend environment"
	@echo "  backend-dev                  - Run backend in development mode"
	@echo "  backend-staging              - Run backend in staging mode"
	@echo "  backend-prod                 - Run backend in production mode"
	@echo "  backend-docker-up ENV=xxx    - Start backend with Docker"
	@echo "  backend-docker-down ENV=xxx  - Stop backend Docker services"
	@echo "  backend-monitoring-up        - Start monitoring stack (Prometheus, Grafana)"
	@echo "  backend-monitoring-down      - Stop monitoring stack"
	@echo ""
	@echo "Frontend Commands:"
	@echo "  frontend-install             - Install frontend dependencies"
	@echo "  frontend-dev                 - Run frontend development server"
	@echo "  frontend-build               - Build frontend for production"
	@echo "  frontend-docker-up           - Start frontend with Docker"
	@echo "  frontend-docker-down         - Stop frontend Docker service"
	@echo ""
	@echo "Full Stack Commands:"
	@echo "  install                      - Install all dependencies"
	@echo "  dev                          - Start full stack with Docker"
	@echo "  stop                         - Stop all Docker services"
	@echo ""
	@echo "For more control, use ./manager.sh script"