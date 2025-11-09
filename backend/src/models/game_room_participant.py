"""GameRoomParticipant model."""
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin


class GameRoomParticipant(Base, UUIDMixin):
    """Join table linking players and AI agents to game rooms."""

    __tablename__ = "game_room_participants"

    game_room_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_rooms.id", ondelete="CASCADE"),
        nullable=False
    )
    player_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("players.id", ondelete="SET NULL"),
        nullable=True
    )
    is_ai_agent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_personality: Mapped[str | None] = mapped_column(String(50), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    left_at: Mapped[datetime | None] = mapped_column(nullable=True)
    replaced_by_ai: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    game_room: Mapped["GameRoom"] = relationship("GameRoom", back_populates="participants")
    player: Mapped["Player"] = relationship("Player")

    def is_active(self) -> bool:
        """Check if participant is still in the game."""
        return self.left_at is None

    def leave(self):
        """Mark participant as having left."""
        self.left_at = datetime.utcnow()

    def __repr__(self):
        participant_type = "AI" if self.is_ai_agent else "Human"
        return f"<GameRoomParticipant(id={self.id}, type={participant_type}, active={self.is_active()})>"
