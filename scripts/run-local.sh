#!/usr/bin/env bash
# Start backend (FastAPI) and frontend (Flask) locally using the Python runner

set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

if [ ! -x ".venv/bin/python" ]; then
  echo "🔧 Bootstrapping .venv via uv..."
  if ! command -v uv >/dev/null 2>&1; then
    echo "❌ uv not found. Install uv or run ./scripts/install-deps.sh"
    exit 1
  fi
  uv venv
  ./scripts/uv-sync.sh --all
fi

echo "🚀 Starting local runner (backend + frontend) with cache generation..."
exec .venv/bin/python run_local.py
