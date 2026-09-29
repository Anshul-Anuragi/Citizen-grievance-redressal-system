import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from app.models.user import User, UserRole, DistrictAdminProfile, OfficerProfile
from app.models.grievance import District, Department, Category
from app.models.complaint import Complaint, ComplaintStatus
from app.core.security import get_password_hash, create_access_token
from app.services.assignment_service import AssignmentService

@pytest.mark.asyncio
async def test_workload_and_assignment(client: AsyncClient, db_session):
    # 1. Setup District, Dept, Admin, Officer
    dist = District(code="IND", name_en="Indore", name_hi="इन्दौर", is_active=True)
    dept = Department(code="PWD", name_en="PWD", name_hi="लोक निर्माण", is_active=True)
    cat = Category(code="ROADS", name_en="Roads", name_hi="सड़क", default_sla_hours=24.0, is_active=True)
    db_session.add_all([dist, dept, cat])
    await db_session.flush()

    admin_user = User(
        email="admin.ind2@mp.gov.in",
        password_hash=get_password_hash("Pass123!"),
        full_name="Indore Admin 2",
        role=UserRole.DISTRICT_ADMIN,
        is_active=True,
        is_verified=True
    )
    off_user = User(
        email="off.ind.pwd@mp.gov.in",
        password_hash=get_password_hash("Pass123!"),
        full_name="PWD Officer",
        role=UserRole.OFFICER,
        is_active=True,
        is_verified=True
    )
    db_session.add_all([admin_user, off_user])
    await db_session.flush()

    admin_prof = DistrictAdminProfile(user_id=admin_user.id, district_code="IND")
    off_prof = OfficerProfile(
        user_id=off_user.id,
        officer_id="OFF-IND-001",
        district_code="IND",
        department_id=dept.id,
        is_available=True,
        active_workload=0
    )
    db_session.add_all([admin_prof, off_prof])
    await db_session.flush()

    # 2. Create complaint
    deadline = datetime.now(timezone.utc) + timedelta(hours=24)
    complaint = Complaint(
        complaint_no="IND-GRV-2026-000100",
        tracking_code="TRK100",
        citizen_id=None,
        is_anonymous=True,
        subject="Road damage",
        description="Road broken",
        district_code="IND",
        location_address="Main St",
        category_id=cat.id,
        department_id=dept.id,
        status=ComplaintStatus.SUBMITTED,
        sla_deadline=deadline
    )
    db_session.add(complaint)
    await db_session.commit()

    admin_token = create_access_token(subject=admin_user.id, role="DISTRICT_ADMIN")

    # 3. Assign officer -> workload increases from 0 to 1
    assign_resp = await client.post(
        f"/api/v1/district-admin/complaints/{complaint.id}/assign",
        json={"officer_id": off_user.id},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert assign_resp.status_code == 200

    await db_session.refresh(off_prof)
    assert off_prof.active_workload == 1

    # 4. Resolve complaint via officer -> workload decreases from 1 to 0
    off_token = create_access_token(subject=off_user.id, role="OFFICER")
    await client.post(
        f"/api/v1/officer/complaints/{complaint.id}/start",
        headers={"Authorization": f"Bearer {off_token}"}
    )
    resolve_resp = await client.post(
        f"/api/v1/officer/complaints/{complaint.id}/resolve?resolution_summary=Repaired+road",
        headers={"Authorization": f"Bearer {off_token}"}
    )
    assert resolve_resp.status_code == 200

    await db_session.refresh(off_prof)
    assert off_prof.active_workload == 0

    # 5. Close resolved complaint via Admin -> workload should NOT drop below 0 (no double decrement)
    close_resp = await client.post(
        f"/api/v1/district-admin/complaints/{complaint.id}/status",
        json={"status": "CLOSED", "remarks": "Admin verified closure"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert close_resp.status_code == 200

    await db_session.refresh(off_prof)
    assert off_prof.active_workload == 0
