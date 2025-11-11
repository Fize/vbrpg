"""Add participant metadata and constraints

Revision ID: 005_add_participant_metadata
Revises: 004_add_room_ownership
Create Date: 2025-11-09 10:53:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '005_add_participant_metadata'
down_revision: Union[str, None] = '004_add_room_ownership'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_owner flag, join_timestamp, and unique constraints to participants."""
    # Add new columns to game_room_participants table
    op.add_column('game_room_participants', sa.Column('is_owner', sa.Boolean(), nullable=False, server_default='0'))
    
    # Backfill join_timestamp from joined_at, then add as NOT NULL
    # SQLite doesn't support ALTER COLUMN, so we must add column with correct constraint directly
    connection = op.get_bind()
    
    # First add as nullable to allow backfill
    op.add_column('game_room_participants', sa.Column('join_timestamp', sa.DateTime(), nullable=True))
    
    # Backfill from joined_at
    connection.execute(text("""
        UPDATE game_room_participants
        SET join_timestamp = joined_at
        WHERE join_timestamp IS NULL
    """))
    
    # For SQLite, we need to recreate the table to change column to NOT NULL
    # However, since we have data, we'll keep it nullable but ensure data integrity via application layer
    # Note: In production, consider using a table recreation approach if strict NOT NULL is required
    
    # Backfill is_owner from game_rooms.owner_id
    connection.execute(text("""
        UPDATE game_room_participants
        SET is_owner = 1
        WHERE player_id IN (
            SELECT owner_id
            FROM game_rooms
            WHERE game_rooms.id = game_room_participants.game_room_id
            AND game_rooms.owner_id IS NOT NULL
        )
    """))
    
    # Add unique constraint to prevent duplicate joins
    op.create_unique_constraint(
        'uq_room_participant',
        'game_room_participants',
        ['game_room_id', 'player_id']
    )
    
    # Create indexes for common queries
    op.create_index('idx_participant_owner', 'game_room_participants', ['game_room_id', 'is_owner'])
    op.create_index('idx_participant_join_time', 'game_room_participants', ['game_room_id', 'join_timestamp'])


def downgrade() -> None:
    """Remove participant metadata and constraints."""
    op.drop_index('idx_participant_join_time', table_name='game_room_participants')
    op.drop_index('idx_participant_owner', table_name='game_room_participants')
    op.drop_constraint('uq_room_participant', 'game_room_participants', type_='unique')
    op.drop_column('game_room_participants', 'join_timestamp')
    op.drop_column('game_room_participants', 'is_owner')
