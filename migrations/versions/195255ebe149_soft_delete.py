"""soft delete

Revision ID: 195255ebe149
Revises: eb4bb1fcb0a5
Create Date: 2026-09-30 09:21:51.065572

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '195255ebe149'
down_revision: Union[str, Sequence[str], None] = 'eb4bb1fcb0a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    with op.batch_alter_table('cvs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table('interview_sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))




def downgrade() -> None:
    """Downgrade schema."""

    with op.batch_alter_table('interview_sessions', schema=None) as batch_op:
        batch_op.drop_column('deleted_at')

    with op.batch_alter_table('cvs', schema=None) as batch_op:
        batch_op.drop_column('deleted_at')


