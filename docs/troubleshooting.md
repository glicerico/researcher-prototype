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
* Force a run: `POST /research/trigger/<userId>`.

## User settings not persisting

User profiles are stored under `backend/storage_data/`.  Verify the process has write permission, or delete the directory to reset state.

## Graph visualisation fails

* Install Graphviz (`dot --version` should work).
* On some systems you may need `pip install pygraphviz` and uncomment it in `requirements.txt`.

## Common test failures

* Missing API key – integration tests are skipped unless `OPENAI_API_KEY` is set.
* Front-end test snapshots may fail if you upgraded React.  Run `npm run test -- -u` to update snapshots. 