#!/bin/bash

# Change to the backend directory
cd "$(dirname "$0")" || exit

# Run all unit tests
echo "Running unit tests..."
python3 -m pytest -v -m "not integration"

# Check if we want to run integration tests
if [ "$1" == "--all" ] || [ "$1" == "-a" ]; then
    # Check if OPENAI_API_KEY is set
    if [ -z "$OPENAI_API_KEY" ]; then
        echo "OPENAI_API_KEY is not set. Skipping integration tests."
    else
        echo "Running integration tests..."
        python3 -m pytest -v -m "integration"
    fi
fi

# Run with coverage if requested
if [ "$1" == "--coverage" ] || [ "$1" == "-c" ]; then
    echo "Running tests with coverage..."
    python3 -m pytest --cov=. --cov-report=term-missing tests/
fi 