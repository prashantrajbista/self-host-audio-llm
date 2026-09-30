"""contact messages

Revision ID: c68171f374d4
Revises: 8909e81e355e
Create Date: 2026-09-30 13:56:08.660333

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c68171f374d4'
down_revision: Union[str, Sequence[str], None] = '8909e81e355e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table('contact_messages',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('topic', sa.String(length=32), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('user_id', sa.String(length=64), nullable=True),
    sa.Column('handled', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('contact_messages', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_contact_messages_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_contact_messages_user_id'), ['user_id'], unique=False)




def downgrade() -> None:
    """Downgrade schema."""

    with op.batch_alter_table('contact_messages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_contact_messages_user_id'))
        batch_op.drop_index(batch_op.f('ix_contact_messages_created_at'))

    op.drop_table('contact_messages')

