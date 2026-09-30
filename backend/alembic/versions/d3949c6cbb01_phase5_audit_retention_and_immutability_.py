"""phase5_audit_retention_and_immutability_triggers

Revision ID: d3949c6cbb01
Revises: eca52746b5a4
Create Date: 2026-09-29 10:58:32.910619

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3949c6cbb01'
down_revision: Union[str, Sequence[str], None] = 'eca52746b5a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: enforce RESTRICT foreign keys and install audit review immutability trigger."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # 1. Update foreign keys from CASCADE to RESTRICT to enforce audit retention
        op.drop_constraint('ai_audit_findings_complaint_id_fkey', 'ai_audit_findings', type_='foreignkey')
        op.create_foreign_key(
            'ai_audit_findings_complaint_id_fkey',
            'ai_audit_findings',
            'complaints',
            ['complaint_id'],
            ['id'],
            ondelete='RESTRICT'
        )

        op.drop_constraint('ai_audit_finding_reviews_finding_id_fkey', 'ai_audit_finding_reviews', type_='foreignkey')
        op.create_foreign_key(
            'ai_audit_finding_reviews_finding_id_fkey',
            'ai_audit_finding_reviews',
            'ai_audit_findings',
            ['finding_id'],
            ['id'],
            ondelete='RESTRICT'
        )

        # 2. Create the immutable audit review trigger function
        op.execute("""
            CREATE OR REPLACE FUNCTION prevent_ai_audit_review_mutation()
            RETURNS trigger AS $$
            BEGIN
                IF TG_OP = 'UPDATE' THEN
                    RAISE EXCEPTION 'AIAuditFindingReview records are strictly append-only and cannot be updated (id: %)', OLD.id
                        USING ERRCODE = 'integrity_constraint_violation';
                ELSIF TG_OP = 'DELETE' THEN
                    RAISE EXCEPTION 'AIAuditFindingReview records are permanent audit logs and cannot be deleted (id: %)', OLD.id
                        USING ERRCODE = 'integrity_constraint_violation';
                END IF;
                RETURN NULL;
            END;
            $$ LANGUAGE plpgsql;
        """)

        # 3. Create the BEFORE UPDATE OR DELETE trigger on ai_audit_finding_reviews
        op.execute("DROP TRIGGER IF EXISTS trg_ai_audit_review_prevent_mutation ON ai_audit_finding_reviews;")
        op.execute("""
            CREATE TRIGGER trg_ai_audit_review_prevent_mutation
            BEFORE UPDATE OR DELETE ON ai_audit_finding_reviews
            FOR EACH ROW
            EXECUTE FUNCTION prevent_ai_audit_review_mutation();
        """)


def downgrade() -> None:
    """Downgrade schema: remove trigger and function, revert foreign keys to CASCADE."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # 1. Remove trigger and function
        op.execute("DROP TRIGGER IF EXISTS trg_ai_audit_review_prevent_mutation ON ai_audit_finding_reviews;")
        op.execute("DROP FUNCTION IF EXISTS prevent_ai_audit_review_mutation();")

        # 2. Revert foreign keys to CASCADE
        op.drop_constraint('ai_audit_finding_reviews_finding_id_fkey', 'ai_audit_finding_reviews', type_='foreignkey')
        op.create_foreign_key(
            'ai_audit_finding_reviews_finding_id_fkey',
            'ai_audit_finding_reviews',
            'ai_audit_findings',
            ['finding_id'],
            ['id'],
            ondelete='CASCADE'
        )

        op.drop_constraint('ai_audit_findings_complaint_id_fkey', 'ai_audit_findings', type_='foreignkey')
        op.create_foreign_key(
            'ai_audit_findings_complaint_id_fkey',
            'ai_audit_findings',
            'complaints',
            ['complaint_id'],
            ['id'],
            ondelete='CASCADE'
        )
