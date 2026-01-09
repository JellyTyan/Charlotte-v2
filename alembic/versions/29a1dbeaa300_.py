"""empty message

Revision ID: 29a1dbeaa300
Revises:
Create Date: 2025-12-12 11:45:53.216689

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29a1dbeaa300'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Users table (using 'banned' as per original schema before rename)
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('banned', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_premium', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_lifetime_premium', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('stars_donated', sa.Integer(), server_default='0', nullable=False),
        sa.Column('premium_ends', sa.Date(), nullable=False),
        sa.Column('last_used', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )

    # User Settings
    op.create_table('user_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('lang', sa.String(length=2), server_default='en', nullable=False),
        sa.Column('send_notifications', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('send_raw', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('send_music_covers', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('send_reactions', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('ping_reaction', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('auto_caption', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('auto_translate_titles', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('title_language', sa.String(length=2), server_default='en', nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )

    # Chats
    op.create_table('chats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('owner_id', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chat_id')
    )

    # Chat Settings
    op.create_table('chat_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('lang', sa.String(length=2), server_default='en', nullable=False),
        sa.Column('send_notifications', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('send_raw', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('send_music_covers', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('send_reactions', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('ping_reaction', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('auto_caption', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('auto_translate_titles', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('title_language', sa.String(length=2), server_default='en', nullable=False),
        sa.Column('preferred_services', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('blocked_services', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('allow_playlists', sa.Boolean(), server_default='true', nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.chat_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chat_id')
    )

    # Statistics
    op.create_table('statistics',
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('service_name', sa.String(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('event_type', sa.String(length=32), nullable=False),
        sa.Column('event_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=True),
        sa.PrimaryKeyConstraint('event_id')
    )

    # Bot Settings
    op.create_table('bot_settings',
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('key')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('bot_settings')
    op.drop_table('statistics')
    op.drop_table('chat_settings')
    op.drop_table('chats')
    op.drop_table('user_settings')
    op.drop_table('users')
