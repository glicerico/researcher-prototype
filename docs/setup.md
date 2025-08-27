# Setup & Installation

This page walks you through installing the **Researcher-Prototype** in a development environment.  For production hints see the bottom of this file.

## 1. Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10 or 3.11 |
| Node.js | 18+ |
| npm     | 9+  |
| Graphviz | latest (for optional graph visualisation) |
| OpenAI account | with API key |
| Zep Cloud account | with API key (optional, for Knowledge Graph) |

> Ubuntu / Debian:
> ```bash
> sudo apt-get update && sudo apt-get install -y python3.11 graphviz nodejs npm
> ```

## 2. Backend (FastAPI + LangGraph)

```bash
# from repo root
cd backend
python -m venv venv
source venv/bin/activate  # fish/zsh adjust accordingly
pip install -r requirements.txt

# create .env
cp .env.example .env
nano .env                 # paste your OPENAI_API_KEY and adjust anything else

# Optional: Configure Zep for Knowledge Graph
# Add these to your .env file:
# ZEP_API_KEY=your_zep_api_key_here
# ZEP_ENABLED=true

# run the API
uvicorn app:app --reload  --host 0.0.0.0 --port 8000
```

The interactive docs will be at `http://localhost:8000/docs`.

## 3. Frontend (React 19)

```bash
cd ../frontend
npm install
npm start
```

React dev-server will launch at `http://localhost:3000` and proxy API calls to `http://localhost:8000` (configured in `.env.development`).  Change `REACT_APP_API_URL` if your backend lives elsewhere.

## 4. Running locally with one command

A helper script bundles the above steps (except adding the API key):

```bash
./setup.sh
```

## 5. Tests

### Backend

```bash
cd backend && source venv/bin/activate
./run_tests.sh            # unit tests
./run_tests.sh --all      # + integration (requires valid OPENAI_API_KEY)
./run_tests.sh --coverage # coverage report

# Test external search APIs directly
python tests/integration/test_search_apis.py --all --query "machine learning"
python tests/integration/test_search_apis.py --semantic-scholar --query "transformers" --limit 5
python tests/integration/test_search_apis.py --hn --query "python" --limit 3
```

### Frontend

```bash
cd frontend
npm run test:unit         # component tests
npm run test:integration  # integration tests (API mocked)
```

## 6. Building for production

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

Host `frontend/build` behind Nginx / Caddy or any static server and point it to the backend. 