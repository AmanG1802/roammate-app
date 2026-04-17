# Roammate

Roammate is a collaborative trip-planning application. Users create trips, invite collaborators, curate ideas in a shared Idea Bin, and build day-by-day itineraries on a drag-and-drop timeline. A live concierge mode powered by OpenAI helps refine plans in real time.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS |
| Backend | FastAPI (Python 3.11), SQLAlchemy (async), Pydantic |
| Database | PostgreSQL 15 + PostGIS |
| Cache | Redis |
| AI | OpenAI API via LangChain |
| Maps | Google Maps JavaScript API |
| Containerisation | Docker Compose |

---

## Prerequisites

- **macOS** (the guide uses Homebrew and Colima; adapt for Linux/Windows)
- **Homebrew** - https://brew.sh
- **Python 3.10+** - for the optional local virtual environment
- **Node.js 20+** - only needed if running the frontend outside Docker

---

## 1. Install Container Runtime

Roammate runs in Docker containers orchestrated by Docker Compose. On macOS you can use **Colima** as a lightweight alternative to Docker Desktop.

```bash
brew install colima docker docker-compose
```

Start Colima (allocate resources to taste):

```bash
colima start --cpu 4 --memory 8 --disk 60
```

Verify everything is working:

```bash
colima status
docker info
```

### Auto-start Colima on login (optional)

```bash
brew services start colima
```

To disable: `brew services stop colima`

---

## 2. Set Up a Local Virtual Environment (optional)

A root-level `requirements.txt` lists the host-side tooling (Colima, Docker CLI, Compose). You can track it in a virtual environment so the versions are pinned per-project:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> **Note:** The backend and frontend dependencies are installed _inside_ their Docker containers automatically. You do **not** need to install them on the host. The venv above is only for the container tooling itself.

---

## 3. Configure Environment Variables

Copy the example file and fill in your keys:

```bash
cp .env.example .env
```

Open `.env` and set the required values:

```dotenv
# Database (defaults are fine for local dev)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=roammate

# Required API keys
OPENAI_API_KEY=<your-openai-key>
GOOGLE_MAPS_API_KEY=<your-google-maps-key>

# Backend JWT secret - change in production
SECRET_KEY=change-me-to-a-long-random-secret-key

# Frontend (used at build time inside the container)
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=<your-google-maps-key>
```

After changing API keys on a running stack, restart the backend:

```bash
docker compose restart backend
```

---

## 4. Build and Run

Make sure Colima (or Docker Desktop) is running, then:

```bash
docker compose up --build
```

On first launch the database initialises from scratch, which takes a few seconds. The backend waits for a PostgreSQL health check before starting, so there is no race condition.

To run in the background:

```bash
docker compose up --build -d
```

---

## 5. Accessing the App

Once all containers are healthy:

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000/api |
| Interactive API Docs (Swagger) | http://localhost:8000/docs |
| Alternative API Docs (ReDoc) | http://localhost:8000/redoc |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

---

## 6. Common Docker Commands

### Lifecycle

```bash
docker compose up              # start (foreground)
docker compose up -d           # start (background)
docker compose down            # stop, keep data
docker compose down -v         # stop, delete all data & volumes
docker compose restart         # restart all services
docker compose restart backend # restart one service
```

### Logs

```bash
docker compose logs -f           # follow all logs
docker compose logs -f backend   # follow one service
docker compose logs -f frontend
docker compose logs -f db
```

### Rebuild

```bash
docker compose up --build        # rebuild everything
docker compose build backend     # rebuild one service
docker compose build frontend
```

### Status & Inspection

```bash
docker compose ps                # running containers
docker ps                        # all Docker containers
docker stats                     # live resource usage
```

### Shell Access

```bash
docker compose exec backend bash
docker compose exec frontend sh
docker compose exec db psql -U postgres -d roammate
```

### Nuclear Reset

```bash
docker compose down --rmi all -v
docker compose up --build
```

---

## 7. Development Workflow

Both services have **hot-reload** enabled — edit files on your host and changes are picked up automatically:

- **Backend** (`backend/`): Uvicorn watches for Python file changes
- **Frontend** (`frontend/`): Next.js fast-refreshes on save

### Adding Backend Dependencies

```bash
# 1. Edit backend/requirements.txt
# 2. Rebuild
docker compose build backend
docker compose up -d backend
```

### Adding Frontend Dependencies

```bash
# 1. Edit frontend/package.json (or npm install inside the container)
# 2. Rebuild
docker compose build frontend
docker compose up -d frontend
```

### Database Migrations

```bash
docker compose exec backend bash
alembic upgrade head
```

---

## 8. Project Structure

```
roammate-app/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── api/          # Route handlers
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   └── main.py       # App entrypoint
│   └── requirements.txt  # Python dependencies
├── frontend/             # Next.js application
│   ├── app/              # Pages (App Router)
│   ├── components/       # React components
│   ├── hooks/            # Custom hooks
│   ├── lib/              # Utilities & store
│   └── package.json      # Node dependencies
├── docker/               # Dockerfiles
│   ├── backend.Dockerfile
│   └── frontend.Dockerfile
├── docker-compose.yml    # Container orchestration
├── .env.example          # Template for environment variables
├── requirements.txt      # Host-side tooling (Colima, Docker)
└── README.md             # This file
```

---

## 9. Troubleshooting

### "Cannot connect to Docker daemon"

```bash
colima status          # is it running?
colima start           # start it
docker context use colima
```

### Port already in use

```bash
lsof -i :3000
lsof -i :8000
# Kill the offending process, or change the port in docker-compose.yml
```

### Backend fails to connect to the database

The `docker-compose.yml` includes a health check on the `db` service. If you still hit connection errors, the database may not have finished initialising. Wait a few seconds and restart the backend:

```bash
docker compose restart backend
```

### Database needs a fresh start

```bash
docker compose down -v
docker compose up --build
```

---

## 10. Useful Links

- [Next.js 14 Docs](https://nextjs.org/docs)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [PostgreSQL + PostGIS](https://postgis.net/)
- [Docker Compose Reference](https://docs.docker.com/compose/)
