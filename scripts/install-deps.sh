#!/bin/bash
# Install dependencies using uv (pyproject-first)

set -euo pipefail

echo "🚀 Installing dependencies for light-score project (pyproject-first)..."

# Ensure uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "✅ uv installed successfully"
fi

# Ensure virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    uv venv
fi

echo "� Syncing dependencies from pyproject.toml (with dev deps and all extras)..."
./scripts/uv-sync.sh --all

echo "✅ All dependencies installed via uv sync!"
echo "💡 To activate the virtual environment: source .venv/bin/activate"
