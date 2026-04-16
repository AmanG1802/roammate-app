# Docker Setup Guide for Roammate App

## Installation Complete ✓

You've successfully installed Docker on your Mac using Colima (without Docker Desktop).

### What was installed:
- **Colima** - Lightweight container runtime for macOS
- **Docker CLI** - Command-line tool for Docker
- **Docker Compose** - Tool for defining multi-container applications

### Colima is now running with:
- 4 CPUs
- 8GB RAM
- 60GB disk space

---

## Quick Commands

### Managing Colima

```bash
# Check if Colima is running
colima status

# Start Colima (if stopped)
colima start

# Stop Colima
colima stop

# Restart Colima
colima restart
```

### Managing Your Roammate App

```bash
# Start all services (database, redis, backend, frontend)
docker compose up

# Start in background (detached mode)
docker compose up -d

# Stop all services
docker compose down

# View logs
docker compose logs -f

# View logs for specific service
docker compose logs -f backend
docker compose logs -f frontend

# Rebuild and start (after code changes)
docker compose up --build

# Remove all containers and volumes (fresh start)
docker compose down -v
```

---

## Environment Setup

Before starting the app, create a `.env` file in the project root with required API keys:

```bash
# Database (optional - defaults provided)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=roammate

# Required API keys
OPENAI_API_KEY=your_openai_api_key
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
```

---

## Starting Your App

1. **Make sure Colima is running:**
   ```bash
   colima status
   ```

2. **Start all services:**
   ```bash
   docker compose up
   ```

3. **Access your app:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

---

## Troubleshooting

### "Cannot connect to Docker daemon"
```bash
# Make sure Colima is running
colima status

# If not, start it
colima start

# Set the correct Docker context
docker context use colima
```

### Port already in use
```bash
# Find what's using the port (e.g., 3000)
lsof -i :3000

# Kill the process or change the port in docker-compose.yml
```

### Rebuild after dependency changes
```bash
# Rebuild all containers
docker compose build

# Or rebuild specific service
docker compose build backend
```

### Fresh start (delete all data)
```bash
# Stop and remove everything including volumes
docker compose down -v

# Start fresh
docker compose up --build
```

---

## Auto-start Colima on Login (Optional)

If you want Colima to start automatically when you log in:

```bash
brew services start colima
```

To disable auto-start:
```bash
brew services stop colima
```

---

## Useful Docker Commands

```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# View images
docker images

# Remove unused images and containers
docker system prune

# View Docker disk usage
docker system df
```

---

## Notes

- Colima runs a lightweight Linux VM in the background
- Docker containers run inside this VM
- All your `docker` commands work exactly like Docker Desktop
- Colima uses less resources than Docker Desktop
- Less likely to be blocked by enterprise security policies
