"""add user_saves table and audio cache index

Revision ID: c1e87f23a9b1
Revises: 4b154c4760db
Create Date: 2026-09-20 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1e87f23a9b1'
down_revision: Union[str, Sequence[str], None] = 'b8669ea8a40b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'user_saves' not in tables:
        op.create_table(
            'user_saves',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('label', sa.String(length=128), nullable=False),
            sa.Column('telegram_file_id', sa.String(), nullable=False),
            sa.Column('media_type', sa.String(length=16), nullable=False),
            sa.Column('title', sa.String(length=256), nullable=True),
            sa.Column('caption', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_user_saves_user_id'), 'user_saves', ['user_id'], unique=False)
        op.create_index('ix_user_saves_user_label', 'user_saves', ['user_id', 'label'], unique=False)

    existing_indexes = [idx['name'] for idx in inspector.get_indexes('mediacache')]
    if 'ix_mediacache_audio' not in existing_indexes:
        op.create_index(
            'ix_mediacache_audio',
            'mediacache',
            ['created_at'],
            unique=False,
            postgresql_where=sa.text("media_type = 'audio' AND telegram_file_id IS NOT NULL")
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('mediacache')]
    if 'ix_mediacache_audio' in existing_indexes:
        op.drop_index('ix_mediacache_audio', table_name='mediacache')

    tables = inspector.get_table_names()
    if 'user_saves' in tables:
        op.drop_index('ix_user_saves_user_label', table_name='user_saves')
        op.drop_index(op.f('ix_user_saves_user_id'), table_name='user_saves')
        op.drop_table('user_saves')
