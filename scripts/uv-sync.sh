#!/bin/bash
# Sync all dependencies using uv with optional extras

set -euo pipefail

echo "🔄 Syncing project dependencies with uv..."

# Ensure uv is installed
if ! command -v uv >/dev/null 2>&1; then
  echo "❌ uv is not installed. Please install uv: https://docs.astral.sh/uv/"
  exit 1
fi

# Ensure uv venv exists
if [ ! -d ".venv" ]; then
  uv venv
fi

# Always install dev dependencies declared in pyproject
EXTRA_FLAGS=(--dev)

# Install extras
if [ "${1:-}" = "--all" ]; then
  echo "➕ Installing all component extras (backend, frontend, functions, security)"
  EXTRA_FLAGS+=(--all-extras)
fi

# Perform sync against pyproject.toml
uv sync "${EXTRA_FLAGS[@]}"

echo "✅ Sync complete."
