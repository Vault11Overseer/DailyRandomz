# DailyRandomz

A React + Python progressive web app for small discoveries. The first slice is random facts, with optional username/password accounts, favorites, and viewing preferences.

## Run locally

Open two terminals from this project folder.

**Python API**

```bash
cd backend
uv sync
uv run uvicorn backend.app:app --reload
```

**React frontend**

```bash
cd frontend
npm ci
npm run dev
```

Visit **http://localhost:5173**. API documentation is at http://127.0.0.1:8000/docs. Interactive write requests require the `X-Randomz-Request: 1` header; the app sends it automatically.

The existing dependencies were already installed when this project was inspected. `uv` manages Python packages; invoking it alone does not start a server. Use the full `uv run uvicorn ...` command above. If a terminal says `uv: command not found`, try `~/.local/bin/uv --version`. If that works, run `export PATH="$HOME/.local/bin:$PATH"` and add that line to your shell configuration for future terminals. `uv run backend` also starts the API, without auto-reload.

## Current behavior

- Guests can draw facts without an account.
- Accounts use unique, case-insensitive usernames (3–32 letters/numbers/underscores) and passwords (12–128 characters).
- Signed-in users skip previously drawn facts by default. Once all 12 starter facts are seen, the app offers a history reset through Settings. Repeats can also be enabled there.
- Favorites and preferences are stored on the server and follow the account across devices.
- Facts are drawn on opening the page and on demand; this version does not enforce a one-fact-per-calendar-day schedule.
- A production build installs as a PWA on supported browsers. After an online visit, the app shell and the last fact can load offline. Sign-in, favorites, settings, and new draws require the API. Private API responses are never service-worker cached. The last fact text (public content) is stored locally, not credentials.
- Quotes, music, and movies are labeled as future additions.

## Check the build and API

```bash
cd backend
uv run python -m unittest discover -s tests -v
```

```bash
cd frontend
npm run lint
npm run build
npm run preview
```

To test installation/offline behavior, use the production preview at http://localhost:4173. Start the API for that origin:

```bash
cd backend
APP_ORIGIN=http://localhost:4173 uv run uvicorn backend.app:app --reload
```

The dev and preview proxies forward `/api` requests to Python on port 8000. Use `localhost` consistently; origin validation deliberately rejects other origins. Service workers are enabled in production builds, not the Vite development server.

## Configuration and deployment

See `backend/.env.example`. Environment variables are read from the process; to load a file, pass `--env-file .env` to uvicorn.

- `DATABASE_PATH`: SQLite file location; defaults to `backend/randomz.db`. Database files are ignored by Git. Keep this file on persistent storage and back it up.
- `APP_ORIGIN`: exact frontend origin, without a trailing slash.
- `COOKIE_SECURE`: set to `true` with production HTTPS.

Serve `frontend/dist` and proxy `/api` to the Python service under **the same HTTPS origin**. The Vite preview server is only for local validation. Passwords are salted and hashed with scrypt. Random session tokens are stored as hashes in the database, expire after 30 days, and are delivered using HttpOnly, SameSite=Strict cookies. Mutation requests require a custom header and reject mismatched browser origins. Authentication attempts are throttled in SQLite per connecting IP.

This is a working local foundation, not a verified thousands-of-users deployment. Before a public launch, add email verification/password recovery or a managed identity provider, database migrations, a larger sourced content collection, monitoring and backups, and load tests for the expected traffic. Move to PostgreSQL and a shared rate limiter when running multiple API instances. Configure trusted proxy handling deliberately so rate limiting sees the correct client IP. SQLite currently serializes fact draws to keep account history consistent.

## Layout

- `backend/src/backend/app.py`: FastAPI routes, account/session handling, SQLite schema and starter facts.
- `backend/tests/test_api.py`: API integration tests using a fresh temporary database.
- `frontend/src/App.jsx`: discovery, sign-in, favorites and settings.
- `frontend/vite.config.js`: API proxy, web manifest and generated service worker.

Implementation references: [FastAPI response cookies](https://fastapi.tiangolo.com/advanced/response-cookies/) and [Vite PWA service worker strategies](https://vite-pwa-org.netlify.app/guide/service-worker-strategies-and-behaviors).
