"""add search vector and trgm to user_saves

Revision ID: a1b2c3d4e5f6
Revises: e9f4a8c2d713
Create Date: 2026-10-02 22:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "7a8b9c0d1e2f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Enable pg_trgm extension (idempotent)
    conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

    # 2. Add generated tsvector column (Russian dictionary over label + title + caption)
    #    Wrapped in try/except-style DDL: only add if not already present.
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("user_saves")]

    if "search_vector" not in columns:
        conn.execute(sa.text("""
            ALTER TABLE user_saves
            ADD COLUMN search_vector tsvector
                GENERATED ALWAYS AS (
                    to_tsvector(
                        'russian',
                        coalesce(label, '') || ' ' ||
                        coalesce(title, '') || ' ' ||
                        coalesce(caption, '')
                    )
                ) STORED
        """))

    # 3. GIN index for tsvector (fast full-text)
    existing_indexes = [idx["name"] for idx in inspector.get_indexes("user_saves")]

    if "ix_user_saves_search_vector" not in existing_indexes:
        conn.execute(sa.text("""
            CREATE INDEX ix_user_saves_search_vector
            ON user_saves
            USING GIN (search_vector)
        """))

    # 4. GIN trigram index on label for fuzzy fallback
    if "ix_user_saves_label_trgm" not in existing_indexes:
        conn.execute(sa.text("""
            CREATE INDEX ix_user_saves_label_trgm
            ON user_saves
            USING GIN (label gin_trgm_ops)
        """))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text(
        "DROP INDEX IF EXISTS ix_user_saves_label_trgm"
    ))
    conn.execute(sa.text(
        "DROP INDEX IF EXISTS ix_user_saves_search_vector"
    ))
    conn.execute(sa.text(
        "ALTER TABLE user_saves DROP COLUMN IF EXISTS search_vector"
    ))
