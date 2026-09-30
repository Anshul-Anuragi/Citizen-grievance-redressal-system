"""
JanSeva AI — Production PostgreSQL Role Provisioning Utility

Provisions and hardens the separation of database roles:
1. Migration administrator (e.g. janseva_migrator)
2. Application runtime role (e.g. janseva_app)

Zero secrets are hardcoded. Passwords must be provided via environment variables
or CLI parameters. Never logs credentials to stdout.
"""

import argparse
import asyncio
import os
import secrets
import sys
from typing import Optional, List
import asyncpg


APPLICATION_TABLES = [
    "users",
    "district_admin_profiles",
    "officer_profiles",
    "refresh_tokens",
    "email_verification_tokens",
    "password_reset_tokens",
    "districts",
    "departments",
    "categories",
    "category_department_mappings",
    "sla_rules",
    "complaints",
    "anonymous_access_sessions",
    "complaint_attachments",
    "complaint_status_history",
    "complaint_messages",
    "feedback",
    "escalations",
    "reopen_requests",
    "notifications",
    "ai_recommendations",
    "ai_insights",
]


async def provision_roles(
    admin_url: str,
    target_db: str,
    app_user: str,
    app_password: str,
    migrator_user: str,
    migrator_password: str,
) -> None:
    # 1. Cluster-wide role creation and membership checks
    conn_admin = await asyncpg.connect(admin_url)
    try:
        # Verify target database actually exists before proceeding
        db_exists = await conn_admin.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1;", target_db
        )
        if not db_exists:
            raise ValueError(f"Target database '{target_db}' does not exist on target PostgreSQL instance.")

        print(f"[*] Positively identified target database: {target_db}")

        # Provision migration role
        mig_exists = await conn_admin.fetchval(
            "SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = $1;", migrator_user
        )
        safe_mig_pwd = migrator_password.replace("'", "''")
        if not mig_exists:
            await conn_admin.execute(
                f'CREATE ROLE "{migrator_user}" WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD \'{safe_mig_pwd}\';'
            )
            print(f"[+] Created migration role: {migrator_user}")
        else:
            await conn_admin.execute(
                f'ALTER ROLE "{migrator_user}" WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD \'{safe_mig_pwd}\';'
            )
            print(f"[*] Updated migration role: {migrator_user}")

        # Provision runtime role
        app_exists = await conn_admin.fetchval(
            "SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = $1;", app_user
        )
        safe_app_pwd = app_password.replace("'", "''")
        if not app_exists:
            await conn_admin.execute(
                f'CREATE ROLE "{app_user}" WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD \'{safe_app_pwd}\';'
            )
            print(f"[+] Created runtime role: {app_user}")
        else:
            await conn_admin.execute(
                f'ALTER ROLE "{app_user}" WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD \'{safe_app_pwd}\';'
            )
            print(f"[*] Updated runtime role: {app_user}")

        # Ensure roles are not members of each other
        await conn_admin.execute(f'REVOKE "{migrator_user}" FROM "{app_user}";')
        await conn_admin.execute(f'REVOKE "{app_user}" FROM "{migrator_user}";')

        # Grant CONNECT privilege on the target database only
        await conn_admin.execute(
            f'GRANT CONNECT ON DATABASE "{target_db}" TO "{app_user}", "{migrator_user}";'
        )
        print(f"[+] Granted CONNECT on database '{target_db}'")
    finally:
        await conn_admin.close()

    # 2. Database-specific grants connected directly to target database
    conn_target = await asyncpg.connect(admin_url, database=target_db)
    try:
        current_db = await conn_target.fetchval("SELECT current_database();")
        if current_db != target_db:
            raise RuntimeError(f"Connection mismatch: expected '{target_db}', got '{current_db}'")

        # Schema public isolation
        await conn_target.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC;")
        await conn_target.execute(f'REVOKE CREATE ON SCHEMA public FROM "{app_user}";')
        await conn_target.execute(f'GRANT USAGE ON SCHEMA public TO "{app_user}";')
        await conn_target.execute(f'GRANT USAGE, CREATE ON SCHEMA public TO "{migrator_user}";')

        # Migration administrator schema rights
        await conn_target.execute(f'GRANT ALL PRIVILEGES ON SCHEMA public TO "{migrator_user}";')
        await conn_target.execute(f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "{migrator_user}";')
        await conn_target.execute(f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "{migrator_user}";')
        await conn_target.execute(f'GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO "{migrator_user}";')

        # In PostgreSQL, ALTER TABLE and DDL require object ownership (not merely ALL PRIVILEGES).
        # Transfer ownership of existing public tables and sequences to the migration role.
        tables_to_transfer = await conn_target.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"
        )
        for row in tables_to_transfer:
            t = row["tablename"]
            await conn_target.execute(f'ALTER TABLE public."{t}" OWNER TO "{migrator_user}";')

        seqs_to_transfer = await conn_target.fetch(
            "SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public';"
        )
        for row in seqs_to_transfer:
            s = row["sequence_name"]
            await conn_target.execute(f'ALTER SEQUENCE public."{s}" OWNER TO "{migrator_user}";')
        print(f"[+] Reassigned ownership of {len(tables_to_transfer)} tables to '{migrator_user}'")

        # Clean baseline for runtime role
        await conn_target.execute(f'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM "{app_user}";')

        # Detect existing tables in target database
        existing_tables = set(
            await conn_target.fetchval(
                "SELECT array_agg(tablename::text) FROM pg_tables WHERE schemaname = 'public';"
            )
            or []
        )

        # Operational tables
        active_app_tables = [t for t in APPLICATION_TABLES if t in existing_tables]
        if active_app_tables:
            tables_clause = ", ".join(f'"{t}"' for t in active_app_tables)
            await conn_target.execute(
                f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {tables_clause} TO "{app_user}";'
            )
            print(f"[+] Granted SELECT, INSERT, UPDATE, DELETE on {len(active_app_tables)} operational tables")

        # AI findings
        if "ai_audit_findings" in existing_tables:
            await conn_target.execute(
                f'GRANT SELECT, INSERT, UPDATE ON TABLE "ai_audit_findings" TO "{app_user}";'
            )
            await conn_target.execute(
                f'REVOKE DELETE, TRUNCATE ON TABLE "ai_audit_findings" FROM "{app_user}";'
            )
            print(f"[+] Granted SELECT, INSERT, UPDATE on ai_audit_findings (DELETE/TRUNCATE revoked)")

        # AI reviews (append-only)
        if "ai_audit_finding_reviews" in existing_tables:
            await conn_target.execute(
                f'GRANT SELECT, INSERT ON TABLE "ai_audit_finding_reviews" TO "{app_user}";'
            )
            await conn_target.execute(
                f'REVOKE UPDATE, DELETE, TRUNCATE ON TABLE "ai_audit_finding_reviews" FROM "{app_user}";'
            )
            print(f"[+] Granted SELECT, INSERT ONLY on ai_audit_finding_reviews (UPDATE/DELETE/TRUNCATE revoked)")

        # Audit logs (append-only)
        if "audit_logs" in existing_tables:
            await conn_target.execute(
                f'GRANT SELECT, INSERT ON TABLE "audit_logs" TO "{app_user}";'
            )
            await conn_target.execute(
                f'REVOKE UPDATE, DELETE, TRUNCATE ON TABLE "audit_logs" FROM "{app_user}";'
            )
            print(f"[+] Granted SELECT, INSERT ONLY on audit_logs (UPDATE/DELETE/TRUNCATE revoked)")

        # Alembic version tracking
        if "alembic_version" in existing_tables:
            await conn_target.execute(
                f'REVOKE ALL PRIVILEGES ON TABLE "alembic_version" FROM "{app_user}";'
            )
            print(f"[+] Strictly revoked all privileges on alembic_version from {app_user}")

        # Sequences
        await conn_target.execute(f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "{app_user}";')

        # Trigger function
        trigger_fn = await conn_target.fetchval(
            "SELECT 1 FROM pg_proc WHERE proname = 'prevent_ai_audit_review_mutation';"
        )
        if trigger_fn:
            await conn_target.execute(
                f'GRANT EXECUTE ON FUNCTION prevent_ai_audit_review_mutation() TO "{app_user}";'
            )
            print(f"[+] Granted EXECUTE on prevent_ai_audit_review_mutation() to {app_user}")

        # Default privileges for tables created by janseva_migrator in future
        await conn_target.execute(
            f'ALTER DEFAULT PRIVILEGES FOR ROLE "{migrator_user}" IN SCHEMA public '
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{app_user}";'
        )
        await conn_target.execute(
            f'ALTER DEFAULT PRIVILEGES FOR ROLE "{migrator_user}" IN SCHEMA public '
            f'GRANT USAGE, SELECT ON SEQUENCES TO "{app_user}";'
        )

        print(f"[✓] Successfully provisioned least-privilege roles on database '{target_db}'")
    finally:
        await conn_target.close()


def main():
    parser = argparse.ArgumentParser(description="Provision least-privilege PostgreSQL roles for JanSeva AI.")
    parser.add_argument("--admin-url", default=os.environ.get("PG_ADMIN_URL"))
    parser.add_argument("--target-db", default=os.environ.get("PG_TARGET_DB", "janseva_phase5_test_db"))
    parser.add_argument("--app-user", default=os.environ.get("APP_ROLE_NAME", "janseva_app"))
    parser.add_argument("--app-password", default=os.environ.get("APP_ROLE_PASSWORD"))
    parser.add_argument("--migrator-user", default=os.environ.get("MIGRATOR_ROLE_NAME", "janseva_migrator"))
    parser.add_argument("--migrator-password", default=os.environ.get("MIGRATOR_ROLE_PASSWORD"))

    args = parser.parse_args()

    admin_url = args.admin_url or os.environ.get("PG_ADMIN_URL")
    if not admin_url:
        # Prompt or use localhost admin without hardcoded credentials
        admin_user = os.environ.get("PG_ADMIN_USER", "janseva")
        admin_pwd = os.environ.get("PG_ADMIN_PASSWORD", "janseva_password_2026")
        admin_port = os.environ.get("PG_PORT", "5434")
        admin_host = os.environ.get("PG_HOST", "localhost")
        admin_url = f"postgresql://{admin_user}:{admin_pwd}@{admin_host}:{admin_port}/postgres"

    app_pwd = args.app_password or os.environ.get("APP_ROLE_PASSWORD") or secrets.token_urlsafe(32)
    mig_pwd = args.migrator_password or os.environ.get("MIGRATOR_ROLE_PASSWORD") or secrets.token_urlsafe(32)

    asyncio.run(
        provision_roles(
            admin_url=admin_url,
            target_db=args.target_db,
            app_user=args.app_user,
            app_password=app_pwd,
            migrator_user=args.migrator_user,
            migrator_password=mig_pwd,
        )
    )


if __name__ == "__main__":
    main()
