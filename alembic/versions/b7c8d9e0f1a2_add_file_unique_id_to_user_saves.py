"""add file_unique_id to user_saves

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-10-04 23:50:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "b7c8d9e0f1a2"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Старые строки остаются с NULL: их дубли по-прежнему ловятся по telegram_file_id
    op.add_column("user_saves", sa.Column("file_unique_id", sa.String(length=64), nullable=True))
    op.create_index("ix_user_saves_file_unique_id", "user_saves", ["file_unique_id"])


def downgrade() -> None:
    op.drop_index("ix_user_saves_file_unique_id", table_name="user_saves")
    op.drop_column("user_saves", "file_unique_id")
