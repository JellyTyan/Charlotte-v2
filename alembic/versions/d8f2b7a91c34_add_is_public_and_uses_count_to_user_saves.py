"""add is_public and uses_count to user_saves

Revision ID: d8f2b7a91c34
Revises: c1e87f23a9b1
Create Date: 2026-09-21 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8f2b7a91c34'
down_revision: Union[str, Sequence[str], None] = 'c1e87f23a9b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'user_saves' in tables:
        cols = [c['name'] for c in inspector.get_columns('user_saves')]
        if 'is_public' not in cols:
            op.add_column('user_saves', sa.Column('is_public', sa.Boolean(), server_default='false', nullable=False))
            op.create_index(op.f('ix_user_saves_is_public'), 'user_saves', ['is_public'], unique=False)
        if 'is_approved' not in cols:
            op.add_column('user_saves', sa.Column('is_approved', sa.Boolean(), server_default='false', nullable=False))
            op.create_index(op.f('ix_user_saves_is_approved'), 'user_saves', ['is_approved'], unique=False)
        if 'uses_count' not in cols:
            op.add_column('user_saves', sa.Column('uses_count', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'user_saves' in tables:
        cols = [c['name'] for c in inspector.get_columns('user_saves')]
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('user_saves')]
        if 'ix_user_saves_is_public' in existing_indexes:
            op.drop_index(op.f('ix_user_saves_is_public'), table_name='user_saves')
        if 'is_public' in cols:
            op.drop_column('user_saves', 'is_public')
        if 'uses_count' in cols:
            op.drop_column('user_saves', 'uses_count')
