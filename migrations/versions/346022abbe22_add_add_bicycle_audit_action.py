"""add add_bicycle audit action

Revision ID: 346022abbe22
Revises: 3875e51a0f2c
Create Date: 2026-09-28 17:11:32.163893

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '346022abbe22'
down_revision: Union[str, Sequence[str], None] = '3875e51a0f2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Postgres allows adding enum values in-transaction (PG12+) as long as the
    # new value isn't used in the same transaction, which it isn't here.
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'add_bicycle'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres has no DROP VALUE for enums; removing 'add_bicycle' would
    # require recreating the type. Left as a no-op — harmless unused value.
    pass
