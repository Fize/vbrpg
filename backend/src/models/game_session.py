"""GameSession model for single-user gaming records."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from src.models.game_room import GameRoom
    from src.models.game_type import GameType


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
    final_score: Mapped[int] = mapped_column(Integer, nullable=True)  # User's final score

    # Final game state snapshot (JSON stored as TEXT in SQLite)
    final_state: Mapped[str] = mapped_column(Text, nullable=False)

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
