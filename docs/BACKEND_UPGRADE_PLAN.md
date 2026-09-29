# JanSeva AI — Backend Upgrade Plan & Verification Report

> **Application Name:** JanSeva AI (MPOnline Civic Grievance Redressal System)  
> **Backend Architecture:** FastAPI + SQLAlchemy 2.0 (Async) + PostgreSQL 16 (aiosqlite for tests)  
> **Status:** Phase 1 (Complete), Phase 2 (Verified & Complete), Phase 3 (Verified & Complete).  
> **Total Test Suite:** 38 passed / 0 failed (19.43s).

---

## 1. Executive Summary

JanSeva AI is an explainable civic grievance-redressal backend built for the citizens and administration of Madhya Pradesh. 

* **Phase 1 (Audit):** Evaluated 35 backend files across models, routes, services, schemas, and tests, identifying 33 gaps across security, data isolation, lifecycle transitions, and observability.
* **Phase 2 (Security & Hardening):** Implemented Alembic async migrations, production `SECRET_KEY` guards, refresh token logout/revocation (`POST /auth/logout`), `pathlib` traversal defense, password policies, atomic complaint numbering using PostgreSQL advisory locks (`pg_advisory_xact_lock`), and request ID middleware.
* **Phase 3 (Complaint Lifecycle & Accountability):** Implemented a deterministic status transition state machine, separated officer resolution claims from independent verification outcomes, added evidence tracking to timeline events, introduced decoupled background SLA overdue scanning, made escalations idempotent, and provided administrative escalation and resolution verification endpoints.

---

## 2. Phase 3 Architecture: Lifecycle, Accountability & Verification

### 2.1 Controlled Complaint Lifecycle State Machine

Status transitions are governed by `ComplaintService.transition_complaint_status()`. Endpoints can no longer bypass lifecycle validation.

```
+-------------+
|  SUBMITTED  |
+------+------+
       |
       +---> RECEIVED (Admin accepts/reviews)
       |
       +---> ASSIGNED (Admin assigns officer)
       |
       +---> REJECTED (Admin rejects invalid complaint)

+-------------+
|  RECEIVED   |
+------+------+
       |
       +---> ASSIGNED (Admin assigns officer)
       |
       +---> REJECTED

+-------------+
|  ASSIGNED   |
+------+------+
       |
       +---> IN_PROGRESS (Officer begins resolution work)
       |
       +---> ASSIGNED (Admin reassigns to another officer)
       |
       +---> REJECTED

+-------------+
| IN_PROGRESS |
+------+------+
       |
       +---> ON_HOLD (Officer requires citizen input/delay; mandatory remarks)
       |
       +---> RESOLVED (Officer submits resolution claim; status = RESOLVED, UNVERIFIED)
       |
       +---> ASSIGNED (Admin reassigns)

+-------------+
|   ON_HOLD   |
+------+------+
       |
       +---> IN_PROGRESS (Officer resumes work)
       |
       +---> RESOLVED (Officer submits resolution claim)
       |
       +---> ASSIGNED (Admin reassigns)

+-------------+
|  RESOLVED   | (Initial claim state: UNVERIFIED)
+------+------+
       |
       +---> CLOSED (Verified satisfactory by citizen feedback OR admin closure)
       |
       +---> REOPENED (Citizen requests reopen; Admin reviews and approves)

+-------------+
|  REOPENED   |
+------+------+
       |
       +---> ASSIGNED (Reassigned to officer)
       |
       +---> IN_PROGRESS (Officer resumes work)

+-------------+
|   CLOSED    | (Terminal state; reopen only via formal administrative review)
+------+------+
       |
       +---> REOPENED (Admin approves formal reopen request)

+-------------+
|  REJECTED   | (Terminal state; reconsider only via formal administrative review)
+------+------+
       |
       +---> REOPENED (Admin approves appeal/reconsideration)
```

Attempting any transition outside this matrix raises an `HTTP 400 Bad Request` with an explicit diagnostic message (`"Invalid complaint status transition from X to Y"`).

---

### 2.2 Resolution Claims vs. Verified Outcomes

A critical requirement of Phase 3 is that an officer marking a complaint as resolved **does not automatically mean the issue is independently verified as resolved**.

1. **Resolution Claim Submission (`POST /officer/complaints/{id}/resolve`):**
   * Performed by the assigned officer.
   * Requires `resolution_summary`. Accepts optional `remarks` and `evidence_attachment_id`.
   * Sets:
     * `complaint.status = ComplaintStatus.RESOLVED`
     * `complaint.resolution_claimed_by_id = current_user.id`
     * `complaint.resolution_evidence_attachment_id = evidence_id`
     * `complaint.verification_status = "UNVERIFIED"`
     * `complaint.resolved_at = datetime.now(timezone.utc)`
   * Decrements officer's active workload.
   * The presence of uploaded evidence or an officer's statement is treated solely as a **claim**, not proof of resolution.

2. **Citizen Independent Verification (`POST /complaints/{id}/feedback`):**
   * Citizen provides rating (1–5), comments, and boolean `is_satisfied`.
   * If `is_satisfied == True`: sets `complaint.verification_status = "VERIFIED_SATISFACTORY"`.
   * If `is_satisfied == False`: sets `complaint.verification_status = "VERIFIED_UNSATISFACTORY"`.
   * Sets `verified_by_user_id` and `verified_at`.

3. **District Admin Independent Verification (`POST /district-admin/complaints/{id}/verify-resolution`):**
   * District Admin inspects the claim, evidence, or citizen reports.
   * Can set `verification_status` to `"VERIFIED_SATISFACTORY"` or `"VERIFIED_UNSATISFACTORY"` with administrative remarks.
   * Preserves human decision-making: AI never makes final administrative closure decisions.

4. **Complaint Closure (`POST /district-admin/complaints/{id}/status` to `CLOSED`):**
   * When closing a complaint, if `verification_status` was still `"UNVERIFIED"`, the admin's explicit closure sets `verification_status = "VERIFIED_SATISFACTORY"` with administrative closure remarks.

---

### 2.3 Audit History & Accountability

* Every status transition, assignment, correction, and escalation records an entry in `ComplaintStatusHistory` and `AuditLog`.
* **Evidence References:** `ComplaintStatusHistory` records `evidence_attachment_id` whenever evidence is attached to a transition.
* **Append-Only History:** Application APIs provide no endpoints to modify or delete timeline history or audit logs.
* **Transaction Atomicity:** Complaint updates, officer workload adjustments, status history, and audit log rows are committed in the same database transaction.

---

### 2.4 SLA & Escalation Workflow

* **Decoupled SLA Scanner:** Overdue calculation is no longer tied to dashboard page loads. An asynchronous background task (`_periodic_sla_overdue_scanner`) runs inside FastAPI's lifespan event loop, periodically updating overdue flags and appending system audit events (`actor_role="SYSTEM"`).
* **On-Demand Admin SLA Scan:** `POST /api/v1/district-admin/sla/scan-overdue` allows admins to trigger immediate overdue checks for their district.
* **Idempotent Escalations:** `POST /api/v1/complaints/{id}/escalate` rejects duplicate pending escalations for the same complaint with `HTTP 409 Conflict`.
* **District Admin Escalation Management:**
  * `GET /api/v1/district-admin/escalations`: Lists escalations strictly isolated to the admin's district.
  * `POST /api/v1/district-admin/escalations/{id}/review`: Allows admins to review and set escalation status to `REVIEWED` or `DISMISSED` with mandatory remarks.
* **Workload Counter Consistency:** Reassignment decrements the previous officer's `active_workload` (with a floor of 0) and increments the new officer's `active_workload` atomically.

---

## 3. Database Migrations (Alembic)

* **Migration 1 (Baseline):** `alembic/versions/78f480187bc2_initial_schema_baseline.py`
  * Defines all 23 initial tables.
* **Migration 2 (Phase 3 Lifecycle):** `alembic/versions/c385ad786ce6_phase3_complaint_lifecycle_and_.py`
  * Adds `resolution_claimed_by_id`, `resolution_evidence_attachment_id`, `verification_status`, `verified_by_user_id`, `verified_at`, `verification_remarks` to `complaints`.
  * Adds `evidence_attachment_id` to `complaint_status_history`.
  * Adds `reviewed_by_user_id`, `reviewed_at` to `escalations`.
  * Fully tested on live PostgreSQL 16 container (`janseva-ai-postgres` on port 5434) for both upgrade and downgrade.

---

## 4. Test Suite Execution Results

Full test run on host (Python 3.14.7, pytest 9.1.1, aiosqlite):

```
collected 38 items

tests/test_ai_fallback.py::test_ai_keyword_rule_fallback_when_unconfigured PASSED [  2%]
tests/test_anonymous_tracking.py::test_anonymous_submission_and_tracking PASSED [  5%]
tests/test_anonymous_tracking.py::test_anonymous_submission_with_empty_email PASSED [  7%]
tests/test_auth.py::test_register_and_login_citizen PASSED               [ 10%]
tests/test_complaint_access.py::test_anonymous_complaint_requires_tracking_session PASSED [ 13%]
tests/test_complaint_access.py::test_ai_preview_does_not_require_a_persisted_complaint PASSED [ 15%]
tests/test_district_isolation.py::test_district_isolation_enforcement PASSED [ 18%]
tests/test_phase2_security.py::test_logout_revokes_refresh_token PASSED  [ 21%]
tests/test_phase2_security.py::test_logout_with_nonexistent_or_invalid_token PASSED [ 23%]
tests/test_phase2_security.py::test_access_token_still_valid_after_logout_until_expiry PASSED [ 26%]
tests/test_phase2_security.py::test_full_session_logout_revokes_all_tokens PASSED [ 28%]
tests/test_phase2_security.py::test_register_rejects_weak_passwords PASSED [ 31%]
tests/test_phase2_security.py::test_officer_create_rejects_weak_password PASSED [ 34%]
tests/test_phase2_security.py::test_submit_complaint_description_length_boundary PASSED [ 36%]
tests/test_phase2_security.py::test_citizen_cannot_view_another_citizens_complaint PASSED [ 39%]
tests/test_phase2_security.py::test_cross_district_admin_cannot_view_other_district_complaint PASSED [ 42%]
tests/test_phase2_security.py::test_unauthorized_attachment_access PASSED [ 44%]
tests/test_phase2_security.py::test_path_traversal_rejected_by_storage_service PASSED [ 47%]
tests/test_phase2_security.py::test_production_secret_key_guard_raises_on_insecure_default PASSED [ 50%]
tests/test_phase2_security.py::test_production_secret_key_guard_raises_on_short_key PASSED [ 52%]
tests/test_phase2_security.py::test_production_secret_key_guard_accepts_strong_key PASSED [ 55%]
tests/test_phase2_security.py::test_development_environment_permits_default_key PASSED [ 57%]
tests/test_phase2_security.py::test_x_request_id_middleware PASSED       [ 60%]
tests/test_phase2_security.py::test_health_endpoint_checks_database PASSED [ 63%]
tests/test_phase2_security.py::test_registered_complaint_atomicity PASSED [ 65%]
tests/test_phase2_security.py::test_anonymous_complaint_atomicity PASSED [ 68%]
tests/test_phase3_lifecycle.py::test_valid_and_invalid_status_transitions PASSED [ 71%]
tests/test_phase3_lifecycle.py::test_resolution_claims_lack_verification PASSED [ 73%]
tests/test_phase3_lifecycle.py::test_resolution_evidence_submission_and_reference PASSED [ 76%]
tests/test_phase3_lifecycle.py::test_human_verification_by_citizen_satisfaction PASSED [ 78%]
tests/test_phase3_lifecycle.py::test_human_verification_by_admin PASSED  [ 81%]
tests/test_phase3_lifecycle.py::test_audit_history_immutability_and_atomicity PASSED [ 84%]
tests/test_phase3_lifecycle.py::test_sla_overdue_processing PASSED       [ 86%]
tests/test_phase3_lifecycle.py::test_idempotent_escalation PASSED        [ 89%]
tests/test_phase3_lifecycle.py::test_escalation_authorization_and_district_isolation PASSED [ 92%]
tests/test_phase3_lifecycle.py::test_reassignment_and_workload_consistency PASSED [ 94%]
tests/test_reopen_workflow.py::test_reopen_workflow PASSED               [ 97%]
tests/test_workload_and_assignment.py::test_workload_and_assignment PASSED [100%]

======================= 38 passed, 33 warnings in 19.43s =======================
```

---

## 5. Files Created or Modified (Phase 3)

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/models/complaint.py` | Modified | Added resolution claim, verification fields, evidence attachment in status history, and review fields in Escalation. |
| `backend/app/schemas/complaint.py` | Modified | Added `ResolutionVerificationRequest`, `EscalationAdminResponse`, `EscalationReviewRequest`, and resolution fields. |
| `backend/app/services/complaint_service.py` | Modified | Added `PERMITTED_TRANSITIONS` state machine, `transition_complaint_status`, and system audit trail for overdue scanner. |
| `backend/app/api/officers.py` | Modified | Integrated lifecycle validation in `/start`, `/hold`, `/resolve`, and recorded resolution claims as UNVERIFIED with evidence references. |
| `backend/app/api/complaints.py` | Modified | Updated `/feedback` to set verification status and made `/escalate` idempotent against duplicate pending escalations. |
| `backend/app/api/district_admin.py` | Modified | Added `/verify-resolution`, `/escalations`, `/escalations/{id}/review`, `/sla/scan-overdue`, and enforced lifecycle transitions on assign and status updates. |
| `backend/app/main.py` | Modified | Added decoupled periodic background SLA scanner in FastAPI lifespan. |
| `backend/alembic/versions/c385ad786ce6_phase3_complaint_lifecycle_and_.py` | Created | Database migration for Phase 3 schema extensions. |
| `backend/tests/test_phase3_lifecycle.py` | Created | 10 comprehensive tests covering all Phase 3 lifecycle and accountability requirements. |
| `docs/BACKEND_UPGRADE_PLAN.md` | Modified | Updated upgrade plan and verification report. |

---

## 6. Known Limitations & Next Steps

* **Phase 4 Scope (Explainable AI & Human-in-the-Loop Redressal):** AI assistance is currently limited to category/priority suggestions and fallback keyword rules. Phase 4 will introduce explainable audit logs for AI recommendations and human review queues for low-confidence classifications.
* **Phase 5 Scope (Observability & Production Polish):** Redis-based token revocation list (`jti`), rate limiting middleware, multilingual complaint translation, and metrics endpoints.

**Phase 3 is complete and verified. Awaiting user review and approval before beginning Phase 4.**
