"""Game-related models for single-user gaming.

This module consolidates all game-related database models:
- GameType: Game catalog with AI opponent support information
- GameRoom: Simplified game room for single-user gaming experience
- GameRoomParticipant: Join table linking sessions and AI agents to game rooms
- GameState: Current state of a single-user game
- GameSession: Historical record of a single-user game session
"""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from src.models.user import Player, Session


# =============================================================================
# GameType
# =============================================================================

class GameType(Base, UUIDMixin):
    """Game catalog with AI opponent support information."""

    __tablename__ = "game_types"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rules_summary: Mapped[str] = mapped_column(Text, nullable=False)
    min_players: Mapped[int] = mapped_column(Integer, nullable=False)
    max_players: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # AI-related fields for single-user experience
    min_ai_opponents: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_ai_opponents: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    supports_spectating: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<GameType(id={self.id}, name={self.name}, available={self.is_available})>"


# =============================================================================
# GameRoom
# =============================================================================

class GameRoom(Base, UUIDMixin):
    """Simplified game room for single-user gaming experience."""

    __tablename__ = "game_rooms"

    code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    game_type_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_types.id"),
        nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # Waiting, In Progress, Completed
    max_players: Mapped[int] = mapped_column(Integer, nullable=False)
    min_players: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Single-player mode fields
    user_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 'spectator' or role ID
    is_spectator_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Counters for tracking
    current_participant_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ai_agent_counter: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    game_type: Mapped["GameType"] = relationship("GameType")
    participants: Mapped[List["GameRoomParticipant"]] = relationship(
        "GameRoomParticipant",
        back_populates="game_room",
        cascade="all, delete-orphan"
    )
    game_state: Mapped[Optional["GameState"]] = relationship(
        "GameState",
        back_populates="game_room",
        uselist=False,
        cascade="all, delete-orphan"
    )
    sessions: Mapped[List["GameSession"]] = relationship(
        "GameSession",
        back_populates="game_room",
        cascade="all, delete-orphan"
    )

    def can_join(self) -> bool:
        """Check if room is accepting new players."""
        return self.status == "Waiting"

    def has_capacity(self) -> bool:
        """Check if room has space for more players."""
        return self.current_participant_count < self.max_players

    def get_active_participants_count(self) -> int:
        """Get count of active (not left) participants."""
        return sum(1 for p in self.participants if p.left_at is None)

    def is_ready_to_start(self) -> bool:
        """Check if room has enough participants to start."""
        return self.get_active_participants_count() >= self.min_players

    def start(self):
        """Transition room to In Progress status."""
        self.status = "In Progress"
        self.started_at = datetime.utcnow()

    def complete(self):
        """Transition room to Completed status."""
        self.status = "Completed"
        self.completed_at = datetime.utcnow()

    def increment_ai_counter(self) -> str:
        """Increment AI agent counter and return sequential AI name.
        
        Returns:
            Sequential AI player name in format "AI玩家{N}"
        """
        self.ai_agent_counter += 1
        return f"AI玩家{self.ai_agent_counter}"

    def __repr__(self):
        return f"<GameRoom(id={self.id}, code={self.code}, status={self.status})>"


# =============================================================================
# GameRoomParticipant
# =============================================================================

class GameRoomParticipant(Base, UUIDMixin):
    """Join table linking players, sessions, and AI agents to game rooms."""

    __tablename__ = "game_room_participants"

    game_room_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_rooms.id", ondelete="CASCADE"),
        nullable=False
    )
    player_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("players.id", ondelete="SET NULL"),
        nullable=True
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True
    )
    is_ai_agent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_personality: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    replaced_by_ai: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    left_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    game_room: Mapped["GameRoom"] = relationship("GameRoom", back_populates="participants")
    player: Mapped[Optional["Player"]] = relationship("Player", lazy="joined")
    session: Mapped[Optional["Session"]] = relationship("Session")

    def is_active(self) -> bool:
        """Check if participant is still in the game."""
        return self.left_at is None

    def leave(self):
        """Mark participant as having left."""
        self.left_at = datetime.utcnow()

    def __repr__(self):
        participant_type = "AI" if self.is_ai_agent else "Human"
        return f"<GameRoomParticipant(id={self.id}, type={participant_type}, active={self.is_active()})>"


# =============================================================================
# GameState
# =============================================================================

class GameState(Base, UUIDMixin):
    """Current state of a single-user game."""

    __tablename__ = "game_states"

    game_room_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_rooms.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    current_phase: Mapped[str] = mapped_column(String(50), default="setup", nullable=False)
    current_turn: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # Deprecated: use current_turn_player_id
    current_turn_player_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("players.id", ondelete="SET NULL"),
        nullable=True
    )
    turn_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    game_data: Mapped[dict] = mapped_column(JSON, nullable=False)  # MySQL native JSON
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    # Relationships
    game_room: Mapped["GameRoom"] = relationship("GameRoom", back_populates="game_state")
    current_turn_player: Mapped[Optional["Player"]] = relationship("Player", lazy="joined")

    def advance_turn(self, next_participant_id: str):
        """Advance to next participant's turn."""
        self.current_turn = next_participant_id
        self.current_turn_player_id = next_participant_id
        self.turn_number += 1
        self.last_updated = datetime.utcnow()

    def pause_game(self):
        """Pause the game."""
        self.is_paused = True
        self.last_updated = datetime.utcnow()

    def resume_game(self):
        """Resume the game."""
        self.is_paused = False
        self.last_updated = datetime.utcnow()

    def __repr__(self):
        return f"<GameState(id={self.id}, turn={self.turn_number}, paused={self.is_paused})>"


# =============================================================================
# GameSession
# =============================================================================

class GameSession(Base, UUIDMixin):
    """Historical record of a single-user game session.
    
    Created when a GameRoom transitions to 'Completed' status.
    Used for short-term game history (30 days retention).
    """

    __tablename__ = "game_sessions"

    # Foreign keys
    game_room_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    game_type_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Game metrics
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    participants_count: Mapped[int] = mapped_column(Integer, nullable=False)
    ai_agents_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Single-user specific fields
    user_won: Mapped[bool] = mapped_column(Boolean, nullable=False)  # User vs AI result
    final_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # User's final score

    # Final game state snapshot (MySQL native JSON)
    final_state: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Relationships
    game_room: Mapped["GameRoom"] = relationship("GameRoom", back_populates="sessions")
    game_type: Mapped["GameType"] = relationship("GameType")

    def __repr__(self):
        return (
            f"<GameSession(id={self.id}, "
            f"game_type_id={self.game_type_id}, "
            f"started_at={self.started_at}, "
            f"user_won={self.user_won})>"
        )

    @property
    def human_players_count(self) -> int:
        """Calculate number of human players (always 1 for single-user)."""
        return 1
