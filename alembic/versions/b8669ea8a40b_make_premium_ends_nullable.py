"""make premium_ends nullable

Revision ID: b8669ea8a40b
Revises: a8311dee8ec2
Create Date: 2026-05-07 21:51:14.209529

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8669ea8a40b'
down_revision: Union[str, Sequence[str], None] = 'a8311dee8ec2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('users', 'premium_ends',
               existing_type=sa.Date(),
               nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('users', 'premium_ends',
               existing_type=sa.Date(),
               nullable=False)
