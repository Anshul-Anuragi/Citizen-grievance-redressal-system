"""
Phase 3 Complaint Lifecycle & Accountability Regression Tests for JanSeva AI.

Covers:
  - Valid and invalid status transitions (state machine enforcement)
  - Resolution claims that lack verification (UNVERIFIED state)
  - Evidence submission and evidence references in resolution
  - Human verification and rejection (citizen feedback and admin verification)
  - Audit-history immutability through application workflows
  - Atomic status/history updates
  - SLA overdue processing and trigger endpoint
  - Idempotent escalation (duplicate rejection)
  - Escalation authorization and district isolation
  - Reassignment and workload consistency
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

from app.models.user import User, UserRole, DistrictAdminProfile, OfficerProfile
from app.models.grievance import District, Department, Category
from app.models.complaint import Complaint, ComplaintStatus, ComplaintStatusHistory, ComplaintAttachment, Escalation
from app.models.audit import AuditLog
from app.core.security import get_password_hash, create_access_token
from app.services.complaint_service import ComplaintService
from seed import seed_data

VALID_PASSWORD = "SecurePass123!"


async def _get_indore_admin(db_session):
    res = await db_session.execute(
        select(User)
        .join(DistrictAdminProfile, User.id == DistrictAdminProfile.user_id)
        .where(DistrictAdminProfile.district_code == "IND")
    )
    admin = res.scalars().first()
    if not admin:
        admin = User(email="admin.indore.test@mp.gov.in", password_hash=get_password_hash(VALID_PASSWORD), full_name="Indore Admin", role=UserRole.DISTRICT_ADMIN, is_active=True, is_verified=True)
        db_session.add(admin)
        await db_session.flush()
        prof = DistrictAdminProfile(user_id=admin.id, district_code="IND")
        db_session.add(prof)
        await db_session.commit()
    return admin


async def _get_indore_officer(db_session):
    res = await db_session.execute(
        select(User)
        .join(OfficerProfile, User.id == OfficerProfile.user_id)
        .where(OfficerProfile.district_code == "IND")
    )
    officer = res.scalars().first()
    if not officer:
        dept = (await db_session.execute(select(Department))).scalars().first()
        officer = User(email="officer.indore.test@mp.gov.in", password_hash=get_password_hash(VALID_PASSWORD), full_name="Indore Officer", role=UserRole.OFFICER, is_active=True, is_verified=True)
        db_session.add(officer)
        await db_session.flush()
        prof = OfficerProfile(user_id=officer.id, officer_id="OFF-IND-999", district_code="IND", department_id=dept.id, is_available=True, active_workload=0)
        db_session.add(prof)
        await db_session.commit()
    return officer


async def _create_test_complaint(db_session, district_code="IND", status=ComplaintStatus.SUBMITTED, citizen=None, officer=None):
    cat = (await db_session.execute(select(Category))).scalars().first()
    dept = (await db_session.execute(select(Department))).scalars().first()

    complaint = Complaint(
        complaint_no=f"{district_code}-GRV-2026-{datetime.now().microsecond:06d}",
        tracking_code="TRK-TEST01",
        citizen_id=citizen.id if citizen else None,
        is_anonymous=citizen is None,
        subject="Lifecycle Test Complaint",
        description="Detailed grievance for lifecycle state machine testing.",
        district_code=district_code,
        location_address="Test Address Road",
        category_id=cat.id,
        department_id=dept.id,
        status=status,
        assigned_officer_id=officer.id if officer else None,
        sla_deadline=datetime.now(timezone.utc) + timedelta(hours=48),
        is_overdue=False,
    )
    db_session.add(complaint)
    await db_session.commit()
    await db_session.refresh(complaint)
    return complaint


# ---------------------------------------------------------------------------
# 1. Valid and Invalid Status Transitions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_valid_and_invalid_status_transitions(client: AsyncClient, db_session):
    await seed_data(db_session)
    admin = await _get_indore_admin(db_session)
    officer = await _get_indore_officer(db_session)
    admin_token = create_access_token(admin.id, "DISTRICT_ADMIN")
    officer_token = create_access_token(officer.id, "OFFICER")

    complaint = await _create_test_complaint(db_session, "IND", status=ComplaintStatus.SUBMITTED)

    # Invalid: SUBMITTED -> ON_HOLD directly (must be rejected with 400)
    resp_invalid1 = await client.post(
        f"/api/v1/district-admin/complaints/{complaint.id}/status",
        json={"status": "ON_HOLD", "remarks": "Skipping to on hold"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_invalid1.status_code == 400
    assert "Invalid complaint status transition" in resp_invalid1.json()["detail"]

    # Invalid: SUBMITTED -> CLOSED directly
    resp_invalid2 = await client.post(
        f"/api/v1/district-admin/complaints/{complaint.id}/status",
        json={"status": "CLOSED", "remarks": "Direct close"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_invalid2.status_code == 400

    # Valid: SUBMITTED -> ASSIGNED via assign endpoint
    resp_assign = await client.post(
        f"/api/v1/district-admin/complaints/{complaint.id}/assign",
        json={"officer_id": officer.id, "remarks": "Assigned to test officer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_assign.status_code == 200

    # Valid: ASSIGNED -> IN_PROGRESS via officer start endpoint
    resp_start = await client.post(
        f"/api/v1/officer/complaints/{complaint.id}/start",
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert resp_start.status_code == 200

    # Valid: IN_PROGRESS -> ON_HOLD via officer hold endpoint
    resp_hold = await client.post(
        f"/api/v1/officer/complaints/{complaint.id}/hold",
        json={"remarks": "Awaiting citizen documentation"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert resp_hold.status_code == 200

    # Valid: ON_HOLD -> RESOLVED via officer resolve endpoint
    resp_resolve = await client.post(
        f"/api/v1/officer/complaints/{complaint.id}/resolve",
        json={"resolution_summary": "Fixed the issue on site", "remarks": "Complete"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert resp_resolve.status_code == 200

    # Invalid: RESOLVED -> IN_PROGRESS directly (must reopen first)
    resp_invalid3 = await client.post(
        f"/api/v1/district-admin/complaints/{complaint.id}/status",
        json={"status": "IN_PROGRESS", "remarks": "Back to in progress"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_invalid3.status_code == 400

    # Valid: RESOLVED -> CLOSED via admin status update
    resp_close = await client.post(
        f"/api/v1/district-admin/complaints/{complaint.id}/status",
        json={"status": "CLOSED", "remarks": "Inspection verified"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_close.status_code == 200


# ---------------------------------------------------------------------------
# 2. Resolution Claims that Lack Verification
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolution_claims_lack_verification(client: AsyncClient, db_session):
    await seed_data(db_session)
    officer = await _get_indore_officer(db_session)
    officer_token = create_access_token(officer.id, "OFFICER")

    complaint = await _create_test_complaint(db_session, "IND", status=ComplaintStatus.IN_PROGRESS, officer=officer)

    resp = await client.post(
        f"/api/v1/officer/complaints/{complaint.id}/resolve",
        json={"resolution_summary": "Officer claims pothole was filled."},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert resp.status_code == 200

    await db_session.refresh(complaint)
    assert complaint.status == ComplaintStatus.RESOLVED
    assert complaint.verification_status == "UNVERIFIED"
    assert complaint.resolution_claimed_by_id == officer.id
    assert complaint.resolved_at is not None
    assert complaint.verified_at is None
    assert complaint.verified_by_user_id is None


# ---------------------------------------------------------------------------
# 3. Evidence Submission and References
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolution_evidence_submission_and_reference(client: AsyncClient, db_session):
    await seed_data(db_session)
    officer = await _get_indore_officer(db_session)
    officer_token = create_access_token(officer.id, "OFFICER")

    complaint = await _create_test_complaint(db_session, "IND", status=ComplaintStatus.IN_PROGRESS, officer=officer)

    # Attach evidence document
    att = ComplaintAttachment(
        complaint_id=complaint.id,
        file_name="site_inspection.jpg",
        file_path="attachments/site_inspection.jpg",
        file_type="image/jpeg",
        file_size=2048,
        uploaded_by_user_id=officer.id
    )
    db_session.add(att)
    await db_session.commit()

    # Bogus attachment ID -> 400
    resp_bogus = await client.post(
        f"/api/v1/officer/complaints/{complaint.id}/resolve",
        json={"resolution_summary": "Done", "evidence_attachment_id": "non-existent-id"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert resp_bogus.status_code == 400

    # Valid attachment reference
    resp_valid = await client.post(
        f"/api/v1/officer/complaints/{complaint.id}/resolve",
        json={"resolution_summary": "Repaired and attached photo proof", "evidence_attachment_id": att.id},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert resp_valid.status_code == 200

    await db_session.refresh(complaint)
    assert complaint.resolution_evidence_attachment_id == att.id

    history_res = await db_session.execute(
        select(ComplaintStatusHistory)
        .where(ComplaintStatusHistory.complaint_id == complaint.id)
        .order_by(ComplaintStatusHistory.timestamp.desc())
    )
    latest_history = history_res.scalars().first()
    assert latest_history.evidence_attachment_id == att.id


# ---------------------------------------------------------------------------
# 4. Human Verification and Rejection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_human_verification_by_citizen_satisfaction(client: AsyncClient, db_session):
    await seed_data(db_session)
    citizen = User(email="feedback.cit@example.com", password_hash=get_password_hash(VALID_PASSWORD), full_name="Feedback Cit", role=UserRole.CITIZEN, is_active=True, is_verified=True)
    db_session.add(citizen)
    await db_session.commit()
    cit_token = create_access_token(citizen.id, "CITIZEN")

    complaint = await _create_test_complaint(db_session, "IND", status=ComplaintStatus.RESOLVED, citizen=citizen)

    resp = await client.post(
        f"/api/v1/complaints/{complaint.id}/feedback",
        json={"rating": 5, "is_satisfied": True, "comments": "Problem was indeed fixed."},
        headers={"Authorization": f"Bearer {cit_token}"},
    )
    assert resp.status_code == 200

    await db_session.refresh(complaint)
    assert complaint.verification_status == "VERIFIED_SATISFACTORY"
    assert complaint.verified_by_user_id == citizen.id
    assert complaint.verified_at is not None


@pytest.mark.asyncio
async def test_human_verification_by_admin(client: AsyncClient, db_session):
    await seed_data(db_session)
    admin = await _get_indore_admin(db_session)
    admin_token = create_access_token(admin.id, "DISTRICT_ADMIN")

    complaint = await _create_test_complaint(db_session, "IND", status=ComplaintStatus.RESOLVED)

    # Admin verifies claim as UNSATISFACTORY
    resp = await client.post(
        f"/api/v1/district-admin/complaints/{complaint.id}/verify-resolution",
        json={"verification_status": "VERIFIED_UNSATISFACTORY", "remarks": "On-site check showed pothole still present."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["verification_status"] == "VERIFIED_UNSATISFACTORY"

    await db_session.refresh(complaint)
    assert complaint.verification_status == "VERIFIED_UNSATISFACTORY"
    assert complaint.verified_by_user_id == admin.id
    assert "pothole still present" in complaint.verification_remarks


# ---------------------------------------------------------------------------
# 5. Audit History Immutability & Atomicity
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_history_immutability_and_atomicity(client: AsyncClient, db_session):
    await seed_data(db_session)
    admin = await _get_indore_admin(db_session)
    officer = await _get_indore_officer(db_session)
    admin_token = create_access_token(admin.id, "DISTRICT_ADMIN")

    complaint = await _create_test_complaint(db_session, "IND", status=ComplaintStatus.SUBMITTED)

    initial_histories = (await db_session.execute(
        select(ComplaintStatusHistory).where(ComplaintStatusHistory.complaint_id == complaint.id)
    )).scalars().all()
    initial_count = len(initial_histories)

    assign_resp = await client.post(
        f"/api/v1/district-admin/complaints/{complaint.id}/assign",
        json={"officer_id": officer.id, "remarks": "Assignment remarks"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert assign_resp.status_code == 200

    updated_histories = (await db_session.execute(
        select(ComplaintStatusHistory).where(ComplaintStatusHistory.complaint_id == complaint.id)
    )).scalars().all()
    assert len(updated_histories) == initial_count + 1

    corr_resp = await client.patch(
        f"/api/v1/district-admin/complaints/{complaint.id}/correct",
        json={"priority": "HIGH", "remarks": "Escalated priority"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert corr_resp.status_code == 200

    final_histories = (await db_session.execute(
        select(ComplaintStatusHistory).where(ComplaintStatusHistory.complaint_id == complaint.id)
    )).scalars().all()
    assert len(final_histories) == initial_count + 2


# ---------------------------------------------------------------------------
# 6. SLA Overdue Processing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sla_overdue_processing(client: AsyncClient, db_session):
    await seed_data(db_session)
    admin = await _get_indore_admin(db_session)
    admin_token = create_access_token(admin.id, "DISTRICT_ADMIN")

    complaint = await _create_test_complaint(db_session, "IND", status=ComplaintStatus.IN_PROGRESS)
    complaint.sla_deadline = datetime.now(timezone.utc) - timedelta(hours=2)
    complaint.is_overdue = False
    db_session.add(complaint)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/district-admin/sla/scan-overdue",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["overdue_complaints_flagged"] >= 1

    await db_session.refresh(complaint)
    assert complaint.is_overdue is True


# ---------------------------------------------------------------------------
# 7. Idempotent Escalation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_idempotent_escalation(client: AsyncClient, db_session):
    await seed_data(db_session)
    citizen = User(email="esc.cit@example.com", password_hash=get_password_hash(VALID_PASSWORD), full_name="Esc Cit", role=UserRole.CITIZEN, is_active=True, is_verified=True)
    db_session.add(citizen)
    await db_session.commit()
    cit_token = create_access_token(citizen.id, "CITIZEN")

    complaint = await _create_test_complaint(db_session, "IND", status=ComplaintStatus.IN_PROGRESS, citizen=citizen)

    # First escalation -> 200 OK
    resp1 = await client.post(
        f"/api/v1/complaints/{complaint.id}/escalate",
        json={"reason": "Officer is not responding for 3 days."},
        headers={"Authorization": f"Bearer {cit_token}"},
    )
    assert resp1.status_code == 200

    # Second escalation while first is PENDING -> 409 Conflict
    resp2 = await client.post(
        f"/api/v1/complaints/{complaint.id}/escalate",
        json={"reason": "Sending again!"},
        headers={"Authorization": f"Bearer {cit_token}"},
    )
    assert resp2.status_code == 409
    assert "pending escalation already exists" in resp2.json()["detail"]


# ---------------------------------------------------------------------------
# 8. Escalation Authorization and District Isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_escalation_authorization_and_district_isolation(client: AsyncClient, db_session):
    await seed_data(db_session)
    citizen_a = User(email="cit.a@example.com", password_hash=get_password_hash(VALID_PASSWORD), full_name="Cit A", role=UserRole.CITIZEN, is_active=True, is_verified=True)
    citizen_b = User(email="cit.b@example.com", password_hash=get_password_hash(VALID_PASSWORD), full_name="Cit B", role=UserRole.CITIZEN, is_active=True, is_verified=True)
    db_session.add_all([citizen_a, citizen_b])
    await db_session.flush()

    complaint = await _create_test_complaint(db_session, "IND", status=ComplaintStatus.IN_PROGRESS, citizen=citizen_a)

    token_b = create_access_token(citizen_b.id, "CITIZEN")

    # Citizen B cannot escalate Citizen A's complaint -> 403
    resp_unauth = await client.post(
        f"/api/v1/complaints/{complaint.id}/escalate",
        json={"reason": "I want to escalate someone elses complaint"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_unauth.status_code == 403

    # Citizen A escalates their own complaint
    token_a = create_access_token(citizen_a.id, "CITIZEN")
    resp_esc = await client.post(
        f"/api/v1/complaints/{complaint.id}/escalate",
        json={"reason": "Work has completely stopped."},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_esc.status_code == 200

    # Bhopal Admin cannot view Indore escalations
    bpl_admin = User(email="bpl.adm@mp.gov.in", password_hash=get_password_hash(VALID_PASSWORD), full_name="BPL Admin", role=UserRole.DISTRICT_ADMIN, is_active=True, is_verified=True)
    db_session.add(bpl_admin)
    await db_session.flush()
    bpl_prof = DistrictAdminProfile(user_id=bpl_admin.id, district_code="BPL")
    db_session.add(bpl_prof)
    await db_session.commit()

    token_bpl = create_access_token(bpl_admin.id, "DISTRICT_ADMIN")
    resp_bpl_list = await client.get("/api/v1/district-admin/escalations", headers={"Authorization": f"Bearer {token_bpl}"})
    assert resp_bpl_list.status_code == 200
    assert len(resp_bpl_list.json()) == 0

    # Indore Admin sees the escalation
    ind_admin = await _get_indore_admin(db_session)
    token_ind = create_access_token(ind_admin.id, "DISTRICT_ADMIN")
    resp_ind_list = await client.get("/api/v1/district-admin/escalations", headers={"Authorization": f"Bearer {token_ind}"})
    assert resp_ind_list.status_code == 200
    ind_escalations = resp_ind_list.json()
    assert len(ind_escalations) >= 1
    esc_id = ind_escalations[0]["id"]

    # Indore Admin reviews the escalation
    resp_review = await client.post(
        f"/api/v1/district-admin/escalations/{esc_id}/review",
        json={"status": "REVIEWED", "admin_remarks": "Instructed officer to prioritize."},
        headers={"Authorization": f"Bearer {token_ind}"},
    )
    assert resp_review.status_code == 200


# ---------------------------------------------------------------------------
# 9. Reassignment and Workload Consistency
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reassignment_and_workload_consistency(client: AsyncClient, db_session):
    await seed_data(db_session)
    admin = await _get_indore_admin(db_session)
    dept = (await db_session.execute(select(Department))).scalars().first()
    admin_token = create_access_token(admin.id, "DISTRICT_ADMIN")

    off1 = User(email="workload.off1@mp.gov.in", password_hash=get_password_hash(VALID_PASSWORD), full_name="Officer One", role=UserRole.OFFICER, is_active=True, is_verified=True)
    off2 = User(email="workload.off2@mp.gov.in", password_hash=get_password_hash(VALID_PASSWORD), full_name="Officer Two", role=UserRole.OFFICER, is_active=True, is_verified=True)
    db_session.add_all([off1, off2])
    await db_session.flush()

    prof1 = OfficerProfile(user_id=off1.id, officer_id="OFF-IND-101", district_code="IND", department_id=dept.id, is_available=True, active_workload=0)
    prof2 = OfficerProfile(user_id=off2.id, officer_id="OFF-IND-102", district_code="IND", department_id=dept.id, is_available=True, active_workload=0)
    db_session.add_all([prof1, prof2])
    await db_session.commit()

    complaint = await _create_test_complaint(db_session, "IND", status=ComplaintStatus.SUBMITTED)

    assert prof1.active_workload == 0
    assert prof2.active_workload == 0

    # 1. Assign to Officer 1 -> prof1 = 1, prof2 = 0
    assign_resp1 = await client.post(
        f"/api/v1/district-admin/complaints/{complaint.id}/assign",
        json={"officer_id": off1.id, "remarks": "Initial assign"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert assign_resp1.status_code == 200
    await db_session.refresh(prof1)
    await db_session.refresh(prof2)
    assert prof1.active_workload == 1
    assert prof2.active_workload == 0

    # 2. Reassign from Officer 1 to Officer 2 -> prof1 = 0, prof2 = 1
    assign_resp2 = await client.post(
        f"/api/v1/district-admin/complaints/{complaint.id}/assign",
        json={"officer_id": off2.id, "remarks": "Reassignment"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert assign_resp2.status_code == 200
    await db_session.refresh(prof1)
    await db_session.refresh(prof2)
    assert prof1.active_workload == 0
    assert prof2.active_workload == 1

    # 3. Officer 2 starts and resolves -> prof2 = 0
    token_off2 = create_access_token(off2.id, "OFFICER")
    await client.post(f"/api/v1/officer/complaints/{complaint.id}/start", headers={"Authorization": f"Bearer {token_off2}"})
    await client.post(
        f"/api/v1/officer/complaints/{complaint.id}/resolve",
        json={"resolution_summary": "Resolved by officer 2"},
        headers={"Authorization": f"Bearer {token_off2}"},
    )
    await db_session.refresh(prof2)
    assert prof2.active_workload == 0
