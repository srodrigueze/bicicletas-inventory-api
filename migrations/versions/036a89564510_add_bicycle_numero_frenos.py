"""add bicycle numero_frenos

Revision ID: 036a89564510
Revises: a6c02f8bcfac
Create Date: 2026-10-02 12:29:45.771149

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '036a89564510'
down_revision: Union[str, Sequence[str], None] = 'a6c02f8bcfac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Manual adjustment: existing bicycle rows predate this column, so a
    # server_default is required to backfill them (assumes 2 brakes; review
    # the existing inventory manually afterward — same criterion already used
    # for rueditas_asistencia/tiene_pedales in DEV-002).
    op.add_column('bicycle', sa.Column('numero_frenos', sa.Integer(), nullable=False, server_default='2'))
    op.alter_column('bicycle', 'numero_frenos', server_default=None)
    op.create_check_constraint(
        'numero_frenos_range', 'bicycle', 'numero_frenos >= 0 AND numero_frenos <= 2'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('numero_frenos_range', 'bicycle', type_='check')
    op.drop_column('bicycle', 'numero_frenos')
