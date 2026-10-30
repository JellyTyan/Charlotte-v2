"""users.language_code: the Telegram client language, to see which translations are worth adding

Revision ID: f5a6b7c8d9e0
Revises: e3f4a5b6c7d8
Create Date: 2026-10-30 18:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "f5a6b7c8d9e0"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("language_code", sa.String(16), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "language_code")
