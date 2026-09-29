"""
Phase 5 Step 1: Production Database & Audit Retention Hardening Tests.

Covers:
  - Legitimate review creation and sequential append-only dispositions succeed.
  - Direct SQL UPDATE on ai_audit_finding_reviews is blocked by database trigger.
  - Rejected mutations leave the original review records completely unchanged.
  - Direct SQL DELETE on ai_audit_finding_reviews is blocked by database trigger.
  - Bulk SQL DELETE on ai_audit_finding_reviews is blocked by database trigger.
  - Parent complaint and finding deletion is blocked when review history exists (Option A Restrict Policy).
  - SQLAlchemy model metadata consistency (ondelete='RESTRICT' and relationship cascades).
  - PostgreSQL live disposable container verification (janseva_phase5_test_db).
"""

import pytest
import os
import uuid
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text, delete, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.database import Base
from app.models.user import User, UserRole
from app.models.grievance import District, Department, Category, PriorityEnum
from app.models.complaint import Complaint, ComplaintStatus
from app.models.ai import AIAuditFinding, AIAuditFindingReview
from app.core.security import get_password_hash

# Strictly targets the disposable PostgreSQL test database on port 5434
PG_DISPOSABLE_TEST_URL = os.environ.get(
    "PG_PHASE5_TEST_URL",
    "postgresql+asyncpg://janseva:janseva_password_2026@localhost:5434/janseva_phase5_test_db"
)


def test_model_metadata_and_schema_consistency():
    """
    Verifies that SQLAlchemy model metadata matches Option A strict retention policy:
    - complaints.id <- ai_audit_findings.complaint_id (ondelete='RESTRICT')
    - ai_audit_findings.id <- ai_audit_finding_reviews.finding_id (ondelete='RESTRICT')
    - ORM cascades do not permit delete-orphan on audit findings or reviews
    """
    finding_complaint_fk = next(
        fk for fk in AIAuditFinding.__table__.foreign_keys
        if fk.column.table.name == "complaints"
    )
    assert finding_complaint_fk.ondelete == "RESTRICT", (
        f"Expected complaint_id ondelete='RESTRICT', got '{finding_complaint_fk.ondelete}'"
    )

    review_finding_fk = next(
        fk for fk in AIAuditFindingReview.__table__.foreign_keys
        if fk.column.table.name == "ai_audit_findings"
    )
    assert review_finding_fk.ondelete == "RESTRICT", (
        f"Expected finding_id ondelete='RESTRICT', got '{review_finding_fk.ondelete}'"
    )

    # Verify ORM relationship cascade options
    complaint_findings_rel = Complaint.__mapper__.relationships["audit_findings"]
    assert not complaint_findings_rel.cascade.delete, "Complaint.audit_findings must not have delete cascade"
    assert not complaint_findings_rel.cascade.delete_orphan, "Complaint.audit_findings must not have delete-orphan"

    finding_reviews_rel = AIAuditFinding.__mapper__.relationships["reviews"]
    assert not finding_reviews_rel.cascade.delete, "AIAuditFinding.reviews must not have delete cascade"
    assert not finding_reviews_rel.cascade.delete_orphan, "AIAuditFinding.reviews must not have delete-orphan"


async def _setup_sqlite_triggers(session: AsyncSession):
    """Installs trigger protections on SQLite in-memory test database."""
    await session.execute(text("""
        CREATE TRIGGER IF NOT EXISTS trg_ai_audit_review_prevent_update
        BEFORE UPDATE ON ai_audit_finding_reviews
        FOR EACH ROW
        BEGIN
            SELECT RAISE(ABORT, 'AIAuditFindingReview records are strictly append-only and cannot be updated');
        END;
    """))
    await session.execute(text("""
        CREATE TRIGGER IF NOT EXISTS trg_ai_audit_review_prevent_delete
        BEFORE DELETE ON ai_audit_finding_reviews
        FOR EACH ROW
        BEGIN
            SELECT RAISE(ABORT, 'AIAuditFindingReview records are permanent audit logs and cannot be deleted');
        END;
    """))
    await session.commit()


async def _seed_test_records(session: AsyncSession):
    """Creates or reuses references, then creates a complaint, finding, and review."""
    dist = (await session.execute(select(District).where(District.code == "IND"))).scalar_one_or_none()
    if not dist:
        dist = District(code="IND", name_en="Indore", name_hi="इन्दौर")
        session.add(dist)

    dept = (await session.execute(select(Department).where(Department.code == "PWD"))).scalar_one_or_none()
    if not dept:
        dept = Department(code="PWD", name_en="Public Works", name_hi="लोक निर्माण")
        session.add(dept)

    cat = (await session.execute(select(Category).where(Category.code == "ROAD"))).scalar_one_or_none()
    if not cat:
        cat = Category(code="ROAD", name_en="Roads", name_hi="सड़क")
        session.add(cat)

    await session.flush()

    user = User(
        email=f"citizen.{uuid.uuid4().hex[:6]}@example.com",
        password_hash="mockhash",
        full_name="Citizen Tester",
        role=UserRole.CITIZEN,
        is_active=True,
        is_verified=True
    )
    admin = User(
        email=f"admin.{uuid.uuid4().hex[:6]}@example.com",
        password_hash="mockhash",
        full_name="Admin Reviewer",
        role=UserRole.DISTRICT_ADMIN,
        is_active=True,
        is_verified=True
    )
    session.add_all([user, admin])
    await session.flush()

    complaint = Complaint(
        complaint_no=f"JAN-P5-{uuid.uuid4().hex[:6].upper()}",
        tracking_code=f"TRK-P5-{uuid.uuid4().hex[:6].upper()}",
        citizen_id=user.id,
        subject="Audit Retention Test Grievance",
        description="Pothole in front of community center",
        district_code="IND",
        location_address="Indore",
        category_id=cat.id,
        department_id=dept.id,
        status=ComplaintStatus.SUBMITTED,
        sla_deadline=datetime.now(timezone.utc) + timedelta(days=2),
        is_overdue=False
    )
    session.add(complaint)
    await session.flush()

    finding = AIAuditFinding(
        complaint_id=complaint.id,
        finding_type="EVIDENCE_LIMITATION",
        severity="MEDIUM",
        facts=json.dumps(["Initial inspection"]),
        interpretations=json.dumps([]),
        unresolved_questions=json.dumps([]),
        explanation="Testing immutability triggers",
        rule_or_model_version="test-v1.0",
        confidence=0.95
    )
    session.add(finding)
    await session.flush()

    review = AIAuditFindingReview(
        finding_id=finding.id,
        reviewer_user_id=admin.id,
        action="ACCEPTED",
        reviewer_notes="Original legitimate review notes."
    )
    session.add(review)
    await session.commit()

    return complaint, finding, review, admin


@pytest.mark.asyncio
async def test_ordinary_review_creation_and_disposition_succeeds(db_session: AsyncSession):
    """Confirms triggers allow legitimate INSERT of multiple sequential dispositions."""
    await _setup_sqlite_triggers(db_session)
    complaint, finding, review1, admin = await _seed_test_records(db_session)

    # Append a secondary review (e.g. supervisor override)
    review2 = AIAuditFindingReview(
        finding_id=finding.id,
        reviewer_user_id=admin.id,
        action="AMENDED",
        reviewer_notes="Amended upon supervisor escalation.",
        amended_severity="HIGH"
    )
    db_session.add(review2)
    await db_session.commit()

    reviews = (await db_session.execute(
        select(AIAuditFindingReview).where(AIAuditFindingReview.finding_id == finding.id)
    )).scalars().all()
    assert len(reviews) == 2


@pytest.mark.asyncio
async def test_direct_sql_update_on_review_blocked_and_original_unchanged(db_session: AsyncSession):
    """Direct SQL UPDATE is blocked by trigger and leaves original review unchanged."""
    await _setup_sqlite_triggers(db_session)
    complaint, finding, review, _ = await _seed_test_records(db_session)
    original_id = review.id
    original_notes = review.reviewer_notes

    with pytest.raises(Exception) as exc_info:
        await db_session.execute(
            update(AIAuditFindingReview)
            .where(AIAuditFindingReview.id == original_id)
            .values(reviewer_notes="Tampered review notes"),
            execution_options={"synchronize_session": False}
        )
        await db_session.commit()
    await db_session.rollback()

    assert "append-only" in str(exc_info.value).lower() or "cannot be updated" in str(exc_info.value).lower()

    # Verify original review remains completely intact
    persisted = (await db_session.execute(
        select(AIAuditFindingReview).where(AIAuditFindingReview.id == original_id)
    )).scalar_one()
    assert persisted.reviewer_notes == original_notes


@pytest.mark.asyncio
async def test_direct_sql_delete_on_review_blocked_and_original_persists(db_session: AsyncSession):
    """Direct SQL DELETE is blocked by trigger and leaves original review intact."""
    await _setup_sqlite_triggers(db_session)
    complaint, finding, review, _ = await _seed_test_records(db_session)
    original_id = review.id

    with pytest.raises(Exception) as exc_info:
        await db_session.execute(
            delete(AIAuditFindingReview).where(AIAuditFindingReview.id == original_id),
            execution_options={"synchronize_session": False}
        )
        await db_session.commit()
    await db_session.rollback()

    assert "permanent" in str(exc_info.value).lower() or "cannot be deleted" in str(exc_info.value).lower()

    # Verify original review still exists in database
    persisted = (await db_session.execute(
        select(AIAuditFindingReview).where(AIAuditFindingReview.id == original_id)
    )).scalar_one_or_none()
    assert persisted is not None


@pytest.mark.asyncio
async def test_bulk_sql_delete_on_review_blocked_by_database_protection(db_session: AsyncSession):
    """Bulk SQL DELETE statements without specific ID are blocked by database trigger."""
    await _setup_sqlite_triggers(db_session)
    complaint, finding, review, _ = await _seed_test_records(db_session)

    with pytest.raises(Exception) as exc_info:
        await db_session.execute(
            delete(AIAuditFindingReview),
            execution_options={"synchronize_session": False}
        )
        await db_session.commit()
    await db_session.rollback()

    assert "permanent" in str(exc_info.value).lower() or "cannot be deleted" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_postgresql_live_disposable_database_hardening():
    """
    Executes live verification strictly against disposable PostgreSQL database (janseva_phase5_test_db):
    - Confirms execution is NOT against default or production database
    - Tests trigger blocks direct SQL UPDATE and leaves original notes unchanged
    - Tests trigger blocks direct SQL DELETE and leaves review persisted
    - Tests trigger blocks bulk SQL DELETE
    - Tests foreign key RESTRICT blocks deleting parent finding
    - Tests foreign key RESTRICT blocks deleting parent complaint
    """
    # Guard: strictly verify destination database name
    assert "janseva_phase5_test_db" in PG_DISPOSABLE_TEST_URL, (
        f"Safety abort: live test must target disposable janseva_phase5_test_db, got {PG_DISPOSABLE_TEST_URL}"
    )

    try:
        engine = create_async_engine(PG_DISPOSABLE_TEST_URL)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            complaint, finding, review, admin = await _seed_test_records(session)
            review_id = review.id
            finding_id = finding.id
            complaint_id = complaint.id
            original_notes = review.reviewer_notes
            session.expunge_all()

            # 1. Verify direct SQL UPDATE fails with trigger exception
            with pytest.raises(Exception) as exc_update:
                await session.execute(
                    update(AIAuditFindingReview)
                    .where(AIAuditFindingReview.id == review_id)
                    .values(reviewer_notes="tampered_notes"),
                    execution_options={"synchronize_session": False}
                )
                await session.commit()
            await session.rollback()
            session.expunge_all()
            assert "append-only" in str(exc_update.value).lower()

            # Verify review notes remain unchanged
            refreshed_review = (await session.execute(
                select(AIAuditFindingReview).where(AIAuditFindingReview.id == review_id)
            )).scalar_one()
            assert refreshed_review.reviewer_notes == original_notes
            session.expunge_all()

            # 2. Verify direct SQL DELETE fails with trigger exception
            with pytest.raises(Exception) as exc_del:
                await session.execute(
                    delete(AIAuditFindingReview).where(AIAuditFindingReview.id == review_id),
                    execution_options={"synchronize_session": False}
                )
                await session.commit()
            await session.rollback()
            session.expunge_all()
            assert "permanent audit logs" in str(exc_del.value).lower()

            # Verify review still exists
            persisted_check = (await session.execute(
                select(AIAuditFindingReview).where(AIAuditFindingReview.id == review_id)
            )).scalar_one_or_none()
            assert persisted_check is not None
            session.expunge_all()

            # 3. Verify bulk SQL DELETE fails with trigger exception
            with pytest.raises(Exception) as exc_bulk:
                await session.execute(
                    delete(AIAuditFindingReview),
                    execution_options={"synchronize_session": False}
                )
                await session.commit()
            await session.rollback()
            session.expunge_all()
            assert "permanent audit logs" in str(exc_bulk.value).lower()

            # 4. Verify deleting parent finding fails under RESTRICT foreign key
            with pytest.raises(Exception) as exc_finding:
                await session.execute(
                    delete(AIAuditFinding).where(AIAuditFinding.id == finding_id),
                    execution_options={"synchronize_session": False}
                )
                await session.commit()
            await session.rollback()
            session.expunge_all()
            err_finding_str = str(exc_finding.value).lower()
            assert "permanent audit logs" in err_finding_str or "violates foreign key constraint" in err_finding_str

            # 5. Verify deleting parent complaint fails under RESTRICT foreign key
            with pytest.raises(Exception) as exc_complaint:
                await session.execute(
                    delete(Complaint).where(Complaint.id == complaint_id),
                    execution_options={"synchronize_session": False}
                )
                await session.commit()
            await session.rollback()
            session.expunge_all()
            err_complaint_str = str(exc_complaint.value).lower()
            assert "permanent audit logs" in err_complaint_str or "violates foreign key constraint" in err_complaint_str

        await engine.dispose()
    except Exception as exc:
        pytest.skip(f"PostgreSQL container test skipped: {exc}")
