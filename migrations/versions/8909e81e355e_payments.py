"""payments

Revision ID: 8909e81e355e
Revises: 195255ebe149
Create Date: 2026-09-30 10:44:58.508897

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8909e81e355e'
down_revision: Union[str, Sequence[str], None] = '195255ebe149'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table('payments',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.String(length=64), nullable=False),
    sa.Column('provider', sa.String(length=16), nullable=False),
    sa.Column('event_id', sa.String(length=255), nullable=False),
    sa.Column('session_id', sa.String(length=255), nullable=False),
    sa.Column('product', sa.String(length=32), nullable=False),
    sa.Column('amount_total', sa.Integer(), nullable=True),
    sa.Column('currency', sa.String(length=8), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('event_id'),
    sa.UniqueConstraint('session_id')
    )
    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_payments_user_id'), ['user_id'], unique=False)




def downgrade() -> None:
    """Downgrade schema."""

    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_payments_user_id'))

    op.drop_table('payments')

