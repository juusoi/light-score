#!/bin/bash
# Lint, format, and type check script (uses .venv binaries)

set -e

echo "🔍 Running code quality checks..."

VENV_BIN=".venv/bin"
if [ ! -x "$VENV_BIN/python" ]; then
    echo "❌ .venv not found. Create it first (e.g., make venv or uv venv && uv sync)."
    exit 1
fi

PY="$VENV_BIN/python"
RUFF_BIN="$VENV_BIN/ruff"
TY_BIN="$VENV_BIN/ty"

echo "🔧 Using Python: $PY"

# Run ruff linting
echo ""
echo "🧹 Running ruff linting..."
if [ -x "$RUFF_BIN" ]; then
    "$RUFF_BIN" check .
else
    "$PY" -m ruff check .
fi

# Run ruff formatting
echo ""
echo "✨ Running ruff formatting..."
if [ -x "$RUFF_BIN" ]; then
    "$RUFF_BIN" format .
else
    "$PY" -m ruff format .
fi

# Run ty type checking (optional)
echo ""
echo "🔬 Running ty type checking..."
if [ -x "$TY_BIN" ]; then
    PYTHONPATH="backend/src:frontend/src:functions/src:${PYTHONPATH}" "$TY_BIN" check . || {
        echo "⚠️  Type checking found issues (expected in alpha version)"
        echo "   ty is pre-release software, these may be false positives"
    }
else
    # Fallback to module if present
    if "$PY" -c "import importlib; import sys; sys.exit(0 if importlib.util.find_spec('ty') else 1)"; then
        PYTHONPATH="backend/src:frontend/src:functions/src:${PYTHONPATH}" "$PY" -m ty check . || {
            echo "⚠️  Type checking found issues (expected in alpha version)"
            echo "   ty is pre-release software, these may be false positives"
        }
    else
        echo "ℹ️  Skipping ty: not installed in .venv (install via 'uv sync --dev')."
    fi
fi

echo ""
echo "✅ Code quality checks completed!"
