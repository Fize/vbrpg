"""GameState model."""
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin


class GameState(Base, UUIDMixin):
    """Current state of an in-progress game."""

    __tablename__ = "game_states"

    game_room_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_rooms.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    current_phase: Mapped[str] = mapped_column(String(50), nullable=False)
    current_turn_player_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("players.id", ondelete="SET NULL"),
        nullable=True
    )
    turn_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    game_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON stored as TEXT in SQLite
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    game_room: Mapped["GameRoom"] = relationship("GameRoom", back_populates="game_state")
    current_turn_player: Mapped["Player"] = relationship("Player")

    def __repr__(self):
        return f"<GameState(id={self.id}, phase={self.current_phase}, turn={self.turn_number})>"
