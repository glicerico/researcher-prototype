# Admin Console & Debugging Tools

## 1. Admin Console (React)

The admin UI is bundled inside the front-end build and accessible at `/admin`.

### Login

```
POST /admin/login   { "password": "<ADMIN_PASSWORD>" }
```

Credentials come from the backend `.env`:

```
ADMIN_PASSWORD=admin123               # change in production!
ADMIN_JWT_SECRET=super-secret-string
ADMIN_JWT_EXPIRE_MINUTES=480
```

After logging in the JWT is stored in `localStorage`; subsequent requests add `Authorization: Bearer <token>`.

### Features

| Section | What it does |
|---------|--------------|
| **Prompt Editor** | View & edit system / node prompts with version history and live test run |
| **Flow Visualiser** | Fetches generated PNG/SVG diagrams of the LangGraph and research flow |
| **Status Panel** | Quick health checks (OpenAI key, Zep memory, research engine status) |

To regenerate diagrams on-demand:

```
POST /admin/flows/diagrams/generate  # add ?force_regenerate=true to ignore cache
```

## 2. Debug Endpoints (Research)

All routes live under `/research/debug/*` and do **not** require admin auth – use responsibly.

* `GET  /research/debug/motivation` – inspect current drives & next scheduled run
* `POST /research/debug/adjust-drives?boredom=0.9` – nudge drives
* `POST /research/debug/update-config` – JSON body with any of: `threshold`, `boredom_rate`, `curiosity_decay`, `tiredness_decay`, `satisfaction_decay`
* `POST /research/debug/active-topics` – list active topics for all users

## 3. Logging & Tracing

* **Logging** – configurable via `logging_config.py`; emojis mark graph stages.  Use `configure_logging(level=logging.DEBUG)` for verbose output.
* **LangSmith Tracing** – enable by setting `LANGCHAIN_TRACING_V2=true` and API key.  Links to each trace appear in the log output.

## 4. Visualising Graphs Locally

```bash
cd backend && source venv/bin/activate
python graph_builder.py              # creates graph.png
python research_graph_builder.py     # creates research_graph.png
```

Graphviz must be installed (`sudo apt-get install graphviz`). 