# Setup & Deployment Instructions

## Local Development Setup

### 1. Prerequisites
- Python 3.10+
- Node.js v18+ & npm

### 2. Backend Setup
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install email-validator

# Run database migration & seed
python seed.py

# Start FastAPI development server
uvicorn app.main:app --reload --port 8000
```
Backend API will be accessible at `http://localhost:8000/api/docs`.

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend web portal will be accessible at `http://localhost:5173`.

---

## Production Deployment Guide

### 1. Frontend Deployment (Vercel)
- Framework Preset: **Vite**
- Build Command: `npm run build`
- Output Directory: `dist`
- Environment Variables:
  - `VITE_API_BASE_URL`: `https://your-backend-api.onrender.com/api/v1`

### 2. Backend Deployment (Render / Railway)
- Environment: Python 3.10+
- Build Command: `pip install -r requirements.txt && pip install email-validator`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Environment Variables:
  - `DATABASE_URL`: `postgresql+asyncpg://postgres:password@db.supabase.co:5432/postgres`
  - `SECRET_KEY`: `<production-random-secret>`
  - `GEMINI_API_KEY`: `<optional-gemini-api-key>`
  - `BACKEND_CORS_ORIGINS`: `["https://your-app.vercel.app"]`

### 3. Database & Storage Deployment (Supabase)
- PostgreSQL Database & Storage Bucket creation in Supabase console.
- Run `python seed.py` pointing `DATABASE_URL` to Supabase PostgreSQL connection string.
