"""interview coach schema

Revision ID: eb4bb1fcb0a5
Revises: 
Create Date: 2026-09-30 00:09:43.992219

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'eb4bb1fcb0a5'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table('cvs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.String(length=64), nullable=False),
    sa.Column('file_name', sa.String(length=255), nullable=False),
    sa.Column('storage_key', sa.String(length=512), nullable=True),
    sa.Column('raw_text', sa.Text(), nullable=False),
    sa.Column('cv_profile', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('cvs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_cvs_user_id'), ['user_id'], unique=False)

    op.create_table('profiles',
    sa.Column('user_id', sa.String(length=64), nullable=False),
    sa.Column('credits', sa.Integer(), nullable=False),
    sa.Column('pass_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('credits >= 0', name='credits_non_negative'),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('interview_sessions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.String(length=64), nullable=False),
    sa.Column('pack_id', sa.String(length=64), nullable=False),
    sa.Column('role', sa.String(length=80), nullable=False),
    sa.Column('seniority', sa.String(length=16), nullable=False),
    sa.Column('interview_type', sa.String(length=16), nullable=False),
    sa.Column('cv_id', sa.Uuid(), nullable=True),
    sa.Column('jd_text', sa.Text(), nullable=True),
    sa.Column('plan', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('charged', sa.Boolean(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('record', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('report', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('overall_score', sa.Integer(), nullable=True),
    sa.Column('verdict', sa.String(length=32), nullable=True),
    sa.Column('recording_key', sa.String(length=512), nullable=True),
    sa.Column('share_slug', sa.String(length=32), nullable=True),
    sa.Column('share_fields', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('is_public', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("status in ('created', 'live', 'scoring', 'scored', 'failed', 'abandoned')", name='valid_status'),
    sa.ForeignKeyConstraint(['cv_id'], ['cvs.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('share_slug')
    )
    with op.batch_alter_table('interview_sessions', schema=None) as batch_op:
        batch_op.create_index('ix_sessions_user_created', ['user_id', 'created_at'], unique=False)




def downgrade() -> None:
    """Downgrade schema."""

    with op.batch_alter_table('interview_sessions', schema=None) as batch_op:
        batch_op.drop_index('ix_sessions_user_created')

    op.drop_table('interview_sessions')
    op.drop_table('profiles')
    with op.batch_alter_table('cvs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_cvs_user_id'))

    op.drop_table('cvs')

