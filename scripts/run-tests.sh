#!/bin/bash
# Run all tests script

set -e

echo "🧪 Running all tests for light-score project..."

# Function to check if virtual environment is activated
check_venv() {
    if [ -z "$VIRTUAL_ENV" ] && [ ! -f ".venv/bin/activate" ]; then
        echo "❌ No virtual environment found. Please run ./scripts/install-deps.sh first (pyproject-first)"
        exit 1
    fi
}

# Function to get Python executable path
get_python() {
    if [ -f ".venv/bin/python" ]; then
        echo ".venv/bin/python"
    elif [ -n "$VIRTUAL_ENV" ]; then
        echo "python"
    else
    # Use the system Python with PYTHONPATH set to venv site-packages
        echo "PYTHONPATH=$(find .venv/lib -name site-packages -type d 2>/dev/null | head -1) $(which python3)"
    fi
}

check_venv

PYTHON_CMD=$(get_python)

echo "🔧 Using Python: $PYTHON_CMD"

# Run backend tests
echo ""
echo "🏗️  Running backend tests..."
cd backend/src
eval "$PYTHON_CMD -m pytest utest/ -v"
cd ../..

# Run frontend tests  
echo ""
echo "🌐 Running frontend tests..."
cd frontend/src
eval "$PYTHON_CMD -m pytest utest/ -v"
cd ../..

# Run functions tests
echo ""
echo "⚡ Running functions tests..."
cd functions/src
eval "$PYTHON_CMD -m pytest utest/ -v"
cd ../..

echo ""
echo "🎉 All tests completed successfully!"
