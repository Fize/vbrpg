"""Single user refactor: Add Session model and update GameType.

Revision ID: 20251126_single_user
Revises: 
Create Date: 2025-11-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251126_single_user"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add Session model, update GameType, create AIAgent, update other models."""
    # Create sessions table
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_active", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id")
    )
    
    # Create ai_agents table
    op.create_table(
        "ai_agents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("personality_type", sa.String(length=30), nullable=False),
        sa.Column("difficulty_level", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username")
    )
    
    # Add AI-related columns to game_types
    op.add_column("game_types", sa.Column("min_ai_opponents", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("game_types", sa.Column("max_ai_opponents", sa.Integer(), nullable=False, server_default="3"))
    op.add_column("game_types", sa.Column("supports_spectating", sa.Boolean(), nullable=False, server_default="true"))
    
    # Update game_rooms table
    op.drop_column("game_rooms", "created_by")  # Remove player references
    op.drop_column("game_rooms", "owner_id")     # Remove player references
    op.drop_column("game_rooms", "current_participant_count")  # Simplify tracking
    
    # Update game_room_participants table
    op.alter_column("game_room_participants", "player_id", new_column_name="session_id")
    op.drop_column("game_room_participants", "is_owner")
    op.drop_column("game_room_participants", "join_timestamp")
    op.drop_column("game_room_participants", "replaced_by_ai")
    op.create_foreign_key("game_room_participants", "session_id", "sessions", "id")
    
    # Update game_states table
    op.drop_column("game_states", "current_phase")
    op.alter_column("game_states", "current_turn_player_id", new_column_name="current_turn")
    op.add_column("game_states", sa.Column("is_paused", sa.Boolean(), nullable=False, server_default="false"))
    op.drop_column("game_states", "updated_at")
    op.add_column("game_states", sa.Column("last_updated", sa.DateTime(), nullable=False))
    op.drop_constraint("fk_game_states_current_turn_player_id_players", "game_states", type_="foreignkey")
    
    # Update game_sessions table
    op.drop_column("game_sessions", "winner_id")  # Remove player references
    op.add_column("game_sessions", sa.Column("user_won", sa.Boolean(), nullable=False))
    op.add_column("game_sessions", sa.Column("final_score", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Revert all changes back to multi-user model."""
    # Drop new tables
    op.drop_table("sessions")
    op.drop_table("ai_agents")
    
    # Revert game_types
    op.drop_column("game_types", "supports_spectating")
    op.drop_column("game_types", "max_ai_opponents")
    op.drop_column("game_types", "min_ai_opponents")
    
    # Revert game_rooms
    op.add_column("game_rooms", sa.Column("created_by", sa.String(length=36), nullable=True))
    op.add_column("game_rooms", sa.Column("owner_id", sa.String(length=36), nullable=True))
    op.add_column("game_rooms", sa.Column("current_participant_count", sa.Integer(), nullable=False))
    
    # Revert game_room_participants
    op.alter_column("game_room_participants", "session_id", new_column_name="player_id")
    op.add_column("game_room_participants", sa.Column("is_owner", sa.Boolean(), nullable=False))
    op.add_column("game_room_participants", sa.Column("join_timestamp", sa.DateTime(), nullable=True))
    op.add_column("game_room_participants", sa.Column("replaced_by_ai", sa.Boolean(), nullable=False))
    
    # Revert game_states
    op.add_column("game_states", sa.Column("current_phase", sa.String(length=50), nullable=False))
    op.alter_column("game_states", "current_turn", new_column_name="current_turn_player_id")
    op.drop_column("game_states", "is_paused")
    op.add_column("game_states", sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.drop_column("game_states", "last_updated")
    
    # Revert game_sessions
    op.add_column("game_sessions", sa.Column("winner_id", sa.String(length=36), nullable=True))
    op.drop_column("game_sessions", "user_won")
    op.drop_column("game_sessions", "final_score")