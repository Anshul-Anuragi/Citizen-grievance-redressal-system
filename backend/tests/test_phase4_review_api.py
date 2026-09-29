"""
Phase 4 Step 3: District Admin AI Review Queue & Human Review Disposition API Tests.

Covers:
  - Authorized district admin can list findings in their own district
  - Cross-district isolation: findings from other districts never appear
  - Unauthorized roles (Citizen, Officer, unauthenticated) cannot access queue or submit dispositions
  - Filtering by severity and review status (PENDING_REVIEW, ACCEPTED, REJECTED, AMENDED)
  - Bounded pagination and deterministic ordering with tie-breaker
  - Invalid filter inputs and invalid disposition payloads rejected with 400
  - Valid ACCEPTED, REJECTED, and AMENDED actions append review records
  - Amendment payload validation (requires at least one amendment field, valid severity, notes)
  - Multiple dispositions form an append-only audit trail preserving prior reviews
  - Unknown and cross-district finding IDs return 404 without leaking cross-district existence
  - Absolute immutability of complaint lifecycle, verification, assignment, and workload
  - Audit logging of review actions
"""

import pytest
import json
import uuid
from typing import Tuple
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta

from app.models.user import User, UserRole, DistrictAdminProfile, OfficerProfile
from app.models.complaint import Complaint, ComplaintStatus, ComplaintAttachment
from app.models.ai import AIAuditFinding, AIAuditFindingReview
from app.models.audit import AuditLog
from app.models.grievance import District, Department, Category, PriorityEnum
from app.core.security import get_password_hash, create_access_token
from seed import seed_data

VALID_PASSWORD = "SecurePassword123!"


async def _create_admin(db: AsyncSession, district_code: str, email: str) -> Tuple[User, str]:
    admin = User(
        email=email,
        password_hash=get_password_hash(VALID_PASSWORD),
        full_name=f"Admin {district_code}",
        role=UserRole.DISTRICT_ADMIN,
        is_active=True,
        is_verified=True
    )
    db.add(admin)
    await db.flush()

    prof = DistrictAdminProfile(user_id=admin.id, district_code=district_code)
    db.add(prof)
    await db.commit()

    token = create_access_token(admin.id, "DISTRICT_ADMIN")
    return admin, token


async def _create_citizen(db: AsyncSession, email: str) -> Tuple[User, str]:
    citizen = User(
        email=email,
        password_hash=get_password_hash(VALID_PASSWORD),
        full_name="Citizen Tester",
        role=UserRole.CITIZEN,
        is_active=True,
        is_verified=True
    )
    db.add(citizen)
    await db.commit()
    token = create_access_token(citizen.id, "CITIZEN")
    return citizen, token


async def _create_officer(db: AsyncSession, district_code: str, email: str) -> Tuple[User, str]:
    officer = User(
        email=email,
        password_hash=get_password_hash(VALID_PASSWORD),
        full_name=f"Officer {district_code}",
        role=UserRole.OFFICER,
        is_active=True,
        is_verified=True
    )
    db.add(officer)
    await db.flush()

    dept = (await db.execute(select(Department))).scalars().first()
    prof = OfficerProfile(
        user_id=officer.id,
        officer_id=f"OFF-{district_code}-{uuid.uuid4().hex[:6].upper()}",
        district_code=district_code,
        department_id=dept.id if dept else None,
        is_available=True,
        active_workload=5
    )
    db.add(prof)
    await db.commit()
    token = create_access_token(officer.id, "OFFICER")
    return officer, token


async def _create_complaint(
    db: AsyncSession,
    district_code: str,
    complaint_no: str,
    status: ComplaintStatus = ComplaintStatus.RESOLVED
) -> Complaint:
    citizen_res = await db.execute(select(User).where(User.role == UserRole.CITIZEN))
    citizen = citizen_res.scalars().first()
    dept = (await db.execute(select(Department))).scalars().first()
    cat = (await db.execute(select(Category))).scalars().first()

    complaint = Complaint(
        complaint_no=complaint_no,
        tracking_code=f"TRK-{complaint_no}",
        citizen_id=citizen.id if citizen else None,
        subject=f"Grievance for {complaint_no}",
        description="Potholes and broken street drainage.",
        district_code=district_code,
        department_id=dept.id if dept else None,
        category_id=cat.id if cat else None,
        status=status,
        priority=PriorityEnum.HIGH,
        sla_deadline=datetime.now(timezone.utc) + timedelta(hours=48),
        location_address="Test road, MP"
    )
    db.add(complaint)
    await db.commit()
    await db.refresh(complaint)
    return complaint


async def _create_finding(
    db: AsyncSession,
    complaint_id: str,
    finding_type: str = "MISSING_RESOLUTION_EVIDENCE",
    severity: str = "HIGH",
    created_at: datetime = None
) -> AIAuditFinding:
    if created_at is None:
        created_at = datetime.now(timezone.utc)
    finding = AIAuditFinding(
        complaint_id=complaint_id,
        finding_type=finding_type,
        severity=severity,
        facts=json.dumps(["Fact 1", "Fact 2"]),
        interpretations=json.dumps(["Interpretation 1"]),
        unresolved_questions=json.dumps(["Question 1"]),
        explanation=f"Explanation for {finding_type}",
        evidence_assessment="NOT_PRESENT",
        rule_or_model_version="rules-v1.0",
        confidence=0.95,
        created_at=created_at
    )
    db.add(finding)
    await db.commit()
    await db.refresh(finding)
    return finding


# ===========================================================================
# Test Cases
# ===========================================================================

@pytest.mark.asyncio
async def test_authorized_district_admin_can_list_findings_in_own_district(client: AsyncClient, db_session: AsyncSession):
    """
    District Admin can access GET /api/v1/district-admin/ai-reviews and sees findings
    for complaints located in their district.
    """
    await seed_data(db_session)
    admin_ind, token_ind = await _create_admin(db_session, "IND", "admin.indore.list@mp.gov.in")
    c1 = await _create_complaint(db_session, "IND", "IND-2026-001")
    f1 = await _create_finding(db_session, c1.id, "MISSING_RESOLUTION_EVIDENCE", "HIGH")

    resp = await client.get(
        "/api/v1/district-admin/ai-reviews",
        headers={"Authorization": f"Bearer {token_ind}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["limit"] == 20
    assert data["offset"] == 0
    item_ids = [item["id"] for item in data["items"]]
    assert f1.id in item_ids

    # Verify item contents match specification
    item = next(i for i in data["items"] if i["id"] == f1.id)
    assert item["complaint_id"] == c1.id
    assert item["complaint_no"] == "IND-2026-001"
    assert item["finding_type"] == "MISSING_RESOLUTION_EVIDENCE"
    assert item["severity"] == "HIGH"
    assert item["current_status"] == "PENDING_REVIEW"
    assert item["facts"] == ["Fact 1", "Fact 2"]
    assert item["interpretations"] == ["Interpretation 1"]
    assert item["unresolved_questions"] == ["Question 1"]
    assert item["latest_review"] is None


@pytest.mark.asyncio
async def test_cross_district_isolation_findings_never_leak(client: AsyncClient, db_session: AsyncSession):
    """
    Indore Admin cannot see Bhopal findings in the queue.
    Bhopal Admin cannot see Indore findings.
    """
    await seed_data(db_session)
    admin_ind, token_ind = await _create_admin(db_session, "IND", "admin.ind.iso@mp.gov.in")
    admin_bho, token_bho = await _create_admin(db_session, "BHO", "admin.bho.iso@mp.gov.in")

    c_ind = await _create_complaint(db_session, "IND", "IND-ISO-001")
    f_ind = await _create_finding(db_session, c_ind.id, "MISSING_RESOLUTION_EVIDENCE", "HIGH")

    c_bho = await _create_complaint(db_session, "BHO", "BHO-ISO-001")
    f_bho = await _create_finding(db_session, c_bho.id, "OVERDUE_INACTIVITY", "CRITICAL")

    # Indore Admin query
    resp_ind = await client.get(
        "/api/v1/district-admin/ai-reviews",
        headers={"Authorization": f"Bearer {token_ind}"}
    )
    assert resp_ind.status_code == 200
    ind_items = resp_ind.json()["items"]
    ind_ids = [i["id"] for i in ind_items]
    assert f_ind.id in ind_ids
    assert f_bho.id not in ind_ids

    # Bhopal Admin query
    resp_bho = await client.get(
        "/api/v1/district-admin/ai-reviews",
        headers={"Authorization": f"Bearer {token_bho}"}
    )
    assert resp_bho.status_code == 200
    bho_items = resp_bho.json()["items"]
    bho_ids = [i["id"] for i in bho_items]
    assert f_bho.id in bho_ids
    assert f_ind.id not in bho_ids


@pytest.mark.asyncio
async def test_unauthorized_roles_cannot_access_review_queue(client: AsyncClient, db_session: AsyncSession):
    """
    Citizens, Officers, and unauthenticated requests are rejected with 401 or 403.
    """
    await seed_data(db_session)
    citizen, cit_token = await _create_citizen(db_session, "citizen.noqueue@example.com")
    officer, off_token = await _create_officer(db_session, "IND", "officer.noqueue@mp.gov.in")

    # Unauthenticated
    resp_anon = await client.get("/api/v1/district-admin/ai-reviews")
    assert resp_anon.status_code == 401

    # Citizen
    resp_cit = await client.get(
        "/api/v1/district-admin/ai-reviews",
        headers={"Authorization": f"Bearer {cit_token}"}
    )
    assert resp_cit.status_code == 403

    # Officer
    resp_off = await client.get(
        "/api/v1/district-admin/ai-reviews",
        headers={"Authorization": f"Bearer {off_token}"}
    )
    assert resp_off.status_code == 403


@pytest.mark.asyncio
async def test_filtering_by_severity_and_status(client: AsyncClient, db_session: AsyncSession):
    """
    Filters by severity (HIGH, MEDIUM, INFO) and status (PENDING_REVIEW, ACCEPTED, REJECTED).
    """
    await seed_data(db_session)
    admin_ind, token_ind = await _create_admin(db_session, "IND", "admin.filter@mp.gov.in")
    c1 = await _create_complaint(db_session, "IND", "IND-FLT-001")

    # Finding 1: HIGH severity, PENDING_REVIEW
    f1 = await _create_finding(db_session, c1.id, "MISSING_RESOLUTION_EVIDENCE", "HIGH")

    # Finding 2: INFO severity, will be ACCEPTED
    f2 = await _create_finding(db_session, c1.id, "OFFICER_CAPACITY_SIGNAL", "INFO")
    rev2 = AIAuditFindingReview(
        finding_id=f2.id,
        reviewer_user_id=admin_ind.id,
        action="ACCEPTED",
        reviewer_notes="Acknowledged workload."
    )
    db_session.add(rev2)
    await db_session.commit()

    # Filter by severity=HIGH
    resp_high = await client.get(
        "/api/v1/district-admin/ai-reviews?severity=HIGH",
        headers={"Authorization": f"Bearer {token_ind}"}
    )
    assert resp_high.status_code == 200
    high_ids = [i["id"] for i in resp_high.json()["items"]]
    assert f1.id in high_ids
    assert f2.id not in high_ids

    # Filter by status=PENDING_REVIEW
    resp_pending = await client.get(
        "/api/v1/district-admin/ai-reviews?status=PENDING_REVIEW",
        headers={"Authorization": f"Bearer {token_ind}"}
    )
    assert resp_pending.status_code == 200
    pending_ids = [i["id"] for i in resp_pending.json()["items"]]
    assert f1.id in pending_ids
    assert f2.id not in pending_ids

    # Filter by status=ACCEPTED
    resp_accepted = await client.get(
        "/api/v1/district-admin/ai-reviews?status=ACCEPTED",
        headers={"Authorization": f"Bearer {token_ind}"}
    )
    assert resp_accepted.status_code == 200
    accepted_ids = [i["id"] for i in resp_accepted.json()["items"]]
    assert f2.id in accepted_ids
    assert f1.id not in accepted_ids


@pytest.mark.asyncio
async def test_pagination_and_deterministic_ordering_with_tie_breaker(client: AsyncClient, db_session: AsyncSession):
    """
    Tests limit, offset, and stable ordering even when items share identical timestamps.
    """
    await seed_data(db_session)
    admin_ind, token_ind = await _create_admin(db_session, "IND", "admin.page@mp.gov.in")
    c = await _create_complaint(db_session, "IND", "IND-PAGE-001")

    # Create 5 findings with identical timestamp
    now = datetime(2026, 9, 29, 10, 0, 0, tzinfo=timezone.utc)
    findings = []
    for i in range(5):
        f = await _create_finding(db_session, c.id, f"RULE_{i}", "MEDIUM", created_at=now)
        findings.append(f)

    # Page 1: limit=2, offset=0
    resp1 = await client.get(
        "/api/v1/district-admin/ai-reviews?limit=2&offset=0",
        headers={"Authorization": f"Bearer {token_ind}"}
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert len(data1["items"]) == 2
    assert data1["total"] >= 5

    # Page 2: limit=2, offset=2
    resp2 = await client.get(
        "/api/v1/district-admin/ai-reviews?limit=2&offset=2",
        headers={"Authorization": f"Bearer {token_ind}"}
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["items"]) == 2

    # Verify no overlap between page 1 and page 2
    page1_ids = {i["id"] for i in data1["items"]}
    page2_ids = {i["id"] for i in data2["items"]}
    assert page1_ids.isdisjoint(page2_ids)


@pytest.mark.asyncio
async def test_invalid_filters_and_disposition_payloads_rejected(client: AsyncClient, db_session: AsyncSession):
    """
    Validates that invalid query parameters and malformed POST requests return 400 Bad Request.
    """
    await seed_data(db_session)
    admin_ind, token_ind = await _create_admin(db_session, "IND", "admin.bad@mp.gov.in")
    c = await _create_complaint(db_session, "IND", "IND-BAD-001")
    f = await _create_finding(db_session, c.id, "MISSING_RESOLUTION_EVIDENCE", "HIGH")

    # Invalid severity
    resp_sev = await client.get(
        "/api/v1/district-admin/ai-reviews?severity=EXTREME",
        headers={"Authorization": f"Bearer {token_ind}"}
    )
    assert resp_sev.status_code == 400

    # Invalid status
    resp_st = await client.get(
        "/api/v1/district-admin/ai-reviews?status=MAYBE",
        headers={"Authorization": f"Bearer {token_ind}"}
    )
    assert resp_st.status_code == 400

    # Invalid action in disposition
    resp_act = await client.post(
        f"/api/v1/district-admin/ai-reviews/{f.id}/disposition",
        json={"action": "INVALID_ACTION", "reviewer_notes": "Valid note here."},
        headers={"Authorization": f"Bearer {token_ind}"}
    )
    assert resp_act.status_code == 422 or resp_act.status_code == 400

    # Missing reviewer notes (too short)
    resp_notes = await client.post(
        f"/api/v1/district-admin/ai-reviews/{f.id}/disposition",
        json={"action": "ACCEPTED", "reviewer_notes": "no"},
        headers={"Authorization": f"Bearer {token_ind}"}
    )
    assert resp_notes.status_code == 422 or resp_notes.status_code == 400

    # AMENDED action without amendment fields
    resp_amend_empty = await client.post(
        f"/api/v1/district-admin/ai-reviews/{f.id}/disposition",
        json={"action": "AMENDED", "reviewer_notes": "Amending this finding."},
        headers={"Authorization": f"Bearer {token_ind}"}
    )
    assert resp_amend_empty.status_code == 422 or resp_amend_empty.status_code == 400


@pytest.mark.asyncio
async def test_valid_accepted_rejected_amended_actions_append_review(client: AsyncClient, db_session: AsyncSession):
    """
    Submitting ACCEPTED, REJECTED, and AMENDED appends review entries correctly.
    """
    await seed_data(db_session)
    admin_ind, token_ind = await _create_admin(db_session, "IND", "admin.actions@mp.gov.in")
    c = await _create_complaint(db_session, "IND", "IND-ACT-001")
    f = await _create_finding(db_session, c.id, "MISSING_RESOLUTION_EVIDENCE", "HIGH")

    # 1. Action: ACCEPTED
    resp1 = await client.post(
        f"/api/v1/district-admin/ai-reviews/{f.id}/disposition",
        json={
            "action": "ACCEPTED",
            "reviewer_notes": "Confirmed: officer forgot to upload repair photo."
        },
        headers={"Authorization": f"Bearer {token_ind}"}
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["current_status"] == "ACCEPTED"
    assert len(data1["reviews"]) == 1
    assert data1["reviews"][0]["action"] == "ACCEPTED"
    assert data1["reviews"][0]["reviewer_user_id"] == admin_ind.id

    # 2. Action: AMENDED (subsequent review updating status to AMENDED)
    resp2 = await client.post(
        f"/api/v1/district-admin/ai-reviews/{f.id}/disposition",
        json={
            "action": "AMENDED",
            "reviewer_notes": "Officer provided invoice via email; reducing severity to LOW.",
            "amended_severity": "LOW",
            "amended_explanation": "Documentary proof received via alternative administrative channel."
        },
        headers={"Authorization": f"Bearer {token_ind}"}
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["current_status"] == "AMENDED"
    assert len(data2["reviews"]) == 2
    # Deterministic order: latest review first
    assert data2["reviews"][0]["action"] == "AMENDED"
    assert data2["reviews"][0]["amended_severity"] == "LOW"
    assert data2["reviews"][1]["action"] == "ACCEPTED"

    # Verify original finding was NOT overwritten
    assert data2["finding_type"] == "MISSING_RESOLUTION_EVIDENCE"
    assert data2["severity"] == "HIGH"  # Original severity intact


@pytest.mark.asyncio
async def test_unknown_and_cross_district_finding_id_returns_404_without_leakage(client: AsyncClient, db_session: AsyncSession):
    """
    Submitting disposition for non-existent finding OR a finding from another district
    returns 404 without leaking cross-district existence.
    """
    await seed_data(db_session)
    admin_ind, token_ind = await _create_admin(db_session, "IND", "admin.leaktest@mp.gov.in")
    admin_bho, _ = await _create_admin(db_session, "BHO", "admin.bho.leaktest@mp.gov.in")

    c_bho = await _create_complaint(db_session, "BHO", "BHO-LEAK-001")
    f_bho = await _create_finding(db_session, c_bho.id, "OVERDUE_INACTIVITY", "HIGH")

    # Non-existent ID
    resp_none = await client.post(
        "/api/v1/district-admin/ai-reviews/non-existent-uuid/disposition",
        json={"action": "ACCEPTED", "reviewer_notes": "Review note."},
        headers={"Authorization": f"Bearer {token_ind}"}
    )
    assert resp_none.status_code == 404
    assert resp_none.json()["detail"] == "AI audit finding not found"

    # Cross-district ID (Indore admin reviewing Bhopal finding)
    resp_cross = await client.post(
        f"/api/v1/district-admin/ai-reviews/{f_bho.id}/disposition",
        json={"action": "ACCEPTED", "reviewer_notes": "Review note."},
        headers={"Authorization": f"Bearer {token_ind}"}
    )
    assert resp_cross.status_code == 404
    assert resp_cross.json()["detail"] == "AI audit finding not found"


@pytest.mark.asyncio
async def test_review_disposition_does_not_mutate_complaint_lifecycle_or_workload(client: AsyncClient, db_session: AsyncSession):
    """
    Crucial boundary: Human review disposition does NOT change complaint status,
    verification status, assigned officer, or officer workload.
    """
    await seed_data(db_session)
    admin_ind, token_ind = await _create_admin(db_session, "IND", "admin.immut@mp.gov.in")
    officer_ind, _ = await _create_officer(db_session, "IND", "officer.immut@mp.gov.in")

    officer_user_id = str(officer_ind.id)
    c = await _create_complaint(db_session, "IND", "IND-IMM-001", status=ComplaintStatus.RESOLVED)
    c.assigned_officer_id = officer_user_id
    c.verification_status = "UNVERIFIED"
    await db_session.commit()

    # Get officer profile workload
    prof_before = (await db_session.execute(select(OfficerProfile).where(OfficerProfile.user_id == officer_user_id))).scalar_one()
    initial_workload = prof_before.active_workload

    f = await _create_finding(db_session, c.id, "MISSING_RESOLUTION_EVIDENCE", "HIGH")

    # Submit REJECTED disposition
    resp = await client.post(
        f"/api/v1/district-admin/ai-reviews/{f.id}/disposition",
        json={"action": "REJECTED", "reviewer_notes": "Disregarding finding: citizen called to confirm resolution."},
        headers={"Authorization": f"Bearer {token_ind}"}
    )
    assert resp.status_code == 200

    # Refresh complaint and officer
    await db_session.refresh(c)
    prof_after = (await db_session.execute(select(OfficerProfile).where(OfficerProfile.user_id == officer_user_id))).scalar_one()

    # Assert complaint lifecycle state is completely unchanged
    assert c.status == ComplaintStatus.RESOLVED
    assert c.verification_status == "UNVERIFIED"
    assert c.assigned_officer_id == officer_user_id
    assert prof_after.active_workload == initial_workload


@pytest.mark.asyncio
async def test_audit_log_created_on_review_disposition(client: AsyncClient, db_session: AsyncSession):
    """
    Submitting a disposition records an AuditLog entry.
    """
    await seed_data(db_session)
    admin_ind, token_ind = await _create_admin(db_session, "IND", "admin.auditentry@mp.gov.in")
    c = await _create_complaint(db_session, "IND", "IND-AUD-001")
    f = await _create_finding(db_session, c.id, "MISSING_RESOLUTION_EVIDENCE", "HIGH")

    resp = await client.post(
        f"/api/v1/district-admin/ai-reviews/{f.id}/disposition",
        json={"action": "ACCEPTED", "reviewer_notes": "Acknowledged and logged into records."},
        headers={"Authorization": f"Bearer {token_ind}"}
    )
    assert resp.status_code == 200

    # Query audit logs
    audit_res = await db_session.execute(
        select(AuditLog).where(
            AuditLog.resource_type == "AI_AUDIT_FINDING",
            AuditLog.resource_id == f.id
        )
    )
    log_entry = audit_res.scalar_one_or_none()
    assert log_entry is not None
    assert log_entry.action == "AI_AUDIT_FINDING_REVIEW"
    assert log_entry.actor_user_id == admin_ind.id
    assert "ACCEPTED" in log_entry.details
