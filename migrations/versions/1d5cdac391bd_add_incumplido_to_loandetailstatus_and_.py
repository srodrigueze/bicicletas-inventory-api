"""add incumplido to loandetailstatus and auditaction

Revision ID: 1d5cdac391bd
Revises: 036a89564510
Create Date: 2026-10-03 11:44:12.843614

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1d5cdac391bd'
down_revision: Union[str, Sequence[str], None] = '036a89564510'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Postgres allows adding enum values in-transaction (PG12+) as long as the
    # new value isn't used in the same transaction, which it isn't here.
    op.execute("ALTER TYPE loandetailstatus ADD VALUE IF NOT EXISTS 'incumplido'")
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'incumplido'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres has no DROP VALUE for enums; removing 'incumplido' would
    # require recreating both types. Left as a no-op — harmless unused value.
    pass
