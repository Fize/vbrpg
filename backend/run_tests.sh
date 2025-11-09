#!/bin/bash

# Run tests script for backend
# Usage: ./run_tests.sh [unit|integration|all] [--coverage]

set -e

cd "$(dirname "$0")"

# Parse arguments
TEST_TYPE="${1:-all}"
COVERAGE="${2:-}"

echo "🧪 Running backend tests..."

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run tests based on type
case "$TEST_TYPE" in
    unit)
        echo "📦 Running unit tests only..."
        if [ "$COVERAGE" = "--coverage" ]; then
            pytest tests/unit/ -v --cov=src --cov-report=term-missing --cov-report=html
        else
            pytest tests/unit/ -v
        fi
        ;;
    integration)
        echo "🔗 Running integration tests only..."
        if [ "$COVERAGE" = "--coverage" ]; then
            pytest tests/integration/ -v --cov=src --cov-report=term-missing --cov-report=html
        else
            pytest tests/integration/ -v
        fi
        ;;
    all)
        echo "🚀 Running all tests..."
        if [ "$COVERAGE" = "--coverage" ]; then
            pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
        else
            pytest tests/ -v
        fi
        ;;
    *)
        echo "❌ Invalid test type: $TEST_TYPE"
        echo "Usage: ./run_tests.sh [unit|integration|all] [--coverage]"
        exit 1
        ;;
esac

echo "✅ Tests completed!"
