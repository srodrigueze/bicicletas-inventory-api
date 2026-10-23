"""add user token version and password audit actions

Revision ID: c4f1a8e63d27
Revises: b7e4d2a91c5f
Create Date: 2026-10-22 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4f1a8e63d27'
down_revision: Union[str, Sequence[str], None] = 'b7e4d2a91c5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Existing tokens carry no version claim, which the app reads as 0 — the
    # same value every existing user starts with, so current sessions survive.
    op.add_column('user', sa.Column('token_version', sa.Integer(), server_default='0', nullable=False))
    # Postgres allows adding enum values in-transaction (PG12+) as long as the
    # new values aren't used in the same transaction, which they aren't here.
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'password_change'")
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'password_reset'")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user', 'token_version')
    # Postgres has no DROP VALUE for enums; the two audit actions are left in
    # place as harmless unused values (same approach as add_bicycle).
    pass
