"""add public_saves_bans table

Revision ID: 7a8b9c0d1e2f
Revises: e9f4a8c2d713
"""
from alembic import op
import sqlalchemy as sa

revision = "7a8b9c0d1e2f"
down_revision = "e9f4a8c2d713"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "public_saves_bans" not in tables:
        op.create_table(
            "public_saves_bans",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id"),
        )
        op.create_index("ix_public_saves_bans_user_id", "public_saves_bans", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_public_saves_bans_user_id", table_name="public_saves_bans")
    op.drop_table("public_saves_bans")
