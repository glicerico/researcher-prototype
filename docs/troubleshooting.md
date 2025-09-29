# Troubleshooting

## API key not working

* Ensure `OPENAI_API_KEY` is in `backend/.env` **and** your OpenAI account has credit.
* Check backend log for HTTP 401 / 429 responses from OpenAI.

## Frontend can't reach backend

* Is the API running on port 8000?  
* Confirm `REACT_APP_API_URL` in `frontend/.env.development` matches.
* Open browser dev-tools → Network tab → look for CORS errors.

## Research engine seems idle

* Is it enabled? `GET /research/status` should return `"enabled": true`.
* Drives may be below threshold – inspect via `GET /research/debug/motivation`.
* Force a run: `POST /research/trigger/{user_id}`.

## User settings not persisting

User profiles are stored under `backend/storage_data/users/`.  Verify the process has write permissions, or delete the directory to reset state.

## Graph visualisation fails

* Install Graphviz (`dot --version` should work).
* Note: `pygraphviz` is commented out in `requirements.txt` as it's not required for basic graph generation.

## Knowledge Graph issues

* **Empty graph**: User needs conversation data in Zep to populate the graph. Have some chats first.
* **"Zep service unavailable"**: Check `ZEP_API_KEY` in `backend/.env` and ensure `ZEP_ENABLED=true`.
* **Graph won't load**: Check backend logs for Zep API errors. Verify API key permissions.
* **"Failed to fetch graph data"**: Usually a Zep connection issue. Check network and API key.
* **Graph visualization broken**: Ensure D3.js is installed (`npm install d3` in frontend).

## Common test failures

* Missing API key – integration tests are skipped unless `OPENAI_API_KEY` is set.
* Front-end test snapshots may fail if you upgraded React.  Run `npm run test -- -u` to update snapshots. 