"""civil service: session elements and interview date, sign-up attribution

Revision ID: 7c2e5b1d9a63
Revises: 3f1a9c2d7e40
Create Date: 2026-10-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7c2e5b1d9a63'
down_revision: Union[str, Sequence[str], None] = '3f1a9c2d7e40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('interview_sessions', sa.Column('elements', JSON, nullable=True))
    op.add_column('interview_sessions', sa.Column('interview_date', sa.Date(), nullable=True))
    op.add_column('profiles', sa.Column('attribution', JSON, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('profiles', 'attribution')
    op.drop_column('interview_sessions', 'interview_date')
    op.drop_column('interview_sessions', 'elements')
