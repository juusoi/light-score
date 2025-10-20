PYTHON?=.venv/bin/python
DOCKER?=podman
PROJECT_NAME=light-score

# Color codes for output
GREEN=\033[0;32m
YELLOW=\033[1;33m
BLUE=\033[0;34m
RED=\033[0;31m
NC=\033[0m # No Color

# Default target
.DEFAULT_GOAL := help

.PHONY: venv sync deps lint fmt ty test ci build-images up down logs clean clean-containers clean-images clean-all clean-project prune help check-deps status restart dev-setup health security lint-e2e fmt-e2e ty-e2e test-e2e ci-e2e

venv:
	@echo "$(BLUE)🏗️  Creating virtual environment...$(NC)"
	@uv venv
	@echo "$(GREEN)✅ Virtual environment created successfully!$(NC)"
	@echo "$(YELLOW)💡 Activate with: source .venv/bin/activate$(NC)"

sync:
	@echo "$(BLUE)🔄 Syncing all dependencies...$(NC)"
	@./scripts/uv-sync.sh --all
	@echo "$(GREEN)✅ Dependencies synced successfully!$(NC)"

deps:
	@echo "$(BLUE)📦 Installing dependencies...$(NC)"
	@./scripts/install-deps.sh
	@echo "$(GREEN)✅ Dependencies installed successfully!$(NC)"

lint:
	@echo "$(BLUE)🔍 Running linter (ruff check)...$(NC)"
	@if [ ! -f "$(PYTHON)" ]; then \
		echo "$(RED)❌ Python environment not found at $(PYTHON)$(NC)"; \
		echo "$(YELLOW)💡 Run 'make dev-setup' first$(NC)"; \
		exit 1; \
	fi
	@$(PYTHON) -m ruff check . && echo "$(GREEN)✅ Linting passed!$(NC)" || (echo "$(RED)❌ Linting failed!$(NC)" && exit 1)

fmt:
	@echo "$(BLUE)🎨 Formatting code (ruff format)...$(NC)"
	@$(PYTHON) -m ruff format .
	@echo "$(GREEN)✅ Code formatted successfully!$(NC)"

ty:
	@echo "$(BLUE)🔎 Running type checking...$(NC)"
	@$(PYTHON) -m ty check . || echo "$(YELLOW)⚠️  Type checking completed with warnings$(NC)"

test:
	@echo "$(BLUE)🧪 Running all tests...$(NC)"
	@./scripts/run-tests.sh && echo "$(GREEN)✅ All tests passed!$(NC)" || (echo "$(RED)❌ Tests failed!$(NC)" && exit 1)

ci: lint ty test

# --- E2E Test Quality ---
lint-e2e:
	@echo "$(BLUE)🔍 Running E2E linting (ESLint)...$(NC)"
	@if [ ! -d "e2e/node_modules" ]; then \
		echo "$(YELLOW)📦 Installing E2E dependencies...$(NC)"; \
		cd e2e && bun install; \
	fi
	@cd e2e && bun run lint && echo "$(GREEN)✅ E2E linting passed!$(NC)" || (echo "$(RED)❌ E2E linting failed!$(NC)" && exit 1)

fmt-e2e:
	@echo "$(BLUE)🎨 Formatting E2E code (Prettier)...$(NC)"
	@if [ ! -d "e2e/node_modules" ]; then \
		echo "$(YELLOW)📦 Installing E2E dependencies...$(NC)"; \
		cd e2e && bun install; \
	fi
	@cd e2e && bun run fmt
	@echo "$(GREEN)✅ E2E code formatted successfully!$(NC)"

ty-e2e:
	@echo "$(BLUE)🔎 Running E2E type checking...$(NC)"
	@if [ ! -d "e2e/node_modules" ]; then \
		echo "$(YELLOW)📦 Installing E2E dependencies...$(NC)"; \
		cd e2e && bun install; \
	fi
	@cd e2e && bun run type-check && echo "$(GREEN)✅ E2E type checking passed!$(NC)" || (echo "$(YELLOW)⚠️  E2E type checking completed with warnings$(NC)" && exit 1)

test-e2e:
	@echo "$(BLUE)🧪 Running E2E tests...$(NC)"
	@if [ ! -d "e2e/node_modules" ]; then \
		echo "$(YELLOW)📦 Installing E2E dependencies...$(NC)"; \
		cd e2e && bun install; \
	fi
	@cd e2e && bun run test:ci && echo "$(GREEN)✅ E2E tests passed!$(NC)" || (echo "$(RED)❌ E2E tests failed!$(NC)" && exit 1)

ci-e2e: lint-e2e ty-e2e test-e2e

security:
	@echo "$(BLUE)🔒 Running security checks...$(NC)"
	@if [ ! -f "$(PYTHON)" ]; then \
		echo "$(RED)❌ Python environment not found at $(PYTHON)$(NC)"; \
		echo "$(YELLOW)💡 Run 'make dev-setup' first$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)🔍 Running Bandit security scan...$(NC)"
	@$(PYTHON) -m bandit -r backend/src -x "backend/src/utest" -q && \
	 $(PYTHON) -m bandit -r frontend/src -x "frontend/src/utest" -q && \
	 $(PYTHON) -m bandit -r functions/src -x "functions/src/utest" -q && \
	 echo "$(GREEN)✅ Bandit scan passed!$(NC)" || (echo "$(YELLOW)⚠️  Bandit found security issues$(NC)" && exit 1)
	@echo "$(BLUE)🔍 Running pip-audit dependency scan...$(NC)"
	@# Ignore GHSA-4xh5-x5gv-qwph: pip tarfile vulnerability fixed in upcoming pip 25.3
	@$(PYTHON) -m pip_audit --desc --ignore-vuln GHSA-4xh5-x5gv-qwph && echo "$(GREEN)✅ Dependency audit passed!$(NC)" || (echo "$(YELLOW)⚠️  Found vulnerable dependencies$(NC)" && exit 1)
	@echo "$(GREEN)✅ Security checks completed!$(NC)"


dev-setup: venv sync
	@echo "$(BLUE)🔒 Installing security tools...$(NC)"
	@uv pip install bandit[toml]>=1.8.0 pip-audit>=2.7.0
	@echo "$(GREEN)🎉 Development environment setup complete!$(NC)"
	@echo "$(YELLOW)💡 Next steps:$(NC)"
	@echo "  • Run containers: $(GREEN)make up$(NC)"
	@echo "  • Run containers: $(GREEN)make up$(NC)"
	@echo "  • Run CI checks: $(GREEN)make ci$(NC)"
	@echo "  • Run security checks: $(GREEN)make security$(NC)"

# --- Containers (Docker/Podman) ---
build-images:
	@echo "$(BLUE)🏗️  Building $(PROJECT_NAME) images with $(DOCKER)...$(NC)"
	@DOCKER=$(DOCKER) ./scripts/compose.sh build
	@echo "$(GREEN)✅ Images built successfully!$(NC)"

up:
	@echo "$(BLUE)🚀 Starting $(PROJECT_NAME) services with $(DOCKER)...$(NC)"
	@DOCKER=$(DOCKER) ./scripts/compose.sh up -d
	@echo "$(GREEN)✅ Services started successfully!$(NC)"
	@echo "$(YELLOW)💡 Backend: http://localhost:8000$(NC)"
	@echo "$(YELLOW)💡 Frontend: http://localhost:5000$(NC)"
	@echo "$(YELLOW)💡 View logs: make logs$(NC)"

down:
	@echo "$(BLUE)🛑 Stopping $(PROJECT_NAME) services...$(NC)"
	@DOCKER=$(DOCKER) ./scripts/compose.sh down -v --remove-orphans
	@echo "$(GREEN)✅ Services stopped successfully!$(NC)"

logs:
	@echo "$(BLUE)📋 Showing container logs (Ctrl+C to exit)...$(NC)"
	@DOCKER=$(DOCKER) ./scripts/compose.sh logs -f --tail=100

status:
	@echo "$(BLUE)📊 Container Status:$(NC)"
	@$(DOCKER) ps --filter "name=$(PROJECT_NAME)" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "$(BLUE)📊 Image Information:$(NC)"
	@$(DOCKER) images --filter "reference=localhost/$(PROJECT_NAME)*" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}"

restart: down up

check-deps:
	@echo "$(BLUE)🔍 Checking dependency consistency...$(NC)"
	@./scripts/check-deps.sh

health:
	@echo "$(BLUE)🏥 Checking application health...$(NC)"
	@echo "Backend health:"
	@curl -s -f http://localhost:8000/ > /dev/null && echo "$(GREEN)  ✅ Backend is healthy$(NC)" || echo "$(RED)  ❌ Backend is unhealthy$(NC)"
	@echo "Frontend health:"
	@curl -s -f http://localhost:5000/ > /dev/null && echo "$(GREEN)  ✅ Frontend is healthy$(NC)" || echo "$(RED)  ❌ Frontend is unhealthy$(NC)"

# --- Container Cleanup ---
clean: clean-containers
	@echo "$(BLUE)🧹 Basic cleanup: stopped containers and dangling images$(NC)"

clean-containers:
	@echo "$(BLUE)🗑️  Removing stopped containers...$(NC)"
	@$(DOCKER) container prune -f
	@echo "$(GREEN)✅ Stopped containers removed!$(NC)"

clean-images:
	@echo "$(BLUE)🗑️  Removing dangling images...$(NC)"
	@$(DOCKER) image prune -f
	@echo "$(GREEN)✅ Dangling images removed!$(NC)"

clean-all: down
	@echo "$(YELLOW)⚠️  Deep cleanup: containers, images, volumes, networks...$(NC)"
	@$(DOCKER) container prune -f
	@$(DOCKER) image prune -a -f
	@$(DOCKER) volume prune -f
	@$(DOCKER) network prune -f
	@echo "$(GREEN)✅ Deep cleanup complete!$(NC)"

prune: 
	@echo "$(RED)⚠️  Nuclear cleanup: removing ALL unused Docker objects...$(NC)"
	@read -p "Are you sure? This will remove ALL unused Docker objects (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@$(DOCKER) system prune -a -f --volumes
	@echo "$(GREEN)💥 Nuclear cleanup complete!$(NC)"

# Remove project-specific images and containers
clean-project:
	@echo "$(BLUE)🎯 Cleaning $(PROJECT_NAME) project containers and images...$(NC)"
	@$(DOCKER) ps -a --filter "name=$(PROJECT_NAME)" --format "{{.ID}}" | xargs -r $(DOCKER) rm -f 2>/dev/null || true
	@$(DOCKER) images --filter "reference=localhost/$(PROJECT_NAME)*" --format "{{.ID}}" | xargs -r $(DOCKER) rmi -f 2>/dev/null || true
	@echo "$(GREEN)✅ Project cleanup complete!$(NC)"

# --- Help ---
help:
	@echo "$(GREEN)🚀 Light Score - Available Commands:$(NC)"
	@echo ""
	@echo "$(BLUE)📦 Development:$(NC)"
	@echo "  $(YELLOW)venv$(NC)          Create virtual environment"
	@echo "  $(YELLOW)sync$(NC)          Sync all dependencies"
	@echo "  $(YELLOW)deps$(NC)          Install dependencies"
	@echo "  $(YELLOW)dev-setup$(NC)     Complete development environment setup (venv + sync)"
	@echo "  $(YELLOW)start$(NC)         Start local development servers"
	@echo ""
	@echo "$(BLUE)🔍 Code Quality (Python):$(NC)"
	@echo "  $(YELLOW)lint$(NC)          Run linting (ruff check)"
	@echo "  $(YELLOW)fmt$(NC)           Format code (ruff format)"
	@echo "  $(YELLOW)ty$(NC)            Run type checking"
	@echo "  $(YELLOW)test$(NC)          Run all tests"
	@echo "  $(YELLOW)security$(NC)      Run security checks (bandit + pip-audit)"
	@echo ""
	@echo "$(BLUE)🎭 E2E Tests (TypeScript):$(NC)"
	@echo "  $(YELLOW)lint-e2e$(NC)      Run E2E linting (ESLint)"
	@echo "  $(YELLOW)fmt-e2e$(NC)       Format E2E code (Prettier)"
	@echo "  $(YELLOW)ty-e2e$(NC)        Run E2E type checking (TypeScript)"
	@echo "  $(YELLOW)test-e2e$(NC)      Run E2E tests (Playwright)"
	@echo "  $(YELLOW)ci-e2e$(NC)        Run E2E CI pipeline (lint + ty + test)"
	@echo ""
	@echo "$(BLUE)🚀 Combined:$(NC)"
	@echo "  $(YELLOW)ci$(NC)            Run full CI pipeline (Python + E2E)"
	@echo ""
	@echo "$(BLUE)🐳 Containers:$(NC)"
	@echo "  $(YELLOW)build-images$(NC)  Build Docker/Podman images"
	@echo "  $(YELLOW)up$(NC)            Start services in containers"
	@echo "  $(YELLOW)down$(NC)          Stop and remove containers"
	@echo "  $(YELLOW)restart$(NC)       Restart all services (down + up)"
	@echo "  $(YELLOW)logs$(NC)          Show container logs"
	@echo "  $(YELLOW)status$(NC)        Show container and image status"
	@echo "  $(YELLOW)health$(NC)        Check application health"
	@echo "  $(YELLOW)check-deps$(NC)    Verify dependency consistency between pyproject.toml and containers"
	@echo ""
	@echo "$(BLUE)🧹 Cleanup:$(NC)"
	@echo "  $(YELLOW)clean$(NC)         Basic cleanup (stopped containers + dangling images)"
	@echo "  $(YELLOW)clean-containers$(NC)  Remove stopped containers"
	@echo "  $(YELLOW)clean-images$(NC)  Remove dangling images"
	@echo "  $(YELLOW)clean-project$(NC) Remove project-specific containers and images"
	@echo "  $(YELLOW)clean-all$(NC)     Deep cleanup (containers, images, volumes, networks)"
	@echo "  $(YELLOW)prune$(NC)         Nuclear cleanup (ALL unused Docker objects) - requires confirmation"
	@echo ""
	@echo "$(BLUE)💡 Examples:$(NC)"
	@echo "  $(GREEN)make ci$(NC)                    # Run full checks"
	@echo "  $(GREEN)DOCKER=docker make up$(NC)      # Use Docker instead of Podman"
	@echo "  $(GREEN)make clean-project$(NC)         # Clean only light-score containers"
	@echo "  $(GREEN)make status$(NC)                # Check current container status"
	@echo ""
	@echo "$(BLUE)🔧 Environment Variables:$(NC)"
	@echo "  $(YELLOW)DOCKER$(NC)        Container engine (podman|docker) - default: podman"
	@echo "  $(YELLOW)PYTHON$(NC)        Python interpreter - default: .venv/bin/python"
