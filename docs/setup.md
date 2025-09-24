# Setup & Installation

This guide covers installing the **Researcher-Prototype** for development. For production deployment see the bottom of this file.

## Quick Start (Recommended)

The fastest way to get started:

```bash
# 1. Install dependencies (one-time setup)
./setup.sh                    # installs Python venv + npm deps
npm install                   # installs concurrently for parallel dev servers

# 2. Configure environment
cd backend
cp .env.example .env
nano .env                     # add your OPENAI_API_KEY

# 3. Start everything
cd ..
npm run dev                   # starts both backend + frontend in parallel
```

Visit `http://localhost:3000` for the React app (proxies API calls to `http://localhost:8000`).

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.9+ |
| Node.js | 18+ |
| npm     | 9+  |
| Graphviz | latest (for graph visualization) |
| OpenAI account | with API key |
| Zep Cloud account | with API key (optional, for Knowledge Graph) |

> Ubuntu / Debian:
> ```bash
> sudo apt-get update && sudo apt-get install -y python3 python3-venv graphviz nodejs npm
> ```

## Manual Setup (Alternative)

If you prefer to set up each component separately:

### Backend (FastAPI + LangGraph)

```bash
# from repo root
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# create .env
cp .env.example .env
nano .env                 # add your OPENAI_API_KEY and other settings

# Optional: Configure Zep for Knowledge Graph
# Add these to your .env file:
# ZEP_API_KEY=your_zep_api_key_here
# ZEP_ENABLED=true

# run the API
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The interactive docs will be at `http://localhost:8000/docs`.

### Frontend (React 19)

```bash
cd ../frontend
npm install
npm start
```

React dev server launches at `http://localhost:3000` and proxies API calls to `http://localhost:8000`.

## Testing

### Backend Tests

```bash
cd backend && source venv/bin/activate
./run_tests.sh            # unit tests
./run_tests.sh --all      # + integration (requires valid OPENAI_API_KEY)
./run_tests.sh --coverage # coverage report

# Test external search APIs directly
python tests/integration/test_search_apis.py --all --query "machine learning"
python tests/integration/test_search_apis.py --openalex --query "transformers" --limit 5
python tests/integration/test_search_apis.py --hn --query "python" --limit 3
```

### Frontend Tests

```bash
cd frontend
npm run test:unit         # component tests
npm run test:integration  # integration tests (requires backend running)
npm run test:all          # full test suite
```

## Email Notifications (Optional)

Configure SMTP in `backend/.env` for background research notifications:

```
# Gmail/Workspace example
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USE_SSL=false
SMTP_USER=<your_email_address>
SMTP_PASSWORD=<your_16_char_app_password>
EMAIL_FROM=<display_from_address>

# Deep-link base for email buttons
FRONTEND_URL=http://localhost:3000
```

**Important**: Use an App Password, not your normal email password. For Google accounts: enable 2-Step Verification, then create an App Password (16-character code) for `SMTP_PASSWORD`.

## Production Build

```bash
# Backend (example with Gunicorn + Uvicorn workers)
source backend/venv/bin/activate
cd backend
pip install gunicorn uvicorn
exec gunicorn app:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --workers 2 --timeout 90

# Frontend
cd ../frontend
npm run build             # outputs static files to frontend/build/
```

Host the `frontend/build` directory with any static server (Nginx, Caddy, etc.) and configure it to proxy API requests to the backend. 