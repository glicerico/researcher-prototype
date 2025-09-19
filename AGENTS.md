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
  • `api/`            Modular FastAPI routers (chat, research, graph, topics, users, admin, status, notifications).
  • `services/`       Core services (logging_config, prompt/search/auth/status managers, personalization manager, research engine, etc.).
  • `storage/`        Managers for profiles, research data, Zep integration.
  • `storage_data/`   JSON persistence for users, conversations, and research findings (git-ignored).
  • `tests/`          Pytest test-suite (`unit/` & `integration/`).
  • `run_tests.sh`    Helper script to run tests / coverage.

• `frontend/` → React 19 SPA consuming the backend API.
  • `src/components/` UI components (functional, hooks-based, `.jsx`).
  • `src/services/`   `axios` wrappers talking to FastAPI.
  • `src/styles/`     CSS modules / plain CSS.

• `setup.sh`     → One-shot script that installs Python + npm dependencies.

If you add files, keep the structure coherent (e.g. new LangGraph nodes into `backend/nodes/`, new React UI parts into `frontend/src/components/`).

---

## 2. Key Technologies

Backend  : FastAPI · LangGraph · LangChain · Pydantic v2 · AsyncIO · Graphviz (dot) via LangGraph built-ins (visualisation)
Frontend : React 19 · Axios · Context API · Jest/React-Testing-Library
Tooling  : Pytest · Coverage.py · ESLint (react-app) · Prettier · Husky git hooks (optional)

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
cd frontend
npm run lint

# Frontend Testing - Use appropriate command for your scenario:
npm run test:unit         # Daily development (fast, mocked APIs)
npm run test:integration  # When backend is running (real API tests)
npm run test:all         # Full test suite (CI/CD, releases)

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

# ▶️ Run everything (one terminal)
npm install             # at repo root (once; installs 'concurrently')
npm run dev             # starts backend + frontend together

# ▶️ Run everything (two terminals)
python backend/app.py      # http://localhost:8000
cd frontend && npm start  # http://localhost:3000

# ✅ Run unit tests only
cd backend && ./run_tests.sh

# 🔍 Regenerate LangGraph diagrams
cd backend
python graph_builder.py                    # produces graph.png (main chat)
python research_graph_builder.py           # produces research_graph.png (research flow)
python research_graph_builder.py --all     # produces chat_graph.png + research_graph.png

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
The React app reads `frontend/.env.*` – `REACT_APP_API_URL` should point to the backend.

### Topic Expansion Pipeline
The expansion system automatically discovers and researches related topics based on user interactions and knowledge graph exploration. It requires Zep for candidate generation and validation.

**Core Configuration:**
- `EXPANSION_ENABLED` (default false): enable autonomous expansion generation in research loop
- `EXPLORATION_PER_ROOT_MAX` (default 2): per-root budget of child expansions to persist
- `EXPANSION_MAX_PARALLEL` (default 2): max concurrent expansion research tasks
- `EXPANSION_MIN_SIMILARITY` (default 0.35): drop candidates below this Zep similarity threshold

**Zep Knowledge Graph Search:**
- `ZEP_SEARCH_LIMIT` (default 10)
- `ZEP_SEARCH_RERANKER` (default cross_encoder)
- `ZEP_SEARCH_TIMEOUT_SECONDS` (default 5)
- `ZEP_SEARCH_RETRIES` (default 2)

**LLM Selection and Augmentation:**
- `EXPANSION_LLM_ENABLED` (default true)
- `EXPANSION_LLM_MODEL` (default gpt-4o-mini)
- `EXPANSION_LLM_MAX_TOKENS` (default 800)
- `EXPANSION_LLM_TEMPERATURE` (default 0.2)
- `EXPANSION_LLM_SUGGESTION_LIMIT` (default 6)
- `EXPANSION_LLM_TIMEOUT_SECONDS` (default 12)

**Lifecycle and Depth Management:**
- `EXPANSION_MAX_DEPTH` (default 2)
- `EXPANSION_ENGAGEMENT_WINDOW_DAYS` (default 7)
- `EXPANSION_PROMOTE_ENGAGEMENT` (default 0.35)
- `EXPANSION_RETIRE_ENGAGEMENT` (default 0.1)
- `EXPANSION_MIN_QUALITY` (default 0.6)
- `EXPANSION_BACKOFF_DAYS` (default 7)
- `EXPANSION_RETIRE_TTL_DAYS` (default 30)

### How Topic Expansion Works
1. **Candidate Generation**: Zep graph search finds related nodes/edges from user's knowledge graph
2. **LLM Selection**: Optional LLM call to augment, filter, and rank candidates based on relevance
3. **Validation**: All suggestions (including LLM-generated) are validated against Zep for similarity scoring
4. **Scheduling**: Selected candidates become new research topics with expansion metadata
5. **Lifecycle Management**: Child expansions are gated by engagement scores, quality metrics, and depth limits
6. **Concurrent Research**: Multiple expansion topics are researched in parallel within configured limits

Debug endpoint: `POST /api/research/debug/expand/{user_id}` accepts `{ root_topic, create_topics?, enable_research?, limit? }`. Returns candidate list, created topics, skipped duplicates, and basic metrics. When Zep disabled, returns `{ success: false, error: 'Zep disabled' }`.

---

## 8. When Working as Codex

• Read existing code before generating fixes—use `grep` & `ripgrep`.
• Prefer **minimal diffs**; preserve surrounding context markers when editing.
• Never commit secrets, large binaries, or OS-specific code (Windows/MacOS). The CI/linter will fail.
• If you are uncertain (≤ 95 % confidence), ask clarifying questions rather than guessing.
