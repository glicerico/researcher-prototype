# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Full-stack AI research assistant prototype combining conversational AI with autonomous background research. Features React 19 frontend, FastAPI + LangGraph backend, motivation-driven research scheduling, and Knowledge Graph visualization powered by Zep.

## Architecture

### Backend (`backend/`)
- **Entry Point**: `app.py` - Main FastAPI application
- **Graph Builders**: `graph_builder.py` (chat flow), `research_graph_builder.py` (research flow)  
- **API Routes**: `api/` - Modular FastAPI routers (chat, research, graph, topics, users, admin)
- **LangGraph Nodes**: `nodes/` - Composable pipeline components (router, search, analysis, etc.)
- **Storage**: `storage/` - Managers for Zep, research data, user profiles
- **Data**: `storage_data/` - Local JSON persistence (users, conversations, findings)

### Frontend (`frontend/src/`)
- **Components**: Functional React components with hooks in `components/`
- **Services**: `services/api.js` - Axios wrappers for backend communication
- **Context**: React Context API for state management
- **Styles**: Plain CSS modules in `styles/`

## Development Commands

### Setup & Development
```bash
# Initial setup (installs venv + npm dependencies)
./setup.sh

# Start both services (recommended)
npm install  # only needed once
npm run dev  # starts backend + frontend with concurrently
```

Note: Graph visualization requires Graphviz installed (the `dot` CLI). On Debian/Ubuntu: `sudo apt-get install graphviz`.

### Backend Testing
```bash
cd backend
source venv/bin/activate
./run_tests.sh                 # Unit tests only
./run_tests.sh --all           # Include integration tests (needs OPENAI_API_KEY)
./run_tests.sh --coverage      # Run with coverage report
```

### Frontend Testing  
```bash
cd frontend
npm test                       # Interactive test runner
npm run test:unit             # Unit tests only
npm run test:integration      # Integration tests only  
npm run test:all              # All tests
npm run lint                  # ESLint
# Optional coverage report
npm test -- --coverage
```

### Single Service Development
```bash
# Backend only (manual)
cd backend && source venv/bin/activate
uvicorn app:app --reload

# Frontend only  
cd frontend && npm start
```

## Code Conventions

### Python (Backend)
- **Format**: Black formatter, 120-character line length
- **Linting**: flake8 with extended ignores for E203, W503
- **Types**: Type hints required for module boundaries, prefer Pydantic models
- **Async**: Use `async def` for FastAPI endpoints unless blocking IO required
- **Virtual Environment**: Always use `backend/venv/` (activated by `dev.sh`)
- **No Backward Compatibility**: This is a prototype - do not maintain backward compatibility. Change interfaces, data formats, and APIs freely as needed. Focus on clean, correct implementation over preserving old behavior. Do not mention in comments removed methods which no longer exist, as compatibility is not needed.

### React (Frontend)  
- **Components**: Functional components with hooks only, no classes
- **Testing**: Jest + React Testing Library, tests beside components as `*.test.js`
- **API**: All backend calls through `services/api.js` (handles user-id header)
- **Styling**: Plain CSS or CSS modules, avoid global overrides

### LangGraph Integration
- **New Nodes**: Place in `backend/nodes/<feature>_node.py` 
- **Interface**: Export `node(state: dict) -> dict` callable
- **Registration**: Add to appropriate graph builder with clear transition names

### Zep Integration
- **SDK Usage**: Use correct methods (`client.graph.node.get_by_user_id()`)
- **Entity IDs**: Use `uuid_` field, not `uuid`  
- **Pagination**: Implement cursor-based pagination for large datasets
- **Error Handling**: Graceful fallbacks for API errors

## Testing Strategy

### Backend Tests (`backend/tests/`)
- **Unit**: `unit/` - Component isolation, fast execution
- **Integration**: `integration/` - API endpoints with real services
- **Markers**: Use pytest markers (`@pytest.mark.integration`)
- **Environment**: Integration tests require `OPENAI_API_KEY`

### Frontend Tests
- **Unit**: Component logic and utilities
- **Integration**: User interactions and API communication  
- **Coverage**: Available in `frontend/coverage/`

## Key Features & Flows

- **Chat Pipeline**: LangGraph orchestration in `graph_builder.py`
- **Research Engine**: Autonomous background research via `research_graph_builder.py`
- **Motivation System**: Native scoring determines when to research (`motivation.py`)
- **Knowledge Graph**: Zep-powered memory and visualization
- **Admin Console**: JWT-secured interface with prompt editor
- **Search Integration**: Perplexity for internet search, OpenAlex for academic search
- Respond in a concise but complete way. Like Einstein said: make it as simple as possible, but not simpler.