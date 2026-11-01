# Run Social Circle Calendar Locally

This guide starts a Docker-managed PostgreSQL database and runs the FastAPI backend and React frontend on your computer.

## Requirements

- Python 3.11 or newer
- Node.js 22.12 or newer (npm is included)
- Docker Desktop (or Docker Engine) with the Compose plugin

## 1. Start PostgreSQL with Docker

From the project root, start the database:

```bash
docker compose up -d db
```

Compose creates the `social_circle` database and a named volume to preserve its data between restarts. The database is available on `localhost:5433` (container port `5432`), avoiding conflicts with a PostgreSQL server already running on your Mac. The Compose credentials are for local development only and match the example backend configuration.

## 2. Configure and start the backend

In a terminal, move into the backend directory:

```bash
cd backend
```

Create a local environment file from the example:

```bash
cp .env.example .env
```

Open `backend/.env`, set `DATABASE_URL` to your PostgreSQL connection URL, and replace `JWT_SECRET` with a random local secret. The example database URL targets the Docker database on host port `5433`:
doc
```dotenv
DATABASE_URL=postgresql+psycopg://postgres:your-local-password@localhost:5433/social_circle
JWT_SECRET=replace-this-with-a-random-local-secret
JWT_ACCESS_TOKEN_MINUTES=20
CORS_ORIGINS=http://localhost:5173
DOCS_ENABLED=true
ENVIRONMENT=development
```

Generate a random local JWT secret if desired:

```bash
openssl rand -hex 32
```

Create and activate a virtual environment, install dependencies, and apply the database migration:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
alembic upgrade head
```

Start the API:

```bash
uvicorn app.main:app --reload
```

The backend runs at `http://localhost:8000`. Interactive API docs are at `http://localhost:8000/docs`; the health check is `http://localhost:8000/health`.

Keep this terminal open while using the app.

## 3. Configure and start the frontend

Open a second terminal at the project root and move into the frontend directory:

```bash
cd frontend
```

Create the frontend environment file and install packages:

```bash
cp .env.example .env
npm install
```

For local development, the example config points to `http://localhost:8000/api`. If that is not your backend address, update `VITE_API_URL` in `frontend/.env`.

Start Vite:

```bash
npm run dev
```

Open the local URL printed by Vite, usually `http://localhost:5173`.

## 4. Use the app

1. Register an account from the sign-in page.
2. Log in and create an event.
3. Use **Connections** to find another account and send/accept a request.
4. Join an event with another account to exercise circle visibility and notifications.

The database must be running, and both the API and frontend development server must remain open.

## 5. Run checks

With the backend virtual environment activated, from `backend/`:

```bash
pytest
```

From `frontend/`:

```bash
npm test
npm run build
```

## Stop the database

From the project root, stop the database without removing its data:

```bash
docker compose down
```

To delete the local database and all its data as well, run `docker compose down --volumes`.

## Troubleshooting

- **Database connection refused:** Check that Docker is running and start the database with `docker compose up -d db`. Confirm pgAdmin and `DATABASE_URL` use host port `5433`.
- **Frontend cannot reach API:** Check that Uvicorn is running on port `8000` and `VITE_API_URL` ends with `/api`.
- **CORS error in browser:** Ensure `CORS_ORIGINS` in `backend/.env` includes the exact Vite origin, usually `http://localhost:5173`, then restart Uvicorn.
- **Missing tables:** Run `alembic upgrade head` from the `backend/` directory with the virtual environment activated.

## Logout behavior note

The current frontend logout clears the access token held in JavaScript memory, clears the signed-in user state, and clears cached API data. It does **not** call the backend `/api/auth/logout` endpoint.

The backend endpoint itself requires a valid bearer token and responds with `{"message":"Signed out"}`. It does not revoke or blacklist the JWT. A copied token remains usable until its configured expiration (20 minutes by default). Logging out in the current frontend therefore signs out that browser application state, not the token on the server.
