#!/usr/bin/env bash

# Setup script for the AI Chatbot Web App
# Assumes you have already activated a Python virtual environment and
# configured environment variables as needed. Installs backend
# dependencies and frontend npm packages.

set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

# --- Backend setup ---
BACKEND_DIR="$REPO_ROOT/backend"

# Upgrade pip and install requirements
pip install --upgrade pip
pip install -r "$BACKEND_DIR/requirements.txt"

# --- Frontend setup ---
FRONTEND_DIR="$REPO_ROOT/chatbot-react"

echo "Installing npm dependencies in $FRONTEND_DIR"
cd "$FRONTEND_DIR"
npm install
cd "$REPO_ROOT"

cat <<'EOM'
Setup complete!
To run the application:
1. Start the backend server (make sure your virtual environment is active):
   python backend/app.py
2. In another terminal, start the frontend:
   cd chatbot-react && npm start
EOM
