# API Specifications & Endpoint Reference

FastAPI automatically generates interactive OpenAPI documentation at `/api/docs` and Redoc at `/api/redoc`.

## Base URL
`/api/v1`

## Key API Route Groups

### 1. Authentication (`/auth`)
- `POST /auth/register`: Register new citizen account.
- `POST /auth/login`: Authenticate and receive JWT access token & refresh token.
- `POST /auth/refresh`: Issue new JWT access token using valid refresh token.
- `GET /auth/me`: Retrieve current logged-in user profile.

### 2. Complaints & Lifecycle (`/complaints`)
- `GET /complaints/districts`: Fetch active Madhya Pradesh districts.
- `GET /complaints/categories`: Fetch active grievance categories and department mappings.
- `GET /complaints/departments`: Fetch active public departments.
- `POST /complaints/submit`: Registered citizen grievance submission.
- `POST /complaints/submit-anonymous`: Anonymous citizen grievance submission (returns Complaint ID + Secret Tracking Code + Access Token).
- `POST /complaints/track-anonymous`: Authenticate Complaint ID + Tracking Code for anonymous access token.
- `GET /complaints/my-complaints`: Registered citizen grievance list.
- `GET /complaints/{complaint_id}`: Retrieve detailed grievance, timeline, messages, feedback, attachments.
- `POST /complaints/{complaint_id}/messages`: Post message in communication thread.
- `POST /complaints/{complaint_id}/feedback`: Submit rating & satisfaction feedback.
- `POST /complaints/{complaint_id}/reopen`: Submit reopen request (creates PENDING ReopenRequest for District Admin review).
- `POST /complaints/{complaint_id}/escalate`: Submit escalation to District Admin.

### 3. District Admin Control (`/district-admin`)
- `GET /district-admin/dashboard`: Overview metrics isolated strictly to assigned district.
- `GET /district-admin/complaints`: Search, filter, and sort district grievances.
- `PATCH /district-admin/complaints/{id}/correct`: Correct category, department, priority.
- `POST /district-admin/complaints/{id}/assign`: Assign officer to complaint.
- `GET /district-admin/recommend-officer/{id}`: Workload-based officer recommendation.
- `POST /district-admin/complaints/{id}/status`: Update complaint status (Put on hold, Reject duplicate, Close).
- `GET /district-admin/reopen-requests`: List pending reopen requests for the district.
- `POST /district-admin/reopen-requests/{id}/approve`: Approve reopen request (transitions status to REOPENED).
- `POST /district-admin/reopen-requests/{id}/reject`: Reject reopen request with reason.
- `GET /district-admin/officers` & `POST /district-admin/officers`: Manage district officers.

### 4. Grievance Officer (`/officer`)
- `GET /officer/dashboard`: Officer assigned tasks & workload.
- `GET /officer/assigned-complaints`: Active assigned complaints.
- `POST /officer/complaints/{id}/start`: Mark IN_PROGRESS.
- `POST /officer/complaints/{id}/hold`: Place ON_HOLD with reason.
- `POST /officer/complaints/{id}/resolve`: Mark RESOLVED with summary & resolution date.

### 5. Attachments (`/attachments`)
- `POST /attachments/upload`: Upload supporting attachment file for complaint (images, PDF, MP4, MP3/WAV, max 10MB).
- `GET /attachments/view/{id}`: Securely view/download authorized complaint attachment.

### 6. Analytics (`/analytics`)
- `GET /analytics/public`: Aggregated anonymized metrics for public portal (NO personal identity leaked).
- `GET /analytics/district-admin`: Detailed district operational charts.

### 7. AI Recommendation & Insights (`/ai`)
- `POST /ai/recommend`: Category, department, priority recommendations (Gemini or Rule Engine Fallback).
- `GET /ai/insights`: Strategic district executive summary for District Admin.
