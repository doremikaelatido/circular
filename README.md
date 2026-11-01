# Social Circle Calendar

A V1 social activity calendar with a React/TypeScript client and FastAPI/PostgreSQL API.

## Architecture and data model

- **Backend:** FastAPI routers are grouped by domain. Pydantic validates inputs; services centralize event lifecycle, visibility, and leave-notification rules, with SQLAlchemy handling persistence. Alembic owns schema changes.
- **Frontend:** React Router pages and TanStack Query hooks consume typed REST resources. A single weekly calendar component receives data and callbacks; fetching and view selection live outside it.
- **Users and connections:** Connection rows are stored in canonical user-ID order and carry pending/accepted/declined status. Only accepted direct links grant circle visibility.
- **Events:** Events belong to a creator; participant rows are separate and have active/left state. Invitations are not participation. Notifications are one row per leave action/recipient.
- **Visibility:** “My Calendar” includes active upcoming events created or joined by the user. “My Circle” includes active upcoming events created by an accepted direct connection or actively joined by one. The same server predicate protects event detail.
- **Assumptions:** Access tokens are short-lived, held only in memory, and there is no refresh token. Event date inputs are interpreted in the browser’s local timezone and transmitted as UTC instants. Connection requests may be sent to users found by exact email or nickname substring. Invitations grant the invitee event-detail/join access but do not count as participation or create notifications.

## Project layout

```text
backend/
  app/                 FastAPI app, domain models, schemas, services and routes
  alembic/             Database migration environment
  tests/               Pytest API and business-rule tests
frontend/
  src/                 React app, features, calendar, hooks and UI
```

## Local setup

Prerequisites: Docker with the Compose plugin, Python 3.11+, and Node.js 22.12+.

1. Start the Docker PostgreSQL database from the project root with `docker compose up -d db`. It creates a persistent local volume.
2. Copy `backend/.env.example` to `backend/.env` and replace the placeholder `JWT_SECRET`.
3. In `backend/`, run `python3 -m venv .venv`, activate it, install with `pip install -r requirements.txt`, apply migrations with `alembic upgrade head`, then start `uvicorn app.main:app --reload`.
4. Copy `frontend/.env.example` to `frontend/.env`, then in `frontend/` run `npm install` and `npm run dev`.
5. Open the Vite URL. Development API docs are available at `http://localhost:8000/docs`.

For the detailed terminal-by-terminal instructions, see [LOCAL_DEVELOPMENT.md](./LOCAL_DEVELOPMENT.md).

Stop the database with `docker compose down`; its data remains in the named volume. Use `docker compose down --volumes` only when you want to delete that local database data.

## Deploying on Vercel with Neon

Use two Vercel projects connected to the same Git repository: one project for the static Vite frontend and a separate Python/FastAPI project for the API. This avoids mixing the independent build/runtime configuration. See Vercel’s guides for [FastAPI](https://vercel.com/docs/frameworks/backend/fastapi) and [Vite](https://vercel.com/docs/frameworks/frontend/vite), and Neon’s guide to [connecting from an application](https://neon.com/docs/connect/connect-from-any-app).

### 1. Create the Neon database

1. Create a Neon project and database.
2. In the Neon console, open **Connect**, select the branch/database/role, and copy the connection string.
3. For the Vercel API, use Neon's **pooled** connection string (hostname includes `-pooler`) to handle serverless database connections. The backend accepts Neon's usual `postgresql://` URL and converts it to the installed Psycopg 3 SQLAlchemy driver automatically.
4. Keep a **direct** connection string for applying migrations. Never commit either URL or paste it into frontend variables.

### 2. Deploy the FastAPI backend

1. Import the repository into Vercel as a new project. Set **Root Directory** to `backend/`. Vercel's Python runtime detects the FastAPI `app` in `app/main.py` and uses `requirements.txt` for dependencies.
2. Add these environment variables in the backend project's Vercel settings for Production (and Preview if you will use previews):

   | Variable | Value |
   | --- | --- |
   | `DATABASE_URL` | Neon pooled URL, including the password and `sslmode=require` query parameter. |
   | `JWT_SECRET` | A unique random secret of at least 32 characters. Generate one locally; do not commit it. |
   | `JWT_ACCESS_TOKEN_MINUTES` | `20` (or another value from 1 to 60). |
   | `CORS_ORIGINS` | Exact frontend origin, e.g. `https://your-frontend.vercel.app` (no trailing slash). |
   | `ENVIRONMENT` | `production` |
   | `DOCS_ENABLED` | `false` |

3. Deploy and note the API's production URL. Confirm its `/health` endpoint returns `{"status":"ok"}`. The deployed API prefix is `/api`; docs are disabled in production by default.

### 3. Apply the database migration

Run the migration from your own machine using the direct Neon connection URL. From the `backend/` directory:

```bash
DATABASE_URL='postgresql://USER:PASSWORD@DIRECT_HOST/DB?sslmode=require' alembic upgrade head
```

The application translates the standard `postgresql://` URL to Psycopg 3 automatically. The migration runs against the selected Neon branch, so verify that branch before executing it. Do not run migrations automatically for every Vercel build.

### 4. Deploy the React frontend

1. Import the same repository into Vercel as a second project. Set **Root Directory** to `frontend/`. Vercel detects Vite; use `npm run build` and the `dist` output directory if it does not fill those in automatically.
2. Add the frontend environment variable `VITE_API_URL` with the deployed API prefix, e.g. `https://your-api.vercel.app/api`.
3. Deploy. [frontend/vercel.json](./frontend/vercel.json) rewrites SPA paths to `index.html`, so routes such as `/connections` and `/inbox` continue to work after refresh.
4. Add the final frontend production origin to the API project's `CORS_ORIGINS`, then redeploy the API if you changed it.

Vite embeds `VITE_API_URL` at build time: changing that setting requires a new frontend deployment. For preview deployments, configure a corresponding preview `VITE_API_URL` and allow the exact preview origin in the API's Preview `CORS_ORIGINS`; do not use an unrestricted wildcard.

### Environment variables

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection URL. Use Neon's pooled URL for the deployed API and a direct URL when running migrations. |
| `JWT_SECRET` | JWT signing secret; use a unique random value in production. |
| `JWT_ACCESS_TOKEN_MINUTES` | Short access-token lifetime (default 20 minutes). |
| `CORS_ORIGINS` | Comma-separated exact frontend origins. |
| `DOCS_ENABLED` | Enables docs only outside production; set `false` in production. |
| `ENVIRONMENT` | Set to `production` to enable production configuration checks. |
| `VITE_API_URL` | Frontend API base URL, including `/api`; Vite reads this during build. |

## Database migrations

Run `alembic upgrade head` in `backend/` to create/update the schema. Create a new migration with `alembic revision --autogenerate -m "describe change"` and review its generated operations before applying it.

## Tests

Install backend requirements and run `pytest` in `backend/`. Backend tests use SQLite for fast isolated API tests; the Alembic initial migration is also validated against SQLite. Frontend tests are run with `npm test` in `frontend/`, and `npm run build` performs the strict TypeScript check plus production build.

## API

FastAPI serves `/docs` and `/openapi.json` in development. Set `DOCS_ENABLED=false` to disable public API documentation.

## V1 boundaries

No event search API, refresh tokens, email/push/chat, event approval flow, or multi-hop connection visibility is included. Search in the header is intentionally a non-functional visual placeholder.
