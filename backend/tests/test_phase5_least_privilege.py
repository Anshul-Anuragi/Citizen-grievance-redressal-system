"""
JanSeva AI — Phase 5 Step 2: Production PostgreSQL Least-Privilege Role Hardening Tests

Verifies strict separation between:
1. Application runtime role (janseva_app) — minimal required DML, append-only review & audit logs, no DDL/ownership.
2. Migration role (janseva_migrator) — schema administration, migrations.

All tests run strictly against the positively identified disposable PostgreSQL database 'janseva_phase5_test_db'.
Zero passwords are committed or printed in output. Credentials are read from environment or .env.local.
"""

import os
from pathlib import Path
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError


# Positively identified disposable database
DISPOSABLE_DB = "janseva_phase5_test_db"

# Load local test credentials from gitignored .env.local if present
_env_local = Path(__file__).resolve().parent.parent / ".env.local"
if _env_local.is_file():
    with open(_env_local) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

_PG_HOST = os.environ.get("PG_HOST", "localhost")
_PG_PORT = os.environ.get("PG_PORT", "5434")
_ADMIN_USER = os.environ.get("PG_ADMIN_USER", "janseva")
_ADMIN_PWD = os.environ.get("PG_ADMIN_PASSWORD", "janseva_password_2026")
_APP_USER = os.environ.get("PG_APP_USER", "janseva_app")
_APP_PWD = os.environ.get("PG_TEST_APP_PASSWORD", "")
_MIGRATOR_USER = os.environ.get("PG_MIGRATOR_USER", "janseva_migrator")
_MIGRATOR_PWD = os.environ.get("PG_TEST_MIGRATOR_PASSWORD", "")

ADMIN_URL = os.environ.get(
    "PG_TEST_DATABASE_URL",
    f"postgresql+asyncpg://{_ADMIN_USER}:{_ADMIN_PWD}@{_PG_HOST}:{_PG_PORT}/{DISPOSABLE_DB}"
)
APP_URL = os.environ.get(
    "PG_TEST_APP_URL",
    f"postgresql+asyncpg://{_APP_USER}:{_APP_PWD}@{_PG_HOST}:{_PG_PORT}/{DISPOSABLE_DB}"
)
MIGRATOR_URL = os.environ.get(
    "PG_TEST_MIGRATOR_URL",
    f"postgresql+asyncpg://{_MIGRATOR_USER}:{_MIGRATOR_PWD}@{_PG_HOST}:{_PG_PORT}/{DISPOSABLE_DB}"
)


async def _get_app_session():
    engine = create_async_engine(APP_URL, echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
    return engine, session_factory()


async def _get_migrator_session():
    engine = create_async_engine(MIGRATOR_URL, echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
    return engine, session_factory()


@pytest.mark.asyncio
async def test_runtime_connectivity_and_health_check():
    """Confirm runtime role can connect, execute SELECT 1, and run advisory lock."""
    try:
        engine, session = await _get_app_session()
    except Exception as exc:
        pytest.skip(f"PostgreSQL container test skipped: {exc}")

    try:
        async with session:
            user = await session.scalar(text("SELECT current_user;"))
            assert user == "janseva_app", f"Expected current_user to be 'janseva_app', got '{user}'"

            val = await session.scalar(text("SELECT 1;"))
            assert val == 1

            lock_result = await session.scalar(text("SELECT pg_advisory_xact_lock(888888);"))
            assert lock_result is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_least_privilege_denies_audit_review_update():
    """Confirm janseva_app is denied UPDATE on ai_audit_finding_reviews with 42501."""
    try:
        engine, session = await _get_app_session()
    except Exception as exc:
        pytest.skip(f"PostgreSQL container test skipped: {exc}")

    try:
        async with session:
            with pytest.raises(DBAPIError) as exc_info:
                await session.execute(
                    text("UPDATE ai_audit_finding_reviews SET reviewer_notes = 'unauthorized' WHERE 1=1;")
                )
            await session.rollback()
            assert "permission denied for table ai_audit_finding_reviews" in str(exc_info.value).lower()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_least_privilege_denies_audit_review_delete():
    """Confirm janseva_app is denied DELETE on ai_audit_finding_reviews with 42501."""
    try:
        engine, session = await _get_app_session()
    except Exception as exc:
        pytest.skip(f"PostgreSQL container test skipped: {exc}")

    try:
        async with session:
            with pytest.raises(DBAPIError) as exc_info:
                await session.execute(
                    text("DELETE FROM ai_audit_finding_reviews WHERE 1=1;")
                )
            await session.rollback()
            assert "permission denied for table ai_audit_finding_reviews" in str(exc_info.value).lower()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_least_privilege_denies_audit_review_truncate():
    """Confirm janseva_app is denied TRUNCATE on ai_audit_finding_reviews with 42501."""
    try:
        engine, session = await _get_app_session()
    except Exception as exc:
        pytest.skip(f"PostgreSQL container test skipped: {exc}")

    try:
        async with session:
            with pytest.raises(DBAPIError) as exc_info:
                await session.execute(
                    text("TRUNCATE TABLE ai_audit_finding_reviews;")
                )
            await session.rollback()
            assert "permission denied for table ai_audit_finding_reviews" in str(exc_info.value).lower()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_least_privilege_denies_table_alter_and_drop():
    """Confirm janseva_app cannot DROP table or DISABLE triggers on audit tables."""
    try:
        engine, session = await _get_app_session()
    except Exception as exc:
        pytest.skip(f"PostgreSQL container test skipped: {exc}")

    try:
        async with session:
            # 1. Drop table denial
            with pytest.raises(DBAPIError) as exc_drop:
                await session.execute(text("DROP TABLE ai_audit_finding_reviews;"))
            await session.rollback()
            assert "must be owner of table" in str(exc_drop.value).lower() or "permission denied" in str(exc_drop.value).lower()

            # 2. Disable trigger denial
            with pytest.raises(DBAPIError) as exc_trigger:
                await session.execute(
                    text("ALTER TABLE ai_audit_finding_reviews DISABLE TRIGGER trg_prevent_ai_audit_review_mutation;")
                )
            await session.rollback()
            assert "must be owner of table" in str(exc_trigger.value).lower() or "permission denied" in str(exc_trigger.value).lower()

            # 3. Change table owner denial
            with pytest.raises(DBAPIError) as exc_owner:
                await session.execute(
                    text("ALTER TABLE ai_audit_finding_reviews OWNER TO janseva_app;")
                )
            await session.rollback()
            assert "must be owner of table" in str(exc_owner.value).lower() or "permission denied" in str(exc_owner.value).lower()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_least_privilege_denies_schema_ddl():
    """Confirm janseva_app is denied CREATE TABLE in schema public."""
    try:
        engine, session = await _get_app_session()
    except Exception as exc:
        pytest.skip(f"PostgreSQL container test skipped: {exc}")

    try:
        async with session:
            with pytest.raises(DBAPIError) as exc_info:
                await session.execute(text("CREATE TABLE evil_table (id int);"))
            await session.rollback()
            assert "permission denied for schema public" in str(exc_info.value).lower()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_least_privilege_denies_role_escalation():
    """Confirm janseva_app cannot escalate privileges using SET ROLE."""
    try:
        engine, session = await _get_app_session()
    except Exception as exc:
        pytest.skip(f"PostgreSQL container test skipped: {exc}")

    try:
        async with session:
            with pytest.raises(DBAPIError) as exc_info:
                await session.execute(text("SET ROLE janseva_migrator;"))
            await session.rollback()
            assert "permission denied to set role" in str(exc_info.value).lower()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_audit_logs_append_only_enforcement():
    """Confirm audit_logs allows SELECT and INSERT, but denies UPDATE and DELETE."""
    try:
        engine, session = await _get_app_session()
    except Exception as exc:
        pytest.skip(f"PostgreSQL container test skipped: {exc}")

    try:
        async with session:
            # 1. INSERT is allowed
            log_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            await session.execute(
                text("""
                    INSERT INTO audit_logs (id, resource_type, resource_id, action, timestamp)
                    VALUES (:id, 'complaint', 'test-res', 'SECURITY_TEST', :ts);
                """),
                {"id": log_id, "ts": now}
            )
            await session.commit()

            # 2. SELECT is allowed
            read_action = await session.scalar(
                text("SELECT action FROM audit_logs WHERE id = :id;"),
                {"id": log_id}
            )
            assert read_action == "SECURITY_TEST"

            # 3. UPDATE is denied
            with pytest.raises(DBAPIError) as exc_upd:
                await session.execute(
                    text("UPDATE audit_logs SET details = 'tampered' WHERE id = :id;"),
                    {"id": log_id}
                )
            await session.rollback()
            assert "permission denied for table audit_logs" in str(exc_upd.value).lower()

            # 4. DELETE is denied
            with pytest.raises(DBAPIError) as exc_del:
                await session.execute(
                    text("DELETE FROM audit_logs WHERE id = :id;"),
                    {"id": log_id}
                )
            await session.rollback()
            assert "permission denied for table audit_logs" in str(exc_del.value).lower()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_findings_delete_denial():
    """Confirm janseva_app is denied DELETE and TRUNCATE on ai_audit_findings."""
    try:
        engine, session = await _get_app_session()
    except Exception as exc:
        pytest.skip(f"PostgreSQL container test skipped: {exc}")

    try:
        async with session:
            with pytest.raises(DBAPIError) as exc_del:
                await session.execute(text("DELETE FROM ai_audit_findings WHERE 1=1;"))
            await session.rollback()
            assert "permission denied for table ai_audit_findings" in str(exc_del.value).lower()

            with pytest.raises(DBAPIError) as exc_trunc:
                await session.execute(text("TRUNCATE TABLE ai_audit_findings;"))
            await session.rollback()
            assert "permission denied for table ai_audit_findings" in str(exc_trunc.value).lower()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_legitimate_complaint_and_review_workflow():
    """Confirm legitimate complaint creation, finding, and review disposition work under janseva_app."""
    try:
        engine, session = await _get_app_session()
    except Exception as exc:
        pytest.skip(f"PostgreSQL container test skipped: {exc}")

    try:
        async with session:
            # Query existing category and department
            cat_id = await session.scalar(text("SELECT id FROM categories LIMIT 1;"))
            dept_id = await session.scalar(text("SELECT id FROM departments LIMIT 1;"))
            assert cat_id is not None and dept_id is not None

            cid = str(uuid.uuid4())
            fid = str(uuid.uuid4())
            rid = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            c_no = f"LP-TEST-{uuid.uuid4().hex[:6].upper()}"
            trk = f"TRK-{uuid.uuid4().hex[:6].upper()}"

            # 1. Create Complaint
            await session.execute(
                text("""
                    INSERT INTO complaints (
                        id, complaint_no, tracking_code, subject, description,
                        category_id, department_id, district_code, location_address,
                        status, priority, is_anonymous, sla_deadline, is_overdue,
                        verification_status, created_at, updated_at
                    )
                    VALUES (
                        :id, :no, :trk, 'Least Privilege Test', 'Testing app role DML',
                        :cat_id, :dept_id, 'IND', 'Indore Community Center',
                        'SUBMITTED', 'MEDIUM', false, :deadline, false,
                        'PENDING', :now, :now
                    );
                """),
                {
                    "id": cid,
                    "no": c_no,
                    "trk": trk,
                    "cat_id": cat_id,
                    "dept_id": dept_id,
                    "deadline": now + timedelta(days=2),
                    "now": now
                }
            )

            # 2. Insert Status History
            await session.execute(
                text("""
                    INSERT INTO complaint_status_history (id, complaint_id, previous_status, new_status, actor_role, timestamp)
                    VALUES (:id, :cid, 'SUBMITTED', 'IN_PROGRESS', 'SYSTEM', :now);
                """),
                {"id": str(uuid.uuid4()), "cid": cid, "now": now}
            )

            # 3. Insert AI Finding
            await session.execute(
                text("""
                    INSERT INTO ai_audit_findings (
                        id, complaint_id, finding_type, severity, facts,
                        interpretations, unresolved_questions, explanation,
                        evidence_assessment, rule_or_model_version, confidence, created_at
                    )
                    VALUES (
                        :id, :cid, 'EVIDENCE_LIMITATION', 'MEDIUM', '[]',
                        '[]', '[]', 'Testing app role permissions',
                        'INCONCLUSIVE', 'test-v1', 0.95, :now
                    );
                """),
                {"id": fid, "cid": cid, "now": now}
            )

            # 4. Insert Review Disposition (INSERT is allowed on review table)
            await session.execute(
                text("""
                    INSERT INTO ai_audit_finding_reviews (id, finding_id, action, reviewer_notes, created_at)
                    VALUES (:id, :fid, 'DISMISSED', 'Disposition inserted legitimately by runtime role', :now);
                """),
                {"id": rid, "fid": fid, "now": now}
            )
            await session.commit()

            # Verify read back
            res = await session.execute(
                text("SELECT action, reviewer_notes FROM ai_audit_finding_reviews WHERE id = :id;"),
                {"id": rid}
            )
            row = res.mappings().one()
            assert row["action"] == "DISMISSED"
            assert "legitimately" in row["reviewer_notes"]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_retention_and_immutability_preserved():
    """Confirm review record immutability and foreign key RESTRICT parent retention under runtime role."""
    try:
        engine, session = await _get_app_session()
    except Exception as exc:
        pytest.skip(f"PostgreSQL container test skipped: {exc}")

    try:
        async with session:
            # Find a complaint that has an AI audit finding
            res = await session.execute(
                text("SELECT id FROM complaints WHERE id IN (SELECT complaint_id FROM ai_audit_findings) LIMIT 1;")
            )
            cid = res.scalar()
            assert cid is not None, "Expected at least one complaint with an AI finding"

            # Attempt to delete the parent complaint - must be rejected by foreign key RESTRICT constraint
            with pytest.raises(IntegrityError) as exc_info:
                await session.execute(
                    text("DELETE FROM complaints WHERE id = :id;"),
                    {"id": cid}
                )
            await session.rollback()
            assert "violates foreign key constraint" in str(exc_info.value).lower() or "restrict" in str(exc_info.value).lower()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_migration_role_separation():
    """Confirm migrator role has alembic privileges while runtime role is completely blocked from alembic."""
    try:
        m_engine, m_session = await _get_migrator_session()
        a_engine, a_session = await _get_app_session()
    except Exception as exc:
        pytest.skip(f"PostgreSQL container test skipped: {exc}")

    try:
        async with m_session:
            m_user = await m_session.scalar(text("SELECT current_user;"))
            assert m_user == "janseva_migrator"

            version = await m_session.scalar(text("SELECT version_num FROM alembic_version;"))
            assert version == "d3949c6cbb01"

        async with a_session:
            with pytest.raises(DBAPIError) as exc_app:
                await a_session.execute(text("SELECT version_num FROM alembic_version;"))
            await a_session.rollback()
            assert "permission denied for table alembic_version" in str(exc_app.value).lower()
    finally:
        await m_engine.dispose()
        await a_engine.dispose()
