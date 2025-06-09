#!/usr/bin/env bash

# Setup script for the AI Chatbot Web App
# Creates a Python virtual environment in backend/, installs backend
# dependencies and frontend npm packages.

set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

# --- Backend setup ---
BACKEND_DIR="$REPO_ROOT/backend"

# Create virtual environment if it doesn't exist
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo "Creating virtual environment in $BACKEND_DIR/venv"
    python3 -m venv "$BACKEND_DIR/venv"
fi

# Activate virtual environment
echo "Activating virtual environment"
source "$BACKEND_DIR/venv/bin/activate"

# Upgrade pip and install requirements
pip install --upgrade pip
pip install -r "$BACKEND_DIR/requirements.txt"

# --- Frontend setup ---
FRONTEND_DIR="$REPO_ROOT/frontend"

echo "Installing npm dependencies in $FRONTEND_DIR"
cd "$FRONTEND_DIR"
npm install
cd "$REPO_ROOT"

cat <<'EOM'
Setup complete!
To run the application:
1. Start the backend server (activate the virtual environment first):
   source backend/venv/bin/activate
   python backend/app.py
2. In another terminal, start the frontend:
   cd frontend && npm start
EOM
