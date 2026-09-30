-- ==============================================================================
-- JanSeva AI — Production PostgreSQL Least-Privilege Role Provisioning Script
-- ==============================================================================
-- IMPORTANT ARCHITECTURE NOTICE:
-- 1. Cluster-wide Scope:
--    Role definitions (CREATE ROLE) in PostgreSQL are cluster-wide (global).
--    Neither janseva_app nor janseva_migrator have SUPERUSER, CREATEDB, or
--    CREATEROLE privileges, nor are they members of each other or superusers.
--
-- 2. Database-specific Scope:
--    Table, schema, sequence, and function grants are local to the connected database.
--    This script MUST be executed while connected to the specific target database:
--      psql -v ON_ERROR_STOP=1 -d <TARGET_DATABASE> -f setup_postgres_roles.sql
--
-- 3. Immutability & Append-Only Guarantees:
--    - ai_audit_finding_reviews: SELECT, INSERT ONLY (Strictly NO UPDATE, DELETE, TRUNCATE).
--    - audit_logs: SELECT, INSERT ONLY (Strictly NO UPDATE, DELETE, TRUNCATE).
--    - ai_audit_findings: SELECT, INSERT, UPDATE (Strictly NO DELETE, TRUNCATE).
--    - alembic_version: NO ACCESS for janseva_app (migration role only).
--    - Schema public: janseva_app has USAGE only (no CREATE/DDL, cannot drop/alter).
-- ==============================================================================

-- 1. Cluster-Wide Role Provisioning (Idempotent)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'janseva_migrator') THEN
        CREATE ROLE janseva_migrator WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD 'CHANGE_IN_PRODUCTION_MIGRATOR_SECRET';
    END IF;

    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'janseva_app') THEN
        CREATE ROLE janseva_app WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD 'CHANGE_IN_PRODUCTION_APP_SECRET';
    END IF;
END $$;

-- Verify roles are not members of each other or superusers
REVOKE janseva_migrator FROM janseva_app;
REVOKE janseva_app FROM janseva_migrator;

-- 2. Database Connection Grants (Current Database Only)
GRANT CONNECT ON DATABASE current_database() TO janseva_app, janseva_migrator;

-- 3. Schema public Permissions
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM janseva_app;

GRANT USAGE ON SCHEMA public TO janseva_app;
GRANT USAGE, CREATE ON SCHEMA public TO janseva_migrator;

-- Grant schema administration to migration role
GRANT ALL PRIVILEGES ON SCHEMA public TO janseva_migrator;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO janseva_migrator;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO janseva_migrator;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO janseva_migrator;

-- In PostgreSQL, ALTER TABLE and DDL require object ownership (not merely ALL PRIVILEGES).
-- Transfer table and sequence ownership to migration role so it can execute ALTER TABLE migrations.
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE format('ALTER TABLE public.%I OWNER TO janseva_migrator;', r.tablename);
    END LOOP;
    FOR r IN (SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public') LOOP
        EXECUTE format('ALTER SEQUENCE public.%I OWNER TO janseva_migrator;', r.sequence_name);
    END LOOP;
END $$;

-- 4. Baseline Reset for Runtime Role on Current Database
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM janseva_app;

-- 5. Standard Operational Tables (DML: SELECT, INSERT, UPDATE, DELETE)
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
    users,
    district_admin_profiles,
    officer_profiles,
    refresh_tokens,
    email_verification_tokens,
    password_reset_tokens,
    districts,
    departments,
    categories,
    category_department_mappings,
    sla_rules,
    complaints,
    anonymous_access_sessions,
    complaint_attachments,
    complaint_status_history,
    complaint_messages,
    feedback,
    escalations,
    reopen_requests,
    notifications,
    ai_recommendations,
    ai_insights
TO janseva_app;

-- 6. Hardened Audit and AI Review Table Permissions
-- ai_audit_findings: SELECT, INSERT, UPDATE allowed for analysis pipeline
GRANT SELECT, INSERT, UPDATE ON TABLE ai_audit_findings TO janseva_app;

-- ai_audit_finding_reviews: Strictly SELECT and INSERT only.
-- Explicitly NO UPDATE, NO DELETE, NO TRUNCATE. Enforces append-only immutable review history.
GRANT SELECT, INSERT ON TABLE ai_audit_finding_reviews TO janseva_app;

-- audit_logs: Strictly SELECT and INSERT only.
-- Explicitly NO UPDATE, NO DELETE, NO TRUNCATE. Enforces regulatory append-only compliance audit trail.
GRANT SELECT, INSERT ON TABLE audit_logs TO janseva_app;

-- Strictly block runtime role from Alembic version tracking
REVOKE ALL PRIVILEGES ON TABLE alembic_version FROM janseva_app;

-- 7. Sequences & Functions
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO janseva_app;

DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_proc WHERE proname = 'prevent_ai_audit_review_mutation') THEN
        GRANT EXECUTE ON FUNCTION prevent_ai_audit_review_mutation() TO janseva_app;
    END IF;
END $$;

-- 8. Future Default Privileges for Objects Created by janseva_migrator
ALTER DEFAULT PRIVILEGES FOR ROLE janseva_migrator IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO janseva_app;

ALTER DEFAULT PRIVILEGES FOR ROLE janseva_migrator IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO janseva_app;

-- Explicit negative overrides on future default privileges
REVOKE UPDATE, DELETE, TRUNCATE ON TABLE ai_audit_finding_reviews FROM janseva_app;
REVOKE UPDATE, DELETE, TRUNCATE ON TABLE audit_logs FROM janseva_app;
REVOKE DELETE, TRUNCATE ON TABLE ai_audit_findings FROM janseva_app;
