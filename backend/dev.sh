#!/usr/bin/env bash
# Activate venv
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/venv/bin/activate"
# Ensure backend directory is on PYTHONPATH for module resolution
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Run FastAPI with built-in watcher
exec uvicorn app:app \
    --host 0.0.0.0 --port 8000 \
    --reload \
    --timeout-graceful-shutdown 20
