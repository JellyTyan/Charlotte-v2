"""track users who blocked the bot and the bot's status in chats

Revision ID: d1e2f3a4b5c6
Revises: c4d5e6f7a8b9
Create Date: 2026-10-26 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "d1e2f3a4b5c6"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
    # last_used was never updated after insert, so it is the registration date
    op.execute("UPDATE users SET created_at = last_used::timestamptz WHERE last_used IS NOT NULL")
    # from now on last_used tracks activity; seed it with the last download we know of
    op.execute("""
        UPDATE users u SET last_used = s.last_event
        FROM (SELECT user_id, max(event_time)::date AS last_event FROM statistics GROUP BY user_id) s
        WHERE s.user_id = u.user_id AND (u.last_used IS NULL OR s.last_event > u.last_used)
    """)

    op.add_column("chats", sa.Column("left_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("chats", sa.Column("bot_status", sa.String(16), nullable=True))
    op.add_column("chats", sa.Column("can_post", sa.Boolean(), nullable=True))
    op.add_column("chats", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for col in ("created_at", "can_post", "bot_status", "left_at"):
        op.drop_column("chats", col)
    op.drop_column("users", "created_at")
    op.drop_column("users", "blocked_at")
