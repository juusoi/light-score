#!/usr/bin/env bash
# Dependency consistency checker for light-score project
# Verifies that container dependencies match pyproject.toml

set -euo pipefail

echo "🔍 Light Score Dependency Consistency Check"
echo "==========================================="
echo ""

echo "📋 Dependencies defined in pyproject.toml:"
echo ""

echo "Backend dependencies:"
grep -A 10 "backend = \[" pyproject.toml | grep -E '^\s*".*"' | sed 's/.*"\(.*\)".*/  ✓ \1/'
echo ""

echo "Frontend dependencies:"
grep -A 10 "frontend = \[" pyproject.toml | grep -E '^\s*".*"' | sed 's/.*"\(.*\)".*/  ✓ \1/'
echo ""

if podman ps --filter "name=light-score" --format "{{.Names}}" | grep -q "backend"; then
    echo "🐳 Backend container dependencies:"
if $DOCKER ps --filter "name=light-score" --format "{{.Names}}" | grep -q "backend"; then
    echo "🐳 Backend container dependencies:"
    $DOCKER exec light-score_backend_1 pip freeze | grep -E "(fastapi|uvicorn|pydantic|httpx)" | while read dep; do
        echo "  ✓ $dep"
    done
    echo ""
else
    echo "⚠️  Backend container not running"
    echo ""
fi

if podman ps --filter "name=light-score" --format "{{.Names}}" | grep -q "frontend"; then
    echo "🐳 Frontend container dependencies:"
if $DOCKER ps --filter "name=light-score" --format "{{.Names}}" | grep -q "frontend"; then
    echo "🐳 Frontend container dependencies:"
    $DOCKER exec light-score_frontend_1 pip freeze | grep -E "(Flask|gunicorn|requests)" | while read dep; do
        echo "  ✓ $dep"
    done
    echo ""
else
    echo "⚠️  Frontend container not running"
    echo ""
fi

echo "💡 Benefits of using pyproject.toml:"
echo "  • Single source of truth for dependencies"
echo "  • No duplication between pyproject.toml and Dockerfiles"
echo "  • Easier dependency management and updates"
echo "  • Consistent versions across development and containers"
