# Digital Grievance Redressal System (Madhya Pradesh Civic Portal)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%2018-61DAFB.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Build-Vite-646CFF.svg)](https://vitejs.dev/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2FSupabase-4169E1.svg)](https://supabase.com/)

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
- **Secure Credential Management**: No hardcoded passwords in version control. Running `python seed.py` generates individual cryptographically secure passwords for all 496 accounts and exports them strictly to `.local/LOCAL_CREDENTIALS.md` (gitignored).
- **Bilingual Interface (i18n)**: Instant English and Hindi UI toggle across public landing page, forms, dashboards, and error messages.

---

## 🔑 Credential Provisioning & Demo Access

For security, plaintext demo credentials are **never hardcoded in source files or public README**.

To generate and retrieve demo credentials locally:
```bash
cd backend
python seed.py
```
This script provisions:
1. **1 Registered Citizen Demo Account** (`citizen@example.com`)
2. **55 District Admin Accounts** (`admin.<district_code_lower>@mp.gov.in`, e.g., `admin.ind@mp.gov.in`, `admin.bho@mp.gov.in`)
3. **440 Department Officer Accounts** (`officer.<district_code_lower>.<dept_code_lower>@mp.gov.in`, e.g., `officer.ind.pwd@mp.gov.in`)

Plaintext generated passwords are saved strictly to your local gitignored file:
`digital-grievance-system/.local/LOCAL_CREDENTIALS.md`

---

## 🛠️ Technology Stack

- **Frontend**: React 18, Vite, React Router v6, Recharts, Lucide Icons, Custom Responsive Civic CSS System, i18n English/Hindi Localization.
- **Backend**: Python 3.10+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async), PyJWT, Bcrypt hashing.
- **Database**: PostgreSQL / Supabase (Production) / SQLite (Local Dev & Pytest).
- **Storage**: Private Storage Service with access-controlled file view proxy.
- **AI**: Gemini API with Keyword Rule Engine Fallback.
- **Email**: Configurable Email Provider Abstraction (Mock / SMTP / Resend).

---

## 📂 Project Structure

```
digital-grievance-system/
├── backend/
│   ├── app/
│   │   ├── api/            # REST API Routes (auth, complaints, district_admin, officers, attachments, ai, analytics, notifications)
│   │   ├── core/           # Security, Permissions, Database Config, Settings
│   │   ├── models/         # SQLAlchemy Models (User, Grievance, Complaint, Notification, AI)
│   │   ├── schemas/        # Pydantic Schemas
│   │   ├── services/       # Business Logic (SLA, Assignment, AI, Email, Storage)
│   │   └── main.py         # FastAPI App Entrypoint & CORS setup
│   ├── scripts/            # Credential Provisioning & Demo Seed Generator
│   ├── tests/              # Pytest Async Test Suite
│   ├── seed.py             # Database Seed Entrypoint
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # Navbar, Footer, Badges, Modals, AI Recommendation Card, Charts
│   │   ├── contexts/       # AuthContext, LanguageContext
│   │   ├── i18n/           # English (en.json) & Hindi (hi.json) Translations
│   │   ├── pages/          # LandingPage, Login, Register, Dashboards, ComplaintDetail
│   │   ├── services/       # Axios API Client
│   │   └── styles/         # Global Civic Styling & Responsive Tokens
│   └── package.json
├── docs/                   # Architecture, DB Schema, API Specs, Deployment & Testing Reports
├── .env.example
└── README.md
```

---

## 🚀 Quick Local Run Instructions

### 1. Backend Setup & Seed
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Seed all 55 MP Districts, Departments, SLA Rules & Accounts
python seed.py

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```
Backend Swagger API Documentation: `http://localhost:8000/api/docs`

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend Web Portal: `http://localhost:5173`

### 3. Run Backend Automated Test Suite
```bash
cd backend
PYTHONPATH=. .venv/bin/pytest tests/
```

### 4. Build Production Frontend
```bash
cd frontend
npm run build
```

---

## 📋 Comprehensive Documentation Links

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Database Schema Specification](docs/DATABASE_SCHEMA.md)
- [API Reference Specs](docs/API_DOCUMENTATION.md)
- [Setup & Deployment Guide](docs/SETUP_AND_DEPLOYMENT.md)
- [Automated Testing Report](docs/TESTING_REPORT.md)

---

## 📜 License & Accreditation
Built for **Government of Madhya Pradesh Civic Governance** / MPOnline Grievance Redressal Standards.
