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

### Active Research Topics Limit
The system enforces a limit on how many topics can be actively researched simultaneously per user:

- `MAX_ACTIVE_RESEARCH_TOPICS_PER_USER` (default 10, range 1-50): Maximum active research topics
  - Applies to ALL topics (manual + autonomous expansions)
  - **User behavior**: Cannot manually activate more topics when at limit; must deactivate existing topics first
  - **Autonomous behavior**: Expansion topics are created as **INACTIVE** when limit is reached (awaiting manual activation)
  - **UI feedback**: Modal popup explains the limit when user tries to activate beyond capacity

### Topic Expansion Pipeline
The expansion system automatically discovers related research topics based on user interactions and knowledge graph exploration. **Requires Zep** for candidate generation and validation.

**LLM Configuration:**
- `EXPANSION_LLM_MODEL` (default gpt-4o-mini): LLM model for topic generation
- `EXPANSION_LLM_CONFIDENCE_THRESHOLD` (default 0.6, range 0.0-1.0): Min confidence for accepting topics
- `EXPANSION_LLM_TIMEOUT_SECONDS` (default 30, range 1-120): Timeout for LLM calls
- Internal constants: `EXPANSION_LLM_MAX_TOKENS=800`, `EXPANSION_LLM_TEMPERATURE=0.2`, `EXPANSION_LLM_SUGGESTION_LIMIT=3`

**Expansion Depth & Breadth Control:**
- `EXPANSION_MAX_DEPTH` (default 2, range 1-10): Max depth for expansion chains (root=0, child=1, grandchild=2, etc.)
- `EXPANSION_MAX_PARALLEL` (default 2, range 1-64): Max concurrent expansion research tasks
- `EXPANSION_MAX_TOTAL_TOPICS_PER_USER` (default 10, range 1-100): Max total expansion topics per user
- `EXPANSION_MAX_UNREVIEWED_TOPICS` (default 5, range 1-50): Max unreviewed topics before pausing expansion
- `EXPANSION_REVIEW_ENGAGEMENT_THRESHOLD` (default 0.2, range 0.0-1.0): Engagement threshold that counts as "reviewed"

**Zep Knowledge Graph Search:**
- `EXPANSION_MIN_SIMILARITY` (default 0.35, range 0.0-1.0): Min similarity score for candidates
- Internal constants: `ZEP_SEARCH_LIMIT=10`, `ZEP_SEARCH_RERANKER=cross_encoder`, `ZEP_SEARCH_TIMEOUT_SECONDS=5`, `ZEP_SEARCH_RETRIES=2`

**Lifecycle Management (Internal Constants):**
- `EXPANSION_ENGAGEMENT_WINDOW_DAYS=7`: Days to look back for engagement scoring
- `EXPANSION_PROMOTE_ENGAGEMENT=0.35`: Engagement threshold to enable child expansions
- `EXPANSION_RETIRE_ENGAGEMENT=0.1`: Engagement threshold to retire topics
- `EXPANSION_MIN_QUALITY=0.6`: Minimum quality threshold for promotion
- `EXPANSION_BACKOFF_DAYS=7`: Days to back off after low engagement
- `EXPANSION_RETIRE_TTL_DAYS=30`: Days before retiring inactive expansions

### How Topic Expansion Works
1. **Candidate Generation**: Zep graph search finds related nodes/edges from user's knowledge graph
2. **LLM Selection**: LLM augments, filters, and ranks candidates based on relevance and research-worthiness
3. **Validation**: All suggestions validated against Zep for similarity scoring
4. **Limit Check**: System checks if `MAX_ACTIVE_RESEARCH_TOPICS_PER_USER` would be exceeded
5. **Topic Creation**: 
   - **Below limit**: Expansion topics created with research **ACTIVE** (auto-researched)
   - **At limit**: Expansion topics created as **INACTIVE** (awaiting manual activation by user)
6. **Lifecycle Management**: Child expansions gated by engagement scores, quality metrics, and depth limits
7. **Concurrent Research**: Active expansion topics researched in parallel within `EXPANSION_MAX_PARALLEL` limit

**Debug endpoint:** `POST /api/research/debug/expand/{user_id}` accepts `{ root_topic, create_topics?, enable_research?, limit? }`. Returns candidate list, created topics, skipped duplicates, and basic metrics. When Zep disabled, returns `{ success: false, error: 'Zep disabled' }`.

---

## 8. When Working as Codex

• Read existing code before generating fixes—use `grep` & `ripgrep`.
• Prefer **minimal diffs**; preserve surrounding context markers when editing.
• Never commit secrets, large binaries, or OS-specific code (Windows/MacOS). The CI/linter will fail.
• If you are uncertain (≤ 95 % confidence), ask clarifying questions rather than guessing.
