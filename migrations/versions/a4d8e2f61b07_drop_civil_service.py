"""drop civil service session elements, interview date and sign-up attribution

Revision ID: a4d8e2f61b07
Revises: 7c2e5b1d9a63
Create Date: 2026-10-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a4d8e2f61b07'
down_revision: Union[str, Sequence[str], None] = '7c2e5b1d9a63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('profiles', 'attribution')
    op.drop_column('interview_sessions', 'interview_date')
    op.drop_column('interview_sessions', 'elements')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('interview_sessions', sa.Column('elements', JSON, nullable=True))
    op.add_column('interview_sessions', sa.Column('interview_date', sa.Date(), nullable=True))
    op.add_column('profiles', sa.Column('attribution', JSON, nullable=True))
