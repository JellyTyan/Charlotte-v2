"""mediacache.data json -> jsonb, trigram indexes for music and saves search

Revision ID: c4d5e6f7a8b9
Revises: b7c8d9e0f1a2
Create Date: 2026-10-25 12:00:00.000000
"""
from alembic import op

revision = "c4d5e6f7a8b9"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None

TRGM_FUNCS = ("strict_word_similarity", "strict_word_similarity_op", "strict_word_similarity_commutator_op", "similarity")
# must match crud.MUSIC_DOC exactly, or the planner won't use the index
MUSIC_DOC = "left(trim(coalesce(data->>'author', '')) || ' ' || coalesce(data->>'title', ''), 100)"
# same for crud.SAVES_DOC
SAVES_DOC = "left(label || ' ' || coalesce(title, '') || ' ' || coalesce(caption, ''), 300)"


def upgrade() -> None:
    # json is re-parsed on every data->>'key'; jsonb is stored parsed (music search 2-3x faster)
    op.execute("ALTER TABLE mediacache ALTER COLUMN data TYPE jsonb USING data::jsonb")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        f"CREATE INDEX ix_mediacache_doc_trgm ON mediacache USING gin ({MUSIC_DOC} gin_trgm_ops)"
    )
    op.execute(f"CREATE INDEX ix_user_saves_doc_trgm ON user_saves USING gin (({SAVES_DOC}) gin_trgm_ops)")
    # pg_trgm declares its functions as cost 1, so the planner would rather filter every audio row
    # (5 query variants x strict_word_similarity each) than use the trigram index: 140 ms vs 20 ms
    for fn in TRGM_FUNCS:
        op.execute(f"ALTER FUNCTION {fn}(text, text) COST 100")


def downgrade() -> None:
    for fn in TRGM_FUNCS:
        op.execute(f"ALTER FUNCTION {fn}(text, text) COST 1")
    op.execute("DROP INDEX IF EXISTS ix_user_saves_doc_trgm")
    op.execute("DROP INDEX IF EXISTS ix_mediacache_doc_trgm")
    op.execute("ALTER TABLE mediacache ALTER COLUMN data TYPE json USING data::json")
