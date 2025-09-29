# AI Chatbot & Autonomous Researcher

A full-stack prototype that pairs a conversational AI with an autonomous background-research engine. It ships with:

* React 19 front-end
* FastAPI + LangGraph back-end
* Motivation-driven research scheduler
* **Privacy-preserving AI personalization system**
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

## Key Features

### 🤖 AI Personalization System
The assistant learns your preferences and adapts its responses while keeping all data private and transparent:

* **Privacy-First**: All personalization data stored locally, never transmitted externally
* **Adaptive Learning**: Learns from your reading patterns, source preferences, and interaction habits  
* **Transparent Control**: See exactly what the system has learned with full override capabilities
* **Smart Formatting**: Automatically adjusts response length, detail level, and structure
* **Source Intelligence**: Prioritizes research sources based on your engagement patterns

👤 **User Experience**: Three-tab interface (Personality, Preferences, What I've Learned) gives you complete control over how the AI adapts to your needs.

### 🔬 Multi-Source Research Engine  
Motivation-driven background research that continuously learns about topics you're interested in. Features intelligent multi-source search that combines web, academic, social (Hacker News), and medical sources for comprehensive responses. 

**Key Features:**
* **Autonomous Topic Expansion** - System automatically discovers related topics using knowledge graph analysis and AI
* **Smart Limits** - Enforces maximum active topics (default: 10) to prevent overwhelming users
* **Graceful Handling** - When at capacity, expansion topics are created as inactive suggestions for manual review
* **Manual Control** - Create custom research topics or choose from AI-suggested expansions

### 📊 Knowledge Graph Visualization
Visual representation of research findings and topic relationships powered by Zep memory.

## Learn More

* docs/setup.md – prerequisites, env variables, testing  
* docs/research_engine.md – how autonomous research & motivation work
* **docs/personalization.md – AI personalization system (complete guide + API reference)**
* docs/ARCHITECTURE.md – multi-source search system architecture
* docs/admin_debugging.md – admin UI, debug APIs, logging & tracing
* docs/user_guide.md – everyday usage including Knowledge Graph
* docs/zep_graph_visualization.md – Knowledge Graph implementation details
* docs/troubleshooting.md – common errors and fixes

## License

GPL-3.0 