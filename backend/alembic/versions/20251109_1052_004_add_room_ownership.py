"""Add room ownership and participant tracking

Revision ID: 004_add_room_ownership
Revises: 003_game_sessions
Create Date: 2025-11-09 10:52:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '004_add_room_ownership'
down_revision: Union[str, None] = '003_game_sessions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add owner tracking and participant counting to game rooms."""
    # Add new columns to game_rooms table
    op.add_column('game_rooms', sa.Column('owner_id', sa.String(36), nullable=True))
    op.add_column('game_rooms', sa.Column('current_participant_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('game_rooms', sa.Column('ai_agent_counter', sa.Integer(), nullable=False, server_default='0'))
    
    # Backfill owner_id from first participant in existing rooms
    connection = op.get_bind()
    connection.execute(text("""
        UPDATE game_rooms
        SET owner_id = (
            SELECT player_id
            FROM game_room_participants
            WHERE game_room_participants.game_room_id = game_rooms.id
            AND game_room_participants.left_at IS NULL
            ORDER BY joined_at ASC
            LIMIT 1
        )
        WHERE EXISTS (
            SELECT 1
            FROM game_room_participants
            WHERE game_room_participants.game_room_id = game_rooms.id
            AND game_room_participants.left_at IS NULL
        )
    """))
    
    # Backfill current_participant_count
    connection.execute(text("""
        UPDATE game_rooms
        SET current_participant_count = (
            SELECT COUNT(*)
            FROM game_room_participants
            WHERE game_room_participants.game_room_id = game_rooms.id
            AND game_room_participants.left_at IS NULL
        )
    """))
    
    # Create foreign key and index for owner_id
    op.create_foreign_key(
        'fk_game_rooms_owner_id',
        'game_rooms',
        'players',
        ['owner_id'],
        ['id'],
        ondelete='SET NULL'  

def downgrade() -> None:
    """Remove room ownership tracking."""
    op.drop_index('idx_room_owner', table_name='game_rooms')
    op.drop_constraint('fk_game_rooms_owner_id', 'game_rooms', type_='foreignkey')
    op.drop_column('game_rooms', 'ai_agent_counter')
    op.drop_column('game_rooms', 'current_participant_count')
    op.drop_column('game_rooms', 'owner_id')
