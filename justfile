# Project configuration
python := ".venv/bin/python"
project := "light-score"

# Container engine: override with `just --set docker docker`
docker := "podman"

# Default recipe: show available commands
default:
    @just --list

# --- Development ---

# Set up development environment (venv + deps + security tools)
dev-setup:
    uv venv --allow-existing
    uv sync --dev --all-extras
    uv pip install 'bandit[toml]>=1.8.0' 'pip-audit>=2.7.0'
    @echo "✅ Development environment ready!"
    @echo "💡 Activate with: source .venv/bin/activate"

# Sync all dependencies from pyproject.toml
sync:
    uv sync --dev --all-extras

# --- Code Quality (Python) ---

# Run linter (ruff check)
lint:
    {{ python }} -m ruff check .

# Lint GitHub Actions workflows (actionlint)
lint-actions:
    #!/usr/bin/env bash
    set -euo pipefail
    if command -v actionlint >/dev/null 2>&1; then
        actionlint .github/workflows/*.yaml
    else
        {{ docker }} run --rm -v "$(pwd):/repo" -w /repo rhysd/actionlint:latest \
            -color .github/workflows/*.yaml
    fi

# Format code (ruff format)
fmt:
    {{ python }} -m ruff format .

# Run type checking (ty)
ty:
    {{ python }} -m ty check .

# Run all Python tests (backend + frontend + functions)
test:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "🏗️  Running backend tests..."
    cd backend/src && {{ justfile_directory() }}/{{ python }} -m pytest utest/ -v
    echo "🌐 Running frontend tests..."
    cd {{ justfile_directory() }}/frontend/src && {{ justfile_directory() }}/{{ python }} -m pytest utest/ -v
    echo "⚡ Running functions tests..."
    cd {{ justfile_directory() }}/functions/src && {{ justfile_directory() }}/{{ python }} -m pytest utest/ -v
    echo "✅ All tests passed!"

# Run full CI pipeline (lint + actions lint + type check + test)
ci: lint lint-actions ty test

# --- Security ---

# Run security checks (bandit + pip-audit)
security:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "🔍 Running Bandit security scan..."
    {{ python }} -m bandit -r backend/src -x "backend/src/utest" -q
    {{ python }} -m bandit -r frontend/src -x "frontend/src/utest" -q
    {{ python }} -m bandit -r functions/src -x "functions/src/utest" -q
    echo "✅ Bandit scan passed!"
    echo "🔍 Running pip-audit dependency scan..."
    {{ python }} -m pip_audit --desc
    echo "✅ Dependency audit passed!"

# --- E2E Tests (TypeScript) ---

[private]
ensure-e2e-deps:
    #!/usr/bin/env bash
    if [ ! -d "e2e/node_modules" ]; then
        echo "📦 Installing E2E dependencies..."
        cd e2e && bun install
    fi

# Run E2E linting (ESLint)
lint-e2e: ensure-e2e-deps
    cd e2e && bun run lint

# Format E2E code (Prettier)
fmt-e2e: ensure-e2e-deps
    cd e2e && bun run fmt

# Run E2E type checking (TypeScript)
ty-e2e: ensure-e2e-deps
    cd e2e && bun run type-check

# Run E2E tests (Playwright)
test-e2e: ensure-e2e-deps
    cd e2e && bun run test:ci

# Run E2E CI pipeline (lint + type check + test)
ci-e2e: lint-e2e ty-e2e test-e2e

# --- Mock Mode ---

# Start services with mock ESPN data
mock-up:
    MOCK_ESPN=true {{ docker }} compose up -d
    @echo "✅ Mock services started!"
    @echo "💡 Backend: http://localhost:8000 (fixture data)"
    @echo "💡 Frontend: http://localhost:5000"

# Run tests in mock mode
test-mock:
    MOCK_ESPN=true just test

# --- Containers ---

# Build Docker/Podman images
build-images:
    {{ docker }} compose build

# Start services in containers
up:
    {{ docker }} compose up -d
    @echo "✅ Services started!"
    @echo "💡 Backend: http://localhost:8000"
    @echo "💡 Frontend: http://localhost:5000"

# Stop and remove containers
down:
    {{ docker }} compose down -v --remove-orphans

# Show container logs (follow)
logs:
    {{ docker }} compose logs -f --tail=100

# Show container and image status
status:
    {{ docker }} ps --filter "name={{ project }}" --format "table {{{{.Names}}}}\t{{{{.Status}}}}\t{{{{.Ports}}}}"
    @echo ""
    {{ docker }} images --filter "reference=localhost/{{ project }}*" --format "table {{{{.Repository}}}}\t{{{{.Tag}}}}\t{{{{.Size}}}}\t{{{{.CreatedSince}}}}"

# Restart all services
restart: down up

# Check dependency consistency
check-deps:
    bash scripts/check-deps.sh

# Check application health
health:
    #!/usr/bin/env bash
    echo "Backend health:"
    curl -sf http://localhost:8000/ > /dev/null && echo "  ✅ Backend is healthy" || echo "  ❌ Backend is unhealthy"
    echo "Frontend health:"
    curl -sf http://localhost:5000/ > /dev/null && echo "  ✅ Frontend is healthy" || echo "  ❌ Frontend is unhealthy"

# --- Cleanup ---

# Basic cleanup (stopped containers + dangling images)
clean: clean-containers

# Remove stopped containers
clean-containers:
    {{ docker }} container prune -f

# Remove dangling images
clean-images:
    {{ docker }} image prune -f

# Deep cleanup (containers, images, volumes, networks)
clean-all: down
    {{ docker }} container prune -f
    {{ docker }} image prune -a -f
    {{ docker }} volume prune -f
    {{ docker }} network prune -f

# Remove project-specific containers and images
clean-project:
    {{ docker }} ps -a --filter "name={{ project }}" --format "{{{{.ID}}}}" | xargs -r {{ docker }} rm -f 2>/dev/null || true
    {{ docker }} images --filter "reference=localhost/{{ project }}*" --format "{{{{.ID}}}}" | xargs -r {{ docker }} rmi -f 2>/dev/null || true

# Nuclear cleanup — ALL unused Docker objects (requires confirmation)
prune:
    #!/usr/bin/env bash
    read -p "⚠️  Remove ALL unused Docker objects? (y/N): " confirm
    [[ "$confirm" == "y" ]] || exit 1
    {{ docker }} system prune -a -f --volumes
    echo "💥 Nuclear cleanup complete!"
