"""recording status (voice anonymization)

Revision ID: 3f1a9c2d7e40
Revises: c68171f374d4
Create Date: 2026-10-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f1a9c2d7e40'
down_revision: Union[str, Sequence[str], None] = 'c68171f374d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('interview_sessions', sa.Column('recording_status', sa.String(length=16), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('interview_sessions', 'recording_status')
