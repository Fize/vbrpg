"""Initial schema for VBRPG backend.

Revision ID: 001_initial
Revises: 
Create Date: 2025-11-29

Creates all tables based on current model definitions:
- players: Player accounts (guest and registered)
- player_profiles: Extended player statistics
- sessions: User session management
- ai_agents: AI opponent configurations
- game_rooms: Game room management
- game_room_participants: Players/AI in game rooms
- game_states: Current game state
- game_sessions: Historical game records
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import JSON


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables."""
    
    # ==========================================================================
    # players table
    # ==========================================================================
    op.create_table(
        'players',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('username', sa.String(50), unique=True, nullable=False),
        sa.Column('is_guest', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_active', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
    )
    op.create_index('idx_players_username', 'players', ['username'])
    op.create_index('idx_players_is_guest', 'players', ['is_guest'])

    # ==========================================================================
    # player_profiles table
    # ==========================================================================
    op.create_table(
        'player_profiles',
        sa.Column('player_id', sa.String(36), sa.ForeignKey('players.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('total_games', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_wins', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('favorite_game_id', sa.String(36), nullable=True),
        sa.Column('ui_preferences', JSON, nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
    )

    # ==========================================================================
    # sessions table
    # ==========================================================================
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(128), unique=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_active', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
    )
    op.create_index('idx_sessions_session_id', 'sessions', ['session_id'])
    op.create_index('idx_sessions_expires_at', 'sessions', ['expires_at'])

    # ==========================================================================
    # ai_agents table
    # ==========================================================================
    op.create_table(
        'ai_agents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('username', sa.String(50), unique=True, nullable=False),
        sa.Column('personality_type', sa.String(30), nullable=False),
        sa.Column('difficulty_level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_ai_agents_personality', 'ai_agents', ['personality_type'])

    # ==========================================================================
    # game_rooms table
    # ==========================================================================
    op.create_table(
        'game_rooms',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('code', sa.String(8), unique=True, nullable=False),
        sa.Column('game_type_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('max_players', sa.Integer(), nullable=False),
        sa.Column('min_players', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('user_role', sa.String(50), nullable=True),
        sa.Column('is_spectator_mode', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('current_participant_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ai_agent_counter', sa.Integer(), nullable=False, server_default='0'),
    )
    op.create_index('idx_game_rooms_code', 'game_rooms', ['code'])
    op.create_index('idx_game_rooms_status', 'game_rooms', ['status'])
    op.create_index('idx_game_rooms_game_type_id', 'game_rooms', ['game_type_id'])

    # ==========================================================================
    # game_room_participants table
    # ==========================================================================
    op.create_table(
        'game_room_participants',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('game_room_id', sa.String(36), sa.ForeignKey('game_rooms.id', ondelete='CASCADE'), nullable=False),
        sa.Column('player_id', sa.String(36), sa.ForeignKey('players.id', ondelete='SET NULL'), nullable=True),
        sa.Column('session_id', sa.String(128), sa.ForeignKey('sessions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_ai_agent', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_owner', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('ai_personality', sa.String(50), nullable=True),
        sa.Column('replaced_by_ai', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('joined_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('left_at', sa.DateTime(), nullable=True),
    )
    op.create_index('idx_participants_game_room', 'game_room_participants', ['game_room_id'])
    op.create_index('idx_participants_player', 'game_room_participants', ['player_id'])
    op.create_index('idx_participants_session', 'game_room_participants', ['session_id'])

    # ==========================================================================
    # game_states table
    # ==========================================================================
    op.create_table(
        'game_states',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('game_room_id', sa.String(36), sa.ForeignKey('game_rooms.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('current_phase', sa.String(50), nullable=False, server_default='setup'),
        sa.Column('current_turn', sa.String(36), nullable=True),
        sa.Column('current_turn_player_id', sa.String(36), sa.ForeignKey('players.id', ondelete='SET NULL'), nullable=True),
        sa.Column('turn_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('game_data', JSON, nullable=False),
        sa.Column('is_paused', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('last_updated', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_game_states_game_room', 'game_states', ['game_room_id'])

    # ==========================================================================
    # game_sessions table (historical records)
    # ==========================================================================
    op.create_table(
        'game_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('game_room_id', sa.String(36), sa.ForeignKey('game_rooms.id', ondelete='CASCADE'), nullable=False),
        sa.Column('game_type_id', sa.String(36), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('participants_count', sa.Integer(), nullable=False),
        sa.Column('ai_agents_count', sa.Integer(), nullable=False),
        sa.Column('user_won', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('final_score', sa.Integer(), nullable=True),
        sa.Column('final_state', JSON, nullable=False),
    )
    op.create_index('idx_game_sessions_game_room', 'game_sessions', ['game_room_id'])
    op.create_index('idx_game_sessions_game_type', 'game_sessions', ['game_type_id'])
    op.create_index('idx_game_sessions_started_at', 'game_sessions', ['started_at'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('game_sessions')
    op.drop_table('game_states')
    op.drop_table('game_room_participants')
    op.drop_table('game_rooms')
    op.drop_table('ai_agents')
    op.drop_table('sessions')
    op.drop_table('player_profiles')
    op.drop_table('players')
