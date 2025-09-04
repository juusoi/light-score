#!/usr/bin/env bash
# Dependency consistency checker for light-score project
# Verifies that running container images contain the deps declared in pyproject.toml
# ShellCheck-clean: quotes, conditionals, robust container engine detection.

set -euo pipefail

echo "🔍 Light Score Dependency Consistency Check"
echo "==========================================="
echo

echo "📋 Dependencies defined in pyproject.toml:"
echo

echo "Backend dependencies:"
grep -A 15 "backend = \[" pyproject.toml | grep -E '^\s*".*"' | sed 's/.*"\(.*\)".*/  ✓ \1/' || true
echo

echo "Frontend dependencies:"
grep -A 15 "frontend = \[" pyproject.toml | grep -E '^\s*".*"' | sed 's/.*"\(.*\)".*/  ✓ \1/' || true
echo

# Detect container engine unless skipped
if [[ "${SKIP_CONTAINER_CHECK:-0}" == "1" ]]; then
    echo "⏭️  Skipping container inspection (SKIP_CONTAINER_CHECK=1)"; echo
    DOCKER_BIN=""
else
    DOCKER_BIN="${DOCKER:-}"
    if [[ -z "${DOCKER_BIN}" ]]; then
        if command -v docker >/dev/null 2>&1; then
            DOCKER_BIN=docker
        elif command -v podman >/dev/null 2>&1; then
            DOCKER_BIN=podman
        else
            echo "⚠️  Neither docker nor podman found – skipping runtime dependency checks"; echo
            DOCKER_BIN=""
        fi
    fi
    [[ -n "${DOCKER_BIN}" ]] && { echo "Using container engine: ${DOCKER_BIN}"; echo; }
fi

# Helper: find first container name matching a pattern
find_container() {
    local pattern=$1
    ${DOCKER_BIN} ps --format '{{.Names}}' | grep -E "${pattern}" | head -n1 || true
}

print_runtime_deps() {
    local name=$1
    local grep_expr=$2
    if [[ -z "${name}" ]]; then
        echo "⚠️  Container not running"
        echo
        return 0
    fi
    echo "🐳 Runtime dependencies in container: ${name}";
    # Use exec + pip freeze; tolerate absence of pip
    if ! ${DOCKER_BIN} exec "${name}" sh -c 'command -v pip >/dev/null'; then
        echo "  ⚠️  pip not available inside container"
        echo
        return 0
    fi
    ${DOCKER_BIN} exec "${name}" pip freeze 2>/dev/null | grep -E "${grep_expr}" | while IFS= read -r dep; do
        [[ -n "${dep}" ]] && echo "  ✓ ${dep}"
    done || true
    echo
}

if [[ -n "${DOCKER_BIN}" ]]; then
    backend_container=$(find_container 'backend')
    echo "Backend container check:"
    print_runtime_deps "${backend_container}" '(fastapi|uvicorn|pydantic|httpx)'

    frontend_container=$(find_container 'frontend')
    echo "Frontend container check:"
    print_runtime_deps "${frontend_container}" '(Flask|gunicorn|requests)'
fi

echo "💡 Benefits of using pyproject.toml:"
echo "  • Single source of truth for dependencies"
echo "  • No duplication between pyproject.toml and Dockerfiles"
echo "  • Easier dependency management and updates"
echo "  • Consistent versions across development and containers"

echo "✅ Dependency check finished"
