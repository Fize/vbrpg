"""Add game_sessions table

Revision ID: 003_game_sessions
Revises: 002_game_rooms
Create Date: 2025-11-08 19:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_game_sessions'
down_revision: Union[str, None] = '002_game_rooms'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create game_sessions table for historical game records."""
    op.create_table(
        'game_sessions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('game_room_id', sa.String(36), nullable=False),
        sa.Column('game_type_id', sa.String(36), nullable=False),
        sa.Column('winner_id', sa.String(36), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('participants_count', sa.Integer(), nullable=False),
        sa.Column('ai_agents_count', sa.Integer(), nullable=False),
        sa.Column('final_state', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['game_room_id'], ['game_rooms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['game_type_id'], ['game_types.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['winner_id'], ['players.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for common queries
    op.create_index('ix_game_sessions_game_room_id', 'game_sessions', ['game_room_id'])
    op.create_index('ix_game_sessions_game_type_id_completed_at', 'game_sessions', ['game_type_id', 'completed_at'])
    op.create_index('ix_game_sessions_winner_id', 'game_sessions', ['winner_id'])
    op.create_index('ix_game_sessions_started_at', 'game_sessions', ['started_at'])


def downgrade() -> None:
    """Drop game_sessions table."""
    op.drop_index('ix_game_sessions_started_at', table_name='game_sessions')
    op.drop_index('ix_game_sessions_winner_id', table_name='game_sessions')
    op.drop_index('ix_game_sessions_game_type_id_completed_at', table_name='game_sessions')
    op.drop_index('ix_game_sessions_game_room_id', table_name='game_sessions')
    op.drop_table('game_sessions')
