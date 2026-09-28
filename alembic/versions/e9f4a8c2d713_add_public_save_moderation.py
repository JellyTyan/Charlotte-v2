"""add moderation status for public saves

Revision ID: e9f4a8c2d713
Revises: d8f2b7a91c34
"""
from alembic import op
import sqlalchemy as sa

revision = "e9f4a8c2d713"
down_revision = "d8f2b7a91c34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_saves",
        sa.Column("is_approved", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.create_index("ix_user_saves_is_approved", "user_saves", ["is_approved"])
    op.alter_column("user_saves", "is_approved", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_user_saves_is_approved", table_name="user_saves")
    op.drop_column("user_saves", "is_approved")
