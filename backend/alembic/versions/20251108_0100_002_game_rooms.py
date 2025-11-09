"""Add game rooms, participants, and game states

Revision ID: 002_game_rooms
Revises: 001_initial
Create Date: 2025-11-08 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_game_rooms'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create game_rooms table
    op.create_table(
        'game_rooms',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('code', sa.String(8), nullable=False),
        sa.Column('game_type_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('max_players', sa.Integer(), nullable=False),
        sa.Column('min_players', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['players.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['game_type_id'], ['game_types.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_game_rooms_status_created_at', 'game_rooms', ['status', 'created_at'])
    op.create_index('ix_game_rooms_game_type_id', 'game_rooms', ['game_type_id'])

    # Create game_room_participants table
    op.create_table(
        'game_room_participants',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('game_room_id', sa.String(36), nullable=False),
        sa.Column('player_id', sa.String(36), nullable=True),
        sa.Column('is_ai_agent', sa.Boolean(), nullable=False, default=False),
        sa.Column('ai_personality', sa.String(50), nullable=True),
        sa.Column('joined_at', sa.DateTime(), nullable=False),
        sa.Column('left_at', sa.DateTime(), nullable=True),
        sa.Column('replaced_by_ai', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['game_room_id'], ['game_rooms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_participants_room_left', 'game_room_participants', ['game_room_id', 'left_at'])
    op.create_index('ix_participants_player_id', 'game_room_participants', ['player_id'])

    # Create game_states table
    op.create_table(
        'game_states',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('game_room_id', sa.String(36), nullable=False),
        sa.Column('current_phase', sa.String(50), nullable=False),
        sa.Column('current_turn_player_id', sa.String(36), nullable=True),
        sa.Column('turn_number', sa.Integer(), nullable=False, default=1),
        sa.Column('game_data', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['current_turn_player_id'], ['players.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['game_room_id'], ['game_rooms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('game_room_id')
    )
    op.create_index('ix_game_states_updated_at', 'game_states', ['updated_at'])


def downgrade() -> None:
    op.drop_index('ix_game_states_updated_at', table_name='game_states')
    op.drop_table('game_states')
    op.drop_index('ix_participants_player_id', table_name='game_room_participants')
    op.drop_index('ix_participants_room_left', table_name='game_room_participants')
    op.drop_table('game_room_participants')
    op.drop_index('ix_game_rooms_game_type_id', table_name='game_rooms')
    op.drop_index('ix_game_rooms_status_created_at', table_name='game_rooms')
    op.drop_table('game_rooms')
