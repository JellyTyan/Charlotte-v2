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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "user_saves" in tables:
        cols = [c["name"] for c in inspector.get_columns("user_saves")]
        if "is_approved" not in cols:
            op.add_column(
                "user_saves",
                sa.Column("is_approved", sa.Boolean(), server_default=sa.true(), nullable=False),
            )
            op.alter_column("user_saves", "is_approved", server_default=None)

        indexes = [idx["name"] for idx in inspector.get_indexes("user_saves")]
        if "ix_user_saves_is_approved" not in indexes:
            op.create_index("ix_user_saves_is_approved", "user_saves", ["is_approved"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "user_saves" in tables:
        indexes = [idx["name"] for idx in inspector.get_indexes("user_saves")]
        if "ix_user_saves_is_approved" in indexes:
            op.drop_index("ix_user_saves_is_approved", table_name="user_saves")
        cols = [c["name"] for c in inspector.get_columns("user_saves")]
        if "is_approved" in cols:
            op.drop_column("user_saves", "is_approved")
