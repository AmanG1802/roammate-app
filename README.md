# Roammate Local Development Setup

## Prerequisites
- Docker & Docker Compose
- Node.js 20+
- Python 3.10+

## Local Environment Config
1. **Frontend:** Copy `frontend/.env.example` to `frontend/.env.local`
2. **Backend:** Copy `backend/.env.example` to `backend/.env`

## Running with Docker (Recommended)
```bash
docker-compose up --build
```

## Manual Setup

### Backend (FastAPI)
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
```
