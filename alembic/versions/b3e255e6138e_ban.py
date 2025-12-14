"""ban

Revision ID: b3e255e6138e
Revises: 29a1dbeaa300
Create Date: 2025-12-14 14:59:06.371772

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3e255e6138e'
down_revision: Union[str, Sequence[str], None] = '29a1dbeaa300'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename banned to is_banned (no need to add/drop, just rename)
    op.alter_column('users', 'banned', new_column_name='is_banned')


def downgrade() -> None:
    """Downgrade schema."""
    # Rename is_banned back to banned
    op.alter_column('users', 'is_banned', new_column_name='banned')
