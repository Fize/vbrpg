"""Initial schema with players, player_profiles, and game_types

Revision ID: 001_initial
Revises: 
Create Date: 2025-11-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create game_types table
    op.create_table(
        'game_types',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('rules_summary', sa.Text(), nullable=False),
        sa.Column('min_players', sa.Integer(), nullable=False),
        sa.Column('max_players', sa.Integer(), nullable=False),
        sa.Column('avg_duration_minutes', sa.Integer(), nullable=False),
        sa.Column('is_available', sa.Boolean(), nullable=False, default=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('ix_game_types_is_available', 'game_types', ['is_available'])

    # Create players table
    op.create_table(
        'players',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('is_guest', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_active', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )
    op.create_index('ix_players_is_guest_expires_at', 'players', ['is_guest', 'expires_at'])
    op.create_index('ix_players_last_active', 'players', ['last_active'])

    # Create player_profiles table
    op.create_table(
        'player_profiles',
        sa.Column('player_id', sa.String(36), nullable=False),
        sa.Column('total_games', sa.Integer(), nullable=False, default=0),
        sa.Column('total_wins', sa.Integer(), nullable=False, default=0),
        sa.Column('favorite_game_id', sa.String(36), nullable=True),
        sa.Column('ui_preferences', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['favorite_game_id'], ['game_types.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('player_id')
    )


def downgrade() -> None:
    op.drop_table('player_profiles')
    op.drop_index('ix_players_last_active', table_name='players')
    op.drop_index('ix_players_is_guest_expires_at', table_name='players')
    op.drop_table('players')
    op.drop_index('ix_game_types_is_available', table_name='game_types')
    op.drop_table('game_types')
