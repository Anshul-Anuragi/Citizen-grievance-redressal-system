import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.models.user import User, UserRole
from seed import seed_data

@pytest.mark.asyncio
async def test_district_isolation_enforcement(client: AsyncClient, db_session):
    # Seed data directly into test session
    await seed_data(db_session)

    # Query active Indore District Admin with profile loaded
    from sqlalchemy.orm import selectinload
    res_admin = await db_session.execute(
        select(User).options(selectinload(User.district_admin_profile)).where(User.role == UserRole.DISTRICT_ADMIN)
    )
    admin_user = res_admin.scalars().first()
    assert admin_user is not None

    # Authenticate as test admin
    from app.core.security import create_access_token
    token = create_access_token(admin_user.id, admin_user.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # Seed test complaint for district
    from app.models.complaint import Complaint, ComplaintStatus
    from app.models.grievance import Category, Department
    cat = (await db_session.execute(select(Category))).scalars().first()
    dept = (await db_session.execute(select(Department))).scalars().first()
    
    from datetime import datetime, timedelta, timezone
    c_test = Complaint(
        complaint_no="AGM-GRV-2026-000001",
        tracking_code="TRK-AGM123",
        subject="Test Grievance for Agar Malwa",
        description="Pothole issue in Agar Malwa main street.",
        location_address="Agar Malwa Main Road",
        district_code=admin_user.district_admin_profile.district_code,
        category_id=cat.id,
        department_id=dept.id,
        status=ComplaintStatus.SUBMITTED,
        sla_deadline=datetime.now(timezone.utc) + timedelta(hours=24)
    )
    db_session.add(c_test)
    await db_session.commit()

    # Fetch district complaints - should ONLY return admin's district complaints
    res = await client.get("/api/v1/district-admin/complaints", headers=headers)
    assert res.status_code == 200
    complaints = res.json()
    assert len(complaints) > 0
    for c in complaints:
        assert c["district_code"] == admin_user.district_admin_profile.district_code
