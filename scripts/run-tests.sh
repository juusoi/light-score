#!/bin/bash
# Simple test runner using the project's virtual environment (.venv)

set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

echo "🧪 Running all tests for light-score project using .venv..."

VENV_PY="$ROOT_DIR/.venv/bin/python"

if [ ! -x "$VENV_PY" ]; then
    echo "❌ .venv not found or python missing at $VENV_PY"
    echo "👉 Run './scripts/install-deps.sh' or 'uv venv && ./scripts/uv-sync.sh --all' first."
    exit 1
fi

echo "🔧 Using Python: $VENV_PY"

# Run backend tests
echo ""
echo "🏗️  Running backend tests..."
cd "$ROOT_DIR/backend/src"
"$VENV_PY" -m pytest utest/ -v
cd "$ROOT_DIR"

# Run frontend tests
echo ""
echo "🌐 Running frontend tests..."
cd "$ROOT_DIR/frontend/src"
"$VENV_PY" -m pytest utest/ -v
cd "$ROOT_DIR"

# Run functions tests
echo ""
echo "⚡ Running functions tests..."
cd "$ROOT_DIR/functions/src"
"$VENV_PY" -m pytest utest/ -v
cd "$ROOT_DIR"

echo ""
echo "🎉 All tests completed successfully!"
