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
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
