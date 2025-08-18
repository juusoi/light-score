#!/bin/bash
# Quick development setup script

set -e

echo "⚡ Quick setup for light-score development..."

# Install dependencies
echo "1️⃣ Installing dependencies..."
./scripts/install-deps.sh

# Run tests to verify setup
echo ""
echo "2️⃣ Running tests to verify setup..."
./scripts/run-tests.sh

echo ""
echo "🎯 Setup complete! You're ready to develop."
echo ""
echo "Next steps:"
echo "  • Activate environment: source .venv/bin/activate"
echo "  • Start backend: cd backend/src && python main.py"
echo "  • Start frontend: cd frontend/src && python app.py"
echo "  • Run local servers: python run_local.py"
