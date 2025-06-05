# AGENTS.md – Guide for AI Assistants Contributing to **researcher-prototype**

This document gives Codex (and any other AI coding assistant) the context, conventions, and commands it needs to work effectively inside this repository.

---

## 1. Repository Overview

The project is a **full-stack AI chatbot** that combines a FastAPI + LangGraph backend with a React frontend.

Directory quick-look:

• `backend/`  → Python 3.9+ service exposing the REST API and autonomous research engine.
  • `app.py`          Main FastAPI application (entry-point).
  • `graph_builder.py` LangGraph builder for the chat pipeline.
  • `research_graph_builder.py` LangGraph builder for the background research flow.
  • `nodes/`          Composable LangGraph nodes (router, search, analysis, research, …).
  • `storage_data/`   JSON persistence for users, conversations, and research findings (git-ignored).
  • `tests/`          Pytest test-suite (`unit/` & `integration/`).
  • `run_tests.sh`    Helper script to run tests / coverage.

• `chatbot-react/` → React 18 SPA consuming the backend API.
  • `src/components/` UI components (functional, hooks-based, `.jsx`).
  • `src/services/`   `axios` wrappers talking to FastAPI.
  • `src/styles/`     CSS modules / plain CSS.

• `setup.sh`     → One-shot script that installs Python + npm dependencies.

If you add files, keep the structure coherent (e.g. new LangGraph nodes into `backend/nodes/`, new React UI parts into `chatbot-react/src/components/`).

---

## 2. Key Technologies

Backend  : FastAPI · LangGraph · LangChain · Pydantic v2 · AsyncIO · PyGraphviz (visualisation)
Frontend : React 18 · Axios · Context API · Jest/React-Testing-Library
Tooling  : Pytest · Coverage.py · ESLint (airbnb, react-hooks) · Prettier · Husky git hooks (optional)

---

## 3. Coding Conventions

### 3.1 Python (backend)
1. **PEP-8** & **black 23+** formatting (120 columns).
2. Type-hint everything that crosses a module boundary. Prefer `pydantic.BaseModel` for structured data.
3. Use asynchronous endpoints (`async def`) in FastAPI unless blocking IO is inevitable.
4. Log with the central `logging_config.py` helpers (`get_logger`, emoji prefixes).
5. Secrets come from **environment variables** only—never commit keys.
6. When a change introduces a new LangGraph node:
   • Put it in `backend/nodes/<feature>_node.py`.
   • Expose a `node(state: dict) -> dict` callable.
   • Add the node to `graph_builder.py` or `research_graph_builder.py` with clear transition names.

### 3.2 JavaScript / React (frontend)
1. Use **functional components** with hooks. No class components.
2. Keep components small; extract logic hooks to `src/utils/` when reusable.
3. Prop-types optional—prefer TypeScript _only_ if you convert the whole file.
4. Style with plain CSS or inline Tailwind-like utility classes kept in `*.css`. Avoid global overrides.
5. API calls go through the single `src/services/api.js` Axios instance (handles user-id header).
6. Tests reside next to components as `*.test.js(x)` using React-Testing-Library.

### 3.3 Commit Style
• Message = `<scope>: <imperative summary>` (e.g. `backend: add deduplication node`).
• Reference issues (`#123`) and emoji in body if helpful.

---

## 4. Quality Gates

Run these before opening a PR or pushing via AI:

### Backend
```bash
cd backend
source venv/bin/activate  # ensure virtualenv
# Static code
black --check .
flake8 .
# Tests
./run_tests.sh --coverage
```

### Frontend
```bash
cd chatbot-react
npm run lint
npm test -- --watchAll=false
npm run build   # ensure prod build succeeds
```

All commands must exit 0.

---

## 5. Pull Request Checklist
1. **Describe** what/why in plain language; link issues.
2. Include **screenshots** / GIFs for UI changes.
3. Ensure tests pass & coverage ≥ current master.
4. Update **README.md** and **this AGENTS.md** if architecture or conventions change.
5. Keep the PR focused (≤ 400 lines diff ideal).

---

## 6. Common Dev Tasks (Cheat-Sheet)

```bash
# 🎉 One-time setup
./setup.sh  # installs Python & npm deps

# ▶️ Run everything (two terminals)
python backend/app.py      # http://localhost:8000
cd chatbot-react && npm start  # http://localhost:3000

# ✅ Run unit tests only
cd backend && ./run_tests.sh

# 🔍 Regenerate LangGraph diagram
cd backend
python graph_builder.py  # produces graph.png

# 🐛 Enable verbose tracing
export LANGCHAIN_TRACING_V2=true
python backend/app.py
```

---

## 7. Environment Variables
Create `backend/.env` (copy `.env.example`) with at least:
```
OPENAI_API_KEY=<key>
API_HOST=0.0.0.0
API_PORT=8000
DEFAULT_MODEL=gpt-4o-mini
ZEP_ENABLED=false  # optional advanced memory
```
The React app reads `chatbot-react/.env.*` – `REACT_APP_API_URL` should point to the backend.

---

## 8. When Working as Codex

• Read existing code before generating fixes—use `grep` & `ripgrep`.
• Prefer **minimal diffs**; preserve surrounding context markers when editing.
• Never commit secrets, large binaries, or OS-specific code (Windows/MacOS). The CI/linter will fail.
• If you are uncertain (≤ 95 % confidence), ask clarifying questions rather than guessing.

---

_This document supersedes the original `AGENTS.md.template`. Keep it up to date as the project evolves._ 