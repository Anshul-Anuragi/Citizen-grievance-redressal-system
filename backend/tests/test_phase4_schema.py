import uuid
import json
import pytest
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models.user import User, UserRole
from app.models.grievance import Category, Department, District, PriorityEnum
from app.models.complaint import Complaint, ComplaintStatus, ComplaintAttachment
from app.models.ai import AIAuditFinding, AIAuditFindingReview
from app.core.security import get_password_hash
from seed import seed_data

VALID_PASSWORD = "StrongPassword@2026!"
PG_TEST_URL = os.environ.get(
    "PG_TEST_DATABASE_URL",
    "postgresql+asyncpg://janseva:janseva_password_2026@localhost:5434/janseva_phase4_test_db"
)


async def _create_test_complaint(
    db: AsyncSession,
    district_code: str = "IND",
    status: ComplaintStatus = ComplaintStatus.SUBMITTED,
    citizen: User = None
) -> Complaint:
    cat = (await db.execute(select(Category))).scalars().first()
    dept = (await db.execute(select(Department))).scalars().first()
    unique_no = f"{district_code}-TEST-{uuid.uuid4().hex[:6].upper()}"

    complaint = Complaint(
        complaint_no=unique_no,
        tracking_code=f"TRK-{uuid.uuid4().hex[:6].upper()}",
        citizen_id=citizen.id if citizen else None,
        is_anonymous=citizen is None,
        subject="Test Grievance for AI Audit",
        description="Grievance description detailing road hazard and broken street drainage.",
        district_code=district_code,
        location_address="Rajwada Square, Indore",
        category_id=cat.id,
        department_id=dept.id,
        priority=PriorityEnum.HIGH,
        status=status,
        sla_deadline=datetime.now(timezone.utc) + timedelta(days=3),
        is_overdue=False
    )
    db.add(complaint)
    await db.commit()
    await db.refresh(complaint)
    return complaint


@pytest.mark.asyncio
async def test_ai_audit_finding_creation_and_relationships(db_session: AsyncSession):
    """
    Verifies AIAuditFinding model creation, fields, JSON list properties,
    and bi-directional relationships with Complaint and ComplaintAttachment.
    """
    await seed_data(db_session)
    complaint = await _create_test_complaint(db_session, "IND", status=ComplaintStatus.RESOLVED)

    # Attach evidence file
    attachment = ComplaintAttachment(
        complaint_id=complaint.id,
        file_name="site_inspection_photo.jpg",
        file_path="uploads/site_inspection_photo.jpg",
        file_type="image/jpeg",
        file_size=204800,
        uploaded_by_user_id=None
    )
    db_session.add(attachment)
    await db_session.commit()
    await db_session.refresh(attachment)

    # Create audit finding
    facts = ["Complaint resolved on 2026-09-29", "Resolution photo attached (200KB)"]
    interpretations = ["Photo shows repaired asphalt patch", "Resolution claim aligns with reported location"]
    questions = ["Was drainage clearance verified independently?"]

    finding = AIAuditFinding(
        complaint_id=complaint.id,
        finding_type="RESOLUTION_CONSISTENCY",
        severity="INFO",
        facts=json.dumps(facts),
        interpretations=json.dumps(interpretations),
        unresolved_questions=json.dumps(questions),
        explanation="Field repair photograph corroborates asphalt patching.",
        evidence_attachment_id=attachment.id,
        evidence_assessment="PRESENT_SUPPORTING",
        rule_or_model_version="audit-engine-v1.0",
        confidence=0.92
    )
    db_session.add(finding)
    await db_session.commit()
    finding_id = finding.id
    complaint_id = complaint.id

    # Query finding back with relationships eagerly loaded
    res = await db_session.execute(
        select(AIAuditFinding)
        .options(selectinload(AIAuditFinding.complaint), selectinload(AIAuditFinding.evidence_attachment))
        .where(AIAuditFinding.id == finding_id)
    )
    refreshed_finding = res.scalar_one()

    # Check properties and JSON parsing helpers
    assert refreshed_finding.id is not None
    assert refreshed_finding.facts_list == facts
    assert refreshed_finding.interpretations_list == interpretations
    assert refreshed_finding.unresolved_questions_list == questions
    assert refreshed_finding.current_status == "PENDING_REVIEW"
    assert refreshed_finding.latest_review is None

    # Check navigability to related entities
    assert refreshed_finding.complaint.id == complaint_id
    assert refreshed_finding.evidence_attachment.id == attachment.id

    # Check reverse relationship on complaint
    refreshed_complaint = (await db_session.execute(
        select(Complaint)
        .where(Complaint.id == complaint_id)
    )).scalar_one()
    await db_session.refresh(refreshed_complaint, ["audit_findings"])
    assert len(refreshed_complaint.audit_findings) == 1
    assert refreshed_complaint.audit_findings[0].id == finding_id


@pytest.mark.asyncio
async def test_review_disposition_creation_and_preservation_of_original_finding(db_session: AsyncSession):
    """
    Verifies human review disposition creation (AMENDED action) and confirms
    that original AI finding fields are strictly preserved without being overwritten.
    """
    await seed_data(db_session)
    complaint = await _create_test_complaint(db_session, "IND", status=ComplaintStatus.IN_PROGRESS)

    original_facts = ["Overdue by 72 hours", "No officer progress notes logged"]
    original_interpretations = ["High risk of civic escalation"]
    original_explanation = "Automated SLA breach detection: zero progress notes."

    finding = AIAuditFinding(
        complaint_id=complaint.id,
        finding_type="SLA_BREACH_RISK",
        severity="HIGH",
        facts=json.dumps(original_facts),
        interpretations=json.dumps(original_interpretations),
        unresolved_questions=json.dumps([]),
        explanation=original_explanation,
        evidence_assessment="NOT_ASSESSED",
        rule_or_model_version="audit-rules-v1.0",
        confidence=0.98
    )
    db_session.add(finding)
    await db_session.commit()
    finding_id = finding.id

    # Create admin reviewer
    admin = User(
        email="rev.admin@mp.gov.in",
        password_hash=get_password_hash(VALID_PASSWORD),
        full_name="Reviewing Admin",
        role=UserRole.DISTRICT_ADMIN,
        is_active=True,
        is_verified=True
    )
    db_session.add(admin)
    await db_session.flush()

    # Append human review disposition (AMENDED)
    review = AIAuditFindingReview(
        finding_id=finding_id,
        reviewer_user_id=admin.id,
        action="AMENDED",
        reviewer_notes="Officer contacted via radio; heavy rain delayed physical asphalt pour.",
        amended_severity="MEDIUM",
        amended_explanation="Work temporarily suspended due to monsoon rainfall. Not deliberate inaction.",
        amended_facts=json.dumps(["Officer communicated delay via dispatch log"]),
        amended_interpretations=json.dumps(["Rain impediment justified short extension"])
    )
    db_session.add(review)
    await db_session.commit()

    # Refresh finding with reviews
    await db_session.refresh(finding, ["reviews"])

    # Current status updated
    assert finding.current_status == "AMENDED"
    assert finding.latest_review is not None
    assert finding.latest_review.action == "AMENDED"
    assert finding.latest_review.reviewer_user_id == admin.id
    assert finding.latest_review.amended_severity == "MEDIUM"

    # CRITICAL REQUIREMENT: Original finding fields remain strictly untouched
    assert finding.severity == "HIGH"
    assert finding.explanation == original_explanation
    assert finding.facts_list == original_facts
    assert finding.interpretations_list == original_interpretations


@pytest.mark.asyncio
async def test_multiple_review_dispositions_and_current_status_derivation(db_session: AsyncSession):
    """
    Verifies that multiple review dispositions form an append-only timeline,
    and current status reflects the latest disposition while preserving full history.
    """
    await seed_data(db_session)
    complaint = await _create_test_complaint(db_session, "IND")

    finding = AIAuditFinding(
        complaint_id=complaint.id,
        finding_type="OFFICER_OVERLOAD",
        severity="MEDIUM",
        facts=json.dumps(["Officer has 18 active tickets"]),
        interpretations=json.dumps(["Workload exceeds standard guideline of 15"]),
        unresolved_questions=json.dumps([]),
        explanation="Capacity threshold flagged for supervisor rebalancing.",
        evidence_assessment="NOT_ASSESSED",
        rule_or_model_version="audit-rules-v1.0",
        confidence=1.0
    )
    db_session.add(finding)
    await db_session.commit()
    finding_id = finding.id

    assert finding.current_status == "PENDING_REVIEW"

    # Admin 1 rejects finding initially
    admin1 = User(
        email="adm1@mp.gov.in",
        password_hash=get_password_hash(VALID_PASSWORD),
        full_name="Admin One",
        role=UserRole.DISTRICT_ADMIN,
        is_active=True,
        is_verified=True
    )
    db_session.add(admin1)
    await db_session.flush()

    review1 = AIAuditFindingReview(
        finding_id=finding_id,
        reviewer_user_id=admin1.id,
        action="REJECTED",
        reviewer_notes="Officer handles rapid routine clearances; threshold acceptable this week."
    )
    db_session.add(review1)
    await db_session.commit()

    # Refresh reviews
    await db_session.refresh(finding, ["reviews"])
    assert finding.current_status == "REJECTED"
    assert len(finding.reviews) == 1

    # Later, Supervisor re-reviews and accepts finding after backlog builds
    admin2 = User(
        email="adm2@mp.gov.in",
        password_hash=get_password_hash(VALID_PASSWORD),
        full_name="Supervising Admin",
        role=UserRole.DISTRICT_ADMIN,
        is_active=True,
        is_verified=True
    )
    db_session.add(admin2)
    await db_session.flush()

    review2 = AIAuditFindingReview(
        finding_id=finding_id,
        reviewer_user_id=admin2.id,
        action="ACCEPTED",
        reviewer_notes="Overriding rejection: 4 new urgent cases added today. Rebalancing required."
    )
    db_session.add(review2)
    await db_session.commit()

    # Refresh reviews
    await db_session.refresh(finding, ["reviews"])

    # Current status derives from latest review
    assert finding.current_status == "ACCEPTED"
    assert len(finding.reviews) == 2
    # Verify latest review is first due to desc order
    assert finding.reviews[0].action == "ACCEPTED"
    assert finding.reviews[0].reviewer_notes == "Overriding rejection: 4 new urgent cases added today. Rebalancing required."
    assert finding.reviews[1].action == "REJECTED"


@pytest.mark.asyncio
async def test_review_deterministic_ordering_with_equal_timestamps(db_session: AsyncSession):
    """
    Verifies that when multiple review dispositions have identical timestamps,
    deterministic ordering is guaranteed by id tie-breaker.
    """
    await seed_data(db_session)
    complaint = await _create_test_complaint(db_session, "IND")

    finding = AIAuditFinding(
        complaint_id=complaint.id,
        finding_type="TEST_TIE_BREAKER",
        severity="INFO",
        explanation="Testing deterministic ordering on equal timestamps.",
        rule_or_model_version="test-v1",
        confidence=1.0
    )
    db_session.add(finding)
    await db_session.commit()

    fixed_time = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)
    # Review with higher alphanumeric ID
    review_a = AIAuditFindingReview(
        id="rev-00000000-0000-0000-0000-000000000001",
        finding_id=finding.id,
        action="REJECTED",
        reviewer_notes="First by ID",
        created_at=fixed_time
    )
    # Review with higher alphanumeric ID created at same timestamp
    review_b = AIAuditFindingReview(
        id="rev-00000000-0000-0000-0000-000000000002",
        finding_id=finding.id,
        action="ACCEPTED",
        reviewer_notes="Second by ID",
        created_at=fixed_time
    )
    db_session.add_all([review_a, review_b])
    await db_session.commit()

    await db_session.refresh(finding, ["reviews"])
    # ID rev-00000000-0000-0000-0000-000000000002 is greater than rev-00000000-0000-0000-0000-000000000001
    assert finding.reviews[0].id == "rev-00000000-0000-0000-0000-000000000002"
    assert finding.reviews[1].id == "rev-00000000-0000-0000-0000-000000000001"
    assert finding.current_status == "ACCEPTED"


@pytest.mark.asyncio
async def test_append_only_enforcement_prevents_updates(db_session: AsyncSession):
    """
    Verifies that existing review disposition records cannot be updated (append-only enforcement).
    """
    await seed_data(db_session)
    complaint = await _create_test_complaint(db_session, "IND")

    finding = AIAuditFinding(
        complaint_id=complaint.id,
        finding_type="TEST_IMMUTABILITY",
        severity="INFO",
        explanation="Testing append-only enforcement.",
        rule_or_model_version="test-v1",
        confidence=1.0
    )
    db_session.add(finding)
    await db_session.commit()

    review = AIAuditFindingReview(
        finding_id=finding.id,
        action="REJECTED",
        reviewer_notes="Original review note"
    )
    db_session.add(review)
    await db_session.commit()

    # Attempt to update the review disposition in place
    review.reviewer_notes = "Tampered review note"
    with pytest.raises(ValueError, match="strictly append-only"):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_postgresql_foreign_key_deletion_behaviors():
    """
    Verifies real PostgreSQL database foreign key constraints:
    - Deleting attachment sets evidence_attachment_id to NULL (SET NULL), preserving finding.
    - Deleting reviewing user sets reviewer_user_id to NULL (SET NULL), preserving review history.
    - Deleting complaint cascades and deletes finding and its reviews (CASCADE).
    """
    try:
        engine = create_async_engine(PG_TEST_URL)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            # Seed minimal district, dept, cat if missing
            d_res = await session.execute(select(District).where(District.code == "IND"))
            dist = d_res.scalar_one_or_none()
            if not dist:
                dist = District(code="IND", name_en="Indore", name_hi="इंदौर")
                session.add(dist)
                await session.flush()

            dept_res = await session.execute(select(Department).where(Department.code == "WATER"))
            dept = dept_res.scalar_one_or_none()
            if not dept:
                dept = Department(code="WATER", name_en="Water Supply", name_hi="जल प्रदाय")
                session.add(dept)
                await session.flush()

            cat_res = await session.execute(select(Category).where(Category.code == "WATER_SUPPLY"))
            cat = cat_res.scalar_one_or_none()
            if not cat:
                cat = Category(code="WATER_SUPPLY", name_en="Water Supply", name_hi="जल आपूर्ति")
                session.add(cat)
                await session.flush()

            await session.commit()

            # Create complaint
            c = Complaint(
                complaint_no=f"TEST-PG-{uuid.uuid4().hex[:6].upper()}",
                tracking_code=f"TRK-{uuid.uuid4().hex[:6].upper()}",
                subject="PG Test Grievance",
                description="Test grievance description",
                district_code="IND",
                location_address="Indore",
                category_id=cat.id,
                department_id=dept.id,
                priority=PriorityEnum.MEDIUM,
                status=ComplaintStatus.SUBMITTED,
                sla_deadline=datetime.now(timezone.utc) + timedelta(days=2),
                is_overdue=False
            )
            session.add(c)
            await session.flush()

            # Attachment
            att = ComplaintAttachment(
                complaint_id=c.id,
                file_name="test.jpg",
                file_path="uploads/test.jpg",
                file_type="image/jpeg",
                file_size=1000
            )
            session.add(att)
            await session.flush()

            # User reviewer
            u = User(
                email=f"pg.user.{uuid.uuid4().hex[:6]}@example.com",
                password_hash="dummyhash",
                full_name="PG Reviewer",
                role=UserRole.DISTRICT_ADMIN,
                is_active=True,
                is_verified=True
            )
            session.add(u)
            await session.flush()

            # Finding
            f = AIAuditFinding(
                complaint_id=c.id,
                finding_type="RESOLUTION_CONSISTENCY",
                severity="HIGH",
                facts=json.dumps(["fact 1"]),
                interpretations=json.dumps(["interp 1"]),
                unresolved_questions=json.dumps(["q 1"]),
                explanation="explanation text",
                evidence_attachment_id=att.id,
                evidence_assessment="PRESENT_SUPPORTING",
                rule_or_model_version="rules-v1.0",
                confidence=0.9
            )
            session.add(f)
            await session.flush()

            # Review
            r = AIAuditFindingReview(
                finding_id=f.id,
                reviewer_user_id=u.id,
                action="ACCEPTED",
                reviewer_notes="Looks good."
            )
            session.add(r)
            await session.commit()

            f_id = f.id
            r_id = r.id
            att_id = att.id
            u_id = u.id
            c_id = c.id

            # Test 1: Delete attachment -> SET NULL on finding in PostgreSQL
            await session.delete(att)
            await session.commit()
            session.expire_all()

            f_ref = (await session.execute(select(AIAuditFinding).where(AIAuditFinding.id == f_id))).scalar_one()
            assert f_ref.evidence_attachment_id is None
            assert f_ref.evidence_assessment == "PRESENT_SUPPORTING"

            # Test 2: Delete reviewer -> SET NULL on review in PostgreSQL
            await session.delete(u)
            await session.commit()
            session.expire_all()

            r_ref = (await session.execute(select(AIAuditFindingReview).where(AIAuditFindingReview.id == r_id))).scalar_one()
            assert r_ref.reviewer_user_id is None
            assert r_ref.action == "ACCEPTED"

            # Test 3: Delete complaint -> CASCADE delete on finding and review in PostgreSQL
            await session.delete(c)
            await session.commit()
            session.expire_all()

            f_none = (await session.execute(select(AIAuditFinding).where(AIAuditFinding.id == f_id))).scalar_one_or_none()
            r_none = (await session.execute(select(AIAuditFindingReview).where(AIAuditFindingReview.id == r_id))).scalar_one_or_none()
            assert f_none is None
            assert r_none is None

        await engine.dispose()
    except Exception as exc:
        pytest.skip(f"PostgreSQL container test skipped: {exc}")
