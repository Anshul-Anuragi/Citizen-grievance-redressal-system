import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from app.models.user import User, UserRole, DistrictAdminProfile, OfficerProfile
from app.models.grievance import District, Department, Category
from app.models.complaint import Complaint, ComplaintStatus, ReopenRequest
from app.core.security import get_password_hash, create_access_token

@pytest.mark.asyncio
async def test_reopen_workflow(client: AsyncClient, db_session):
    # 1. Setup District, Dept, Category, Admin, Citizen
    dist = District(code="IND", name_en="Indore", name_hi="इन्दौर", is_active=True)
    dept = Department(code="PWD", name_en="PWD", name_hi="लोक निर्माण", is_active=True)
    cat = Category(code="ROADS", name_en="Roads", name_hi="सड़क", default_sla_hours=24.0, is_active=True)
    db_session.add_all([dist, dept, cat])
    await db_session.flush()

    cit_user = User(
        email="reopen.cit@example.com",
        password_hash=get_password_hash("Pass123!"),
        full_name="Reopen Citizen",
        role=UserRole.CITIZEN,
        is_active=True,
        is_verified=True
    )
    admin_user = User(
        email="admin.ind@mp.gov.in",
        password_hash=get_password_hash("Pass123!"),
        full_name="Indore Admin",
        role=UserRole.DISTRICT_ADMIN,
        is_active=True,
        is_verified=True
    )
    db_session.add_all([cit_user, admin_user])
    await db_session.flush()

    admin_prof = DistrictAdminProfile(user_id=admin_user.id, district_code="IND")
    db_session.add(admin_prof)
    await db_session.flush()

    # 2. Create RESOLVED complaint
    deadline = datetime.now(timezone.utc) + timedelta(hours=24)
    complaint = Complaint(
        complaint_no="IND-GRV-2026-000099",
        tracking_code="TRK999",
        citizen_id=cit_user.id,
        is_anonymous=False,
        subject="Pothole issue",
        description="Pothole near square",
        district_code="IND",
        location_address="Main St",
        category_id=cat.id,
        department_id=dept.id,
        status=ComplaintStatus.RESOLVED,
        sla_deadline=deadline
    )
    db_session.add(complaint)
    await db_session.commit()

    cit_token = create_access_token(subject=cit_user.id, role="CITIZEN")
    admin_token = create_access_token(subject=admin_user.id, role="DISTRICT_ADMIN")

    # 3. Citizen submits reopen request (status must become PENDING, not directly REOPENED)
    reopen_resp = await client.post(
        f"/api/v1/complaints/{complaint.id}/reopen",
        json={"justification": "The pothole was not filled properly and broke again."},
        headers={"Authorization": f"Bearer {cit_token}"}
    )
    assert reopen_resp.status_code == 200
    assert reopen_resp.json()["status"] == "PENDING"

    # Verify complaint status remains RESOLVED until admin approves
    await db_session.refresh(complaint)
    assert complaint.status == ComplaintStatus.RESOLVED

    # 4. District Admin lists pending reopen requests
    list_resp = await client.get(
        "/api/v1/district-admin/reopen-requests?status_filter=PENDING",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert list_resp.status_code == 200
    reqs = list_resp.json()
    assert len(reqs) >= 1
    req_id = reqs[0]["id"]

    # 5. District Admin approves reopen request
    approve_resp = await client.post(
        f"/api/v1/district-admin/reopen-requests/{req_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert approve_resp.status_code == 200

    # Verify complaint status transitioned to REOPENED
    await db_session.refresh(complaint)
    assert complaint.status == ComplaintStatus.REOPENED
