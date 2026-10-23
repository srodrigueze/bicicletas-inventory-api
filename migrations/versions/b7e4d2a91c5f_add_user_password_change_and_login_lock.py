"""add user password change and login lock

Revision ID: b7e4d2a91c5f
Revises: 1d5cdac391bd
Create Date: 2026-10-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e4d2a91c5f'
down_revision: Union[str, Sequence[str], None] = '1d5cdac391bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default true: every account that already exists is forced to
    # change its password at the next login, since any of them may still be
    # using the guessable password derived from the document.
    op.add_column('user', sa.Column('must_change_password', sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column('user', sa.Column('failed_login_attempts', sa.Integer(), server_default='0', nullable=False))
    op.add_column('user', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user', 'locked_until')
    op.drop_column('user', 'failed_login_attempts')
    op.drop_column('user', 'must_change_password')
