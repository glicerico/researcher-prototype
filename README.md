# AI Chatbot & Autonomous Researcher

A full-stack prototype that pairs a conversational AI with an autonomous background-research engine. It ships with:

* React 19 front-end
* FastAPI + LangGraph back-end
* Motivation-driven research scheduler
* Knowledge Graph visualization (powered by Zep)
* JWT-secured admin console & prompt editor
* Local JSON storage – no external DB needed

## Quick Start (dev)

### One-shot (recommended)

```bash
# install JS dev deps (only needed once)
npm install

# start both backend (Uvicorn ‑-reload) + frontend (React) in parallel
npm run dev
```

That command:
1. activates the virtual-env inside `backend/venv/`.
2. launches Uvicorn with auto-reload and a 20-second graceful-shutdown window.
3. starts the React dev server.
4. streams both logs side-by-side via [`concurrently`](https://www.npmjs.com/package/concurrently).

### Manual (legacy)

```bash
# 1. clone repo & run helper script
./setup.sh               # installs backend venv + npm deps

# 2. start backend
cd backend && source venv/bin/activate
uvicorn app:app --reload

# 3. start frontend (new shell)
cd ../frontend && npm start
```

Detailed installation / production guides live in the docs folder.

## Repository Layout

```
backend/   FastAPI application, LangGraph, storage
frontend/  React UI
setup.sh   one-shot installer for dev stacks
docs/      extended documentation (setup, research engine, admin debug …)
```

## Learn More

* docs/setup.md – prerequisites, env variables, testing
* docs/research_engine.md – how autonomous research & motivation work
* docs/admin_debugging.md – admin UI, debug APIs, logging & tracing
* docs/user_guide.md – everyday usage including Knowledge Graph
* docs/zep_graph_visualization.md – Knowledge Graph implementation details
* docs/troubleshooting.md – common errors and fixes

## License

GPL-3.0 