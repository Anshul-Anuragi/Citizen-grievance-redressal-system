# System Architecture - Digital Grievance Redressal System

## Executive Overview
The **Digital Grievance Redressal System** is an MPOnline / Madhya Pradesh government-style civic grievance portal designed to provide transparent, time-bound, SLA-monitored grievance resolution across all 55 districts of MP.

## System Topology & Layers

```
[ Citizen (Web / Mobile) ] <---> [ Vercel React Vite Frontend (i18n En/Hi) ]
                                            │
                                            ▼ REST JSON APIs + JWT
                                [ Render / Railway FastAPI Backend ]
                                            │
           ┌────────────────────────────────┼──────────────────────────────┐
           ▼                                ▼                              ▼
[ PostgreSQL / Supabase DB ]     [ Private Storage Service ]    [ Gemini AI Layer (Optional) ]
(Tables, Isolation, SLA)        (Uploads, Signed View Proxy)   (Smart Category & Admin Insights)
```

## Security & Access Control Architecture

1. **Role-Based Access Control (RBAC)**:
   - `CITIZEN`: Submit registered grievances, view timeline, send messages, rate resolution.
   - `ANONYMOUS`: Submit anonymous complaints with Complaint ID + Tracking Code token session.
   - `DISTRICT_ADMIN`: Highest operational administrative role; isolated data control over assigned district, officer management, category/department correction, workload assignment, SLA monitoring.
   - `OFFICER`: Process assigned tasks, update progress, request information, mark resolved with summary.

2. **Strict District Data Isolation**:
   - Every database query for District Admins and Grievance Officers automatically enforces a `district_code` filter.
   - Admins or Officers attempting cross-district data modification receive an immediate HTTP 403 Forbidden.

3. **Security Token Hashing**:
   - Secrets are never stored in plaintext. `refresh_tokens`, `email_verification_tokens`, `password_reset_tokens`, `anonymous_access_sessions`, and anonymous admin report tokens store SHA-256 cryptographic hashes (`token_hash`) with expiration timestamps.

4. **SLA Calculation Engine**:
   - Deadline = `Category Default SLA Hours * Priority Multiplier` (HIGH: 0.5x, MEDIUM: 1.0x, LOW: 1.5x).
   - Automated overdue detection flags expired active complaints.

5. **Gemini AI & Fallback Architecture**:
   - AI functions as an optional recommendation layer.
   - If `GEMINI_API_KEY` is unavailable or fails, system invokes a keyword rule engine.
   - AI recommendations are stored separately in `ai_recommendations` table and do NOT alter administrative status without human approval.
