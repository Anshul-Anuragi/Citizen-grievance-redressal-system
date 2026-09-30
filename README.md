# Digital Grievance Redressal System (Madhya Pradesh Civic Portal)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2016-000000.svg)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/Language-TypeScript-3178C6.svg)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2FNeon-4169E1.svg)](https://neon.tech/)

A complete, production-grade civic grievance redressal portal built for the **Government of Madhya Pradesh** and integrated with **MPOnline** governance workflows.

The application provides transparent, time-bound, SLA-monitored grievance redressal for citizens across all **55 districts of Madhya Pradesh**, with strict district data isolation, dynamic category-to-department routing, structured citizen-officer communication, District Admin reopen approval workflows, supporting document attachments, optional Gemini AI recommendation & executive insight layer, and bilingual support (English + Hindi).

---

## 🏛️ System Features & Key Highlights

- **User Roles & Authorization**:
  - **Registered Citizen**: Registration, Login with JWT access/refresh token rotation, Password Reset, Dashboard, Grievance Submission, Attachment Upload, SLA Countdown, Structured Communication, Resolution Feedback & Reopen Requests.
  - **Anonymous Citizen**: Submit grievances without creating an account. Generates Complaint ID + Secret Tracking Code + Secure Session Access Token. Citizen identity is never exposed unnecessarily.
  - **District Admin**: Highest operational administrative role per district. Manage district complaints, assign/reassign officers, review and approve/reject reopen requests, set status, monitor SLAs, and manage grievance officers. Isolated strictly to their assigned district.
  - **Grievance Officer**: Work on assigned grievances within their department and district. Move complaints to `IN_PROGRESS`, place `ON_HOLD`, communicate with citizens, and mark `RESOLVED` with resolution details.

- **55 Madhya Pradesh Districts & 440 Department Officer Accounts**: Authoritative database seeding provisions District Admin accounts for all 55 MP districts and 440 officer accounts (55 districts × 8 departments).
- **Strict District Data Isolation**: District Admins and Grievance Officers can ONLY query, manage, and view data belonging to their assigned district. Cross-district data queries return HTTP 403 Forbidden on the backend.
- **Dynamic Category → Department SLA Routing**: Database-driven category mapping. Priority (`HIGH`: 0.5x, `MEDIUM`: 1.0x, `LOW`: 1.5x) dynamically calculates the SLA deadline.
- **Workload-Based Officer Assignment**: System auto-recommends eligible officers based on matching department, same district, active availability status, and lowest active workload.
- **Strict Reopen Workflow**: Reopening a `RESOLVED` or `CLOSED` complaint requires a citizen to submit a `ReopenRequest`. Only District Admin approval transitions the complaint to `REOPENED` and restores officer workload.
- **Attachment Workflow**: Multi-format supporting document uploads (Images, PDF, MP4, MP3/WAV) with file size validation (max 10MB) and secure access controls.
- **Optional Gemini AI Layer**: Uses Gemini API for smart category/priority recommendations and executive district insights. IF GEMINI IS UNAVAILABLE OR UNCONFIGURED, THE SYSTEM AUTOMATICALLY FALLS BACK TO A KEYWORD RULE ENGINE WITHOUT BREAKING CORE FUNCTIONALITY.
- **Secure Credential Management**: No hardcoded passwords in version control. Safe seeding with environment variables.
- **Bilingual Interface (i18n)**: Instant English and Hindi UI toggle across public landing page, forms, dashboards, and error messages.

---

## 🛠️ Technology Stack

- **Frontend**: Next.js 16 (App Router), React 19, TypeScript, Lucide Icons, Custom Responsive Civic CSS System, Zero-Flicker Sticky Header, Bilingual English/Hindi Localization.
- **Backend**: Python 3.10+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async), PyJWT, Bcrypt hashing, SlowAPI Rate Limiting.
- **Database**: PostgreSQL / Neon Serverless (Production) / SQLite (Local Dev & Pytest) with least-privilege role separation (`janseva_app` vs `janseva_migrator`) and immutable audit log triggers.
- **Storage**: Pluggable Attachment Storage (Local filesystem or Supabase Storage).
- **Messaging**: Pluggable Notification Service (Mock, SMTP, Resend).
- **AI**: Gemini API with keyword-based rule engine fallback.

---

## 🚀 Quick Local Run Instructions

### 1. Backend Setup
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```
Backend Swagger API Documentation: `http://localhost:8000/docs`

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend Web Portal: `http://localhost:3000`

### 3. Run Backend Automated Test Suite
```bash
cd backend
pytest tests/
```

### 4. Build Production Frontend
```bash
cd frontend
npm run build
```

---

## 📋 Comprehensive Documentation Links

- [Setup & Configuration](docs/SETUP.md)
- [API Reference Specs](docs/API.md)
- [Database Schema & Hardening](docs/DATABASE.md)
- [Security & Least-Privilege Architecture](docs/SECURITY.md)
- [Explainable AI & Fallbacks](docs/AI.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Interactive Demo Guide](docs/DEMO.md)
- [Future Roadmap](docs/FUTURE_ROADMAP.md)

---

## 📜 License & Accreditation
Built for **Government of Madhya Pradesh Civic Governance** / MPOnline Grievance Redressal Standards.
