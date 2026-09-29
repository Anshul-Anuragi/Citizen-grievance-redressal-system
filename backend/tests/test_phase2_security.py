"""
Phase 2 security regression tests for JanSeva AI.

Covers:
  - Logout endpoint revokes refresh token (C-3)
  - Reuse of revoked refresh token is rejected (C-3)
  - Logout with nonexistent token is handled gracefully
  - Access token usability after logout (stateless JWT until Phase 5)
  - Full-session logout revokes all tokens (C-3)
  - Password policy enforced on registration (M-8)
  - Password policy enforced on officer creation
  - Complaint description max-length enforced (M-9)
  - Cross-citizen complaint access denied (403)
  - Unauthenticated access to registered complaint denied (401)
  - Cross-district admin access denied (403)
  - Attachment access by unauthorized citizen denied (403)
  - Attachment access by unauthenticated user denied (401)
  - Attachment path traversal attempt rejected (C-6)
  - Production SECRET_KEY guard raises RuntimeError on insecure default (C-2)
  - X-Request-ID header present on every response (L-2)
  - Health endpoint reports live db_status (L-5)
  - Transaction atomicity for registered and anonymous complaint submissions
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from app.models.user import User, UserRole, DistrictAdminProfile, RefreshToken
from app.models.grievance import District, Department, Category
from app.models.complaint import Complaint, ComplaintStatus, ComplaintStatusHistory, AnonymousAccessSession, ComplaintAttachment
from app.models.audit import AuditLog
from app.core.security import get_password_hash, create_access_token
from app.services.storage_service import StorageService
from seed import seed_data

VALID_PASSWORD = "SecurePass123!"


# ---------------------------------------------------------------------------
# C-3: Logout & Token Revocation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client: AsyncClient, db_session):
    reg = await client.post("/api/v1/auth/register", json={
        "email": "logout.test@example.com",
        "password": VALID_PASSWORD,
        "full_name": "Logout Tester",
    })
    assert reg.status_code == 201

    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "logout.test@example.com",
        "password": VALID_PASSWORD,
    })
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # Logout with valid refresh token
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_resp.status_code == 200
    assert logout_resp.json()["message"] == "Logged out successfully."

    # Reuse of revoked refresh token must be rejected with 401
    refresh_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_with_nonexistent_or_invalid_token(client: AsyncClient, db_session):
    reg = await client.post("/api/v1/auth/register", json={
        "email": "invalid.logout@example.com",
        "password": VALID_PASSWORD,
        "full_name": "Invalid Logout",
    })
    assert reg.status_code == 201

    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "invalid.logout@example.com",
        "password": VALID_PASSWORD,
    })
    access_token = login_resp.json()["access_token"]

    # Logout with unknown token string should still return 200 gracefully
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "non_existent_token_12345"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_resp.status_code == 200


@pytest.mark.asyncio
async def test_access_token_still_valid_after_logout_until_expiry(client: AsyncClient, db_session):
    reg = await client.post("/api/v1/auth/register", json={
        "email": "jwt.verify@example.com",
        "password": VALID_PASSWORD,
        "full_name": "JWT Verify",
    })
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "jwt.verify@example.com",
        "password": VALID_PASSWORD,
    })
    tokens = login_resp.json()

    await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "jwt.verify@example.com"


@pytest.mark.asyncio
async def test_full_session_logout_revokes_all_tokens(client: AsyncClient, db_session):
    reg = await client.post("/api/v1/auth/register", json={
        "email": "full.logout@example.com",
        "password": VALID_PASSWORD,
        "full_name": "Full Logout Tester",
    })
    assert reg.status_code == 201

    r1 = await client.post("/api/v1/auth/login", json={"email": "full.logout@example.com", "password": VALID_PASSWORD})
    r2 = await client.post("/api/v1/auth/login", json={"email": "full.logout@example.com", "password": VALID_PASSWORD})
    token_a = r1.json()["refresh_token"]
    token_b = r2.json()["refresh_token"]
    access = r2.json()["access_token"]

    logout_resp = await client.post("/api/v1/auth/logout", json={}, headers={"Authorization": f"Bearer {access}"})
    assert logout_resp.status_code == 200

    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": token_a})).status_code == 401
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": token_b})).status_code == 401


# ---------------------------------------------------------------------------
# M-8: Password Policy
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_rejects_weak_passwords(client: AsyncClient, db_session):
    # No uppercase
    r1 = await client.post("/api/v1/auth/register", json={
        "email": "p1@example.com", "password": "lowercase123!", "full_name": "P1"
    })
    assert r1.status_code == 422

    # No lowercase
    r2 = await client.post("/api/v1/auth/register", json={
        "email": "p2@example.com", "password": "UPPERCASE123!", "full_name": "P2"
    })
    assert r2.status_code == 422

    # No digit
    r3 = await client.post("/api/v1/auth/register", json={
        "email": "p3@example.com", "password": "NoDigitsHere!", "full_name": "P3"
    })
    assert r3.status_code == 422

    # No special character
    r4 = await client.post("/api/v1/auth/register", json={
        "email": "p4@example.com", "password": "NoSpecialChar12", "full_name": "P4"
    })
    assert r4.status_code == 422

    # Too short (< 8 chars)
    r5 = await client.post("/api/v1/auth/register", json={
        "email": "p5@example.com", "password": "Ab1!", "full_name": "P5"
    })
    assert r5.status_code == 422

    # Valid strong password
    r6 = await client.post("/api/v1/auth/register", json={
        "email": "p6@example.com", "password": VALID_PASSWORD, "full_name": "P6"
    })
    assert r6.status_code == 201


@pytest.mark.asyncio
async def test_officer_create_rejects_weak_password(client: AsyncClient, db_session):
    await seed_data(db_session)
    admin = (await db_session.execute(
        select(User).where(User.role == UserRole.DISTRICT_ADMIN)
    )).scalars().first()
    token = create_access_token(admin.id, "DISTRICT_ADMIN")
    dept = (await db_session.execute(select(Department))).scalars().first()

    resp = await client.post(
        "/api/v1/district-admin/officers",
        json={
            "email": "officer.weak@mp.gov.in",
            "password": "weak",
            "full_name": "Weak Officer",
            "district_code": "IND",
            "department_id": dept.id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# M-9: Complaint Description Max Length
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_complaint_description_length_boundary(client: AsyncClient, db_session):
    await seed_data(db_session)
    cat = (await db_session.execute(select(Category))).scalars().first()

    user = User(
        email="length.test@example.com",
        password_hash=get_password_hash(VALID_PASSWORD),
        full_name="Length User",
        role=UserRole.CITIZEN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    token = create_access_token(user.id, "CITIZEN")

    # Over 5000 characters -> 422
    resp_too_long = await client.post(
        "/api/v1/complaints/submit",
        json={
            "subject": "Valid Subject",
            "description": "X" * 5001,
            "district_code": "IND",
            "location_address": "Test Street",
            "category_id": cat.id,
            "priority": "MEDIUM",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_too_long.status_code == 422

    # Exact boundary (5000 chars) -> 201
    resp_boundary = await client.post(
        "/api/v1/complaints/submit",
        json={
            "subject": "Valid Subject",
            "description": "X" * 5000,
            "district_code": "IND",
            "location_address": "Test Street",
            "category_id": cat.id,
            "priority": "MEDIUM",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_boundary.status_code == 201


# ---------------------------------------------------------------------------
# Authorization: Cross-Citizen, Unauthenticated, and Cross-District
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_citizen_cannot_view_another_citizens_complaint(client: AsyncClient, db_session):
    await seed_data(db_session)

    user_a = User(email="owner@example.com", password_hash=get_password_hash(VALID_PASSWORD), full_name="Owner", role=UserRole.CITIZEN, is_active=True, is_verified=True)
    user_b = User(email="stranger@example.com", password_hash=get_password_hash(VALID_PASSWORD), full_name="Stranger", role=UserRole.CITIZEN, is_active=True, is_verified=True)
    db_session.add_all([user_a, user_b])
    await db_session.flush()

    cat = (await db_session.execute(select(Category))).scalars().first()
    dept = (await db_session.execute(select(Department))).scalars().first()

    complaint = Complaint(
        complaint_no="IND-GRV-2026-AUTH01",
        tracking_code="TRK-AUTH01",
        citizen_id=user_a.id,
        is_anonymous=False,
        subject="Private Grievance",
        description="Private information belonging to user A.",
        district_code="IND",
        location_address="Private Road",
        category_id=cat.id,
        department_id=dept.id,
        status=ComplaintStatus.SUBMITTED,
        sla_deadline=datetime.now(timezone.utc) + timedelta(hours=48),
    )
    db_session.add(complaint)
    await db_session.commit()

    token_b = create_access_token(user_b.id, "CITIZEN")

    resp = await client.get(f"/api/v1/complaints/{complaint.id}", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 403

    resp_unauth = await client.get(f"/api/v1/complaints/{complaint.id}")
    assert resp_unauth.status_code == 401


@pytest.mark.asyncio
async def test_cross_district_admin_cannot_view_other_district_complaint(client: AsyncClient, db_session):
    await seed_data(db_session)

    bpl_admin = User(email="admin.bpl@mp.gov.in", password_hash=get_password_hash(VALID_PASSWORD), full_name="BPL Admin", role=UserRole.DISTRICT_ADMIN, is_active=True, is_verified=True)
    db_session.add(bpl_admin)
    await db_session.flush()
    bpl_prof = DistrictAdminProfile(user_id=bpl_admin.id, district_code="BPL")
    db_session.add(bpl_prof)

    cat = (await db_session.execute(select(Category))).scalars().first()
    dept = (await db_session.execute(select(Department))).scalars().first()

    ind_complaint = Complaint(
        complaint_no="IND-GRV-2026-XDIST01",
        tracking_code="TRK-XDIST01",
        citizen_id=None,
        is_anonymous=True,
        subject="Indore Pothole",
        description="Issue specifically located in Indore.",
        district_code="IND",
        location_address="Indore MG Road",
        category_id=cat.id,
        department_id=dept.id,
        status=ComplaintStatus.SUBMITTED,
        sla_deadline=datetime.now(timezone.utc) + timedelta(hours=48),
    )
    db_session.add(ind_complaint)
    await db_session.commit()

    token_bpl = create_access_token(bpl_admin.id, "DISTRICT_ADMIN")

    resp = await client.get(f"/api/v1/complaints/{ind_complaint.id}", headers={"Authorization": f"Bearer {token_bpl}"})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Attachment Access & Path Traversal (C-6)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unauthorized_attachment_access(client: AsyncClient, db_session):
    await seed_data(db_session)

    owner = User(email="att.owner@example.com", password_hash=get_password_hash(VALID_PASSWORD), full_name="Att Owner", role=UserRole.CITIZEN, is_active=True, is_verified=True)
    stranger = User(email="att.stranger@example.com", password_hash=get_password_hash(VALID_PASSWORD), full_name="Att Stranger", role=UserRole.CITIZEN, is_active=True, is_verified=True)
    db_session.add_all([owner, stranger])
    await db_session.flush()

    cat = (await db_session.execute(select(Category))).scalars().first()
    dept = (await db_session.execute(select(Department))).scalars().first()

    complaint = Complaint(
        complaint_no="IND-GRV-2026-ATT01",
        tracking_code="TRK-ATT01",
        citizen_id=owner.id,
        is_anonymous=False,
        subject="Attachment Subject",
        description="Description with confidential document.",
        district_code="IND",
        location_address="Road 1",
        category_id=cat.id,
        department_id=dept.id,
        status=ComplaintStatus.SUBMITTED,
        sla_deadline=datetime.now(timezone.utc) + timedelta(hours=48),
    )
    db_session.add(complaint)
    await db_session.flush()

    att = ComplaintAttachment(
        complaint_id=complaint.id,
        file_name="confidential.pdf",
        file_path="attachments/confidential.pdf",
        file_type="application/pdf",
        file_size=1024,
        uploaded_by_user_id=owner.id,
    )
    db_session.add(att)
    await db_session.commit()

    token_stranger = create_access_token(stranger.id, "CITIZEN")

    resp_forbidden = await client.get(f"/api/v1/attachments/view/{att.id}", headers={"Authorization": f"Bearer {token_stranger}"})
    assert resp_forbidden.status_code == 403

    resp_unauth = await client.get(f"/api/v1/attachments/view/{att.id}")
    assert resp_unauth.status_code == 401


def test_path_traversal_rejected_by_storage_service():
    with pytest.raises(ValueError, match="path traversal"):
        StorageService.get_full_file_path("../../etc/passwd")

    with pytest.raises(ValueError, match="path traversal"):
        StorageService.get_full_file_path("/etc/shadow")


# ---------------------------------------------------------------------------
# C-2: Production SECRET_KEY Guard
# ---------------------------------------------------------------------------

def test_production_secret_key_guard_raises_on_insecure_default():
    from app.core.config import _INSECURE_DEFAULT_SECRET
    from app.main import _check_production_security

    with patch("app.main.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "production"
        mock_settings.SECRET_KEY = _INSECURE_DEFAULT_SECRET
        with pytest.raises(RuntimeError, match="insecure default value"):
            _check_production_security()


def test_production_secret_key_guard_raises_on_short_key():
    from app.main import _check_production_security

    with patch("app.main.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "production"
        mock_settings.SECRET_KEY = "short_key_123"
        with pytest.raises(RuntimeError, match="too short"):
            _check_production_security()


def test_production_secret_key_guard_accepts_strong_key():
    from app.main import _check_production_security

    with patch("app.main.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "production"
        mock_settings.SECRET_KEY = "x" * 64
        _check_production_security()


def test_development_environment_permits_default_key():
    from app.core.config import _INSECURE_DEFAULT_SECRET
    from app.main import _check_production_security

    with patch("app.main.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "development"
        mock_settings.SECRET_KEY = _INSECURE_DEFAULT_SECRET
        _check_production_security()


# ---------------------------------------------------------------------------
# L-2 & L-5: Middleware and Health Check
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_x_request_id_middleware(client: AsyncClient, db_session):
    resp = await client.get("/health")
    assert "x-request-id" in resp.headers

    custom_id = "test-request-id-12345"
    resp2 = await client.get("/health", headers={"X-Request-ID": custom_id})
    assert resp2.headers.get("x-request-id") == custom_id


@pytest.mark.asyncio
async def test_health_endpoint_checks_database(client: AsyncClient, db_session):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["db_status"] == "ok"


@pytest.mark.asyncio
async def test_health_endpoint_reports_503_on_database_error(client: AsyncClient):
    from unittest.mock import patch
    from app.main import app
    from app.core.database import get_db

    async def broken_get_db():
        raise RuntimeError("Database connection refused")
        yield None

    prev_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = broken_get_db
    try:
        with patch("app.main.get_db", broken_get_db):
            resp = await client.get("/health")
            assert resp.status_code == 503
            data = resp.json()
            assert data["status"] == "unhealthy"
            assert data["db_status"] == "error"
            assert "Database connection refused" in data.get("db_detail", "")
    finally:
        if prev_override is not None:
            app.dependency_overrides[get_db] = prev_override
        else:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Section E: Transaction Atomicity
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_registered_complaint_atomicity(client: AsyncClient, db_session):
    await seed_data(db_session)
    cat = (await db_session.execute(select(Category))).scalars().first()

    user = User(email="atomic.cit@example.com", password_hash=get_password_hash(VALID_PASSWORD), full_name="Atomic Cit", role=UserRole.CITIZEN, is_active=True, is_verified=True)
    db_session.add(user)
    await db_session.commit()
    token = create_access_token(user.id, "CITIZEN")

    resp = await client.post(
        "/api/v1/complaints/submit",
        json={
            "subject": "Atomic Subject",
            "description": "Atomic test description.",
            "district_code": "IND",
            "location_address": "Indore Main Square",
            "category_id": cat.id,
            "priority": "HIGH",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    complaint_id = resp.json()["id"]

    histories = (await db_session.execute(
        select(ComplaintStatusHistory).where(ComplaintStatusHistory.complaint_id == complaint_id)
    )).scalars().all()
    assert len(histories) == 1
    assert histories[0].new_status == "SUBMITTED"
    assert histories[0].actor_role == "CITIZEN"

    audit = (await db_session.execute(
        select(AuditLog).where(AuditLog.resource_id == complaint_id)
    )).scalars().all()
    assert len(audit) >= 1
    assert audit[0].action == "COMPLAINT_STATUS_SUBMITTED"


@pytest.mark.asyncio
async def test_anonymous_complaint_atomicity(client: AsyncClient, db_session):
    await seed_data(db_session)
    cat = (await db_session.execute(select(Category))).scalars().first()

    resp = await client.post(
        "/api/v1/complaints/submit-anonymous",
        json={
            "subject": "Anonymous Atomic Subject",
            "description": "Anonymous atomic description issue.",
            "district_code": "IND",
            "location_address": "Indore Square 2",
            "category_id": cat.id,
            "priority": "MEDIUM",
        },
    )
    assert resp.status_code == 201
    complaint_id = resp.json()["id"]
    token = resp.json()["anonymous_access_token"]
    assert token is not None

    sessions = (await db_session.execute(
        select(AnonymousAccessSession).where(AnonymousAccessSession.complaint_id == complaint_id)
    )).scalars().all()
    assert len(sessions) == 1

    histories = (await db_session.execute(
        select(ComplaintStatusHistory).where(ComplaintStatusHistory.complaint_id == complaint_id)
    )).scalars().all()
    assert len(histories) == 1
    assert histories[0].actor_role == "ANONYMOUS"
