"""GameState model for single-user gaming."""
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin


class GameState(Base, UUIDMixin):
    """Current state of a single-user game."""

    __tablename__ = "game_states"

    game_room_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_rooms.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    current_turn: Mapped[str] = mapped_column(String(36), nullable=False)  # session_id or ai_agent_id
    turn_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    game_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON stored as TEXT in SQLite
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    # Relationships
    game_room: Mapped["GameRoom"] = relationship("GameRoom", back_populates="game_state")

    def advance_turn(self, next_participant_id: str):
        """Advance to next participant's turn."""
        self.current_turn = next_participant_id
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
