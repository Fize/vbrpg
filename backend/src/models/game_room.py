"""GameRoom model."""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from src.models.game_session import GameSession


class GameRoom(Base, UUIDMixin):
    """Game room for active or completed game sessions."""

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
    created_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("players.id", ondelete="SET NULL"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    game_type: Mapped["GameType"] = relationship("GameType")
    creator: Mapped["Player"] = relationship("Player", foreign_keys=[created_by])
    participants: Mapped[list["GameRoomParticipant"]] = relationship(
        "GameRoomParticipant",
        back_populates="game_room",
        cascade="all, delete-orphan"
    )
    game_state: Mapped["GameState"] = relationship(
        "GameState",
        back_populates="game_room",
        uselist=False,
        cascade="all, delete-orphan"
    )
    sessions: Mapped[list["GameSession"]] = relationship(
        "GameSession",
        back_populates="game_room",
        cascade="all, delete-orphan"
    )

    def can_join(self) -> bool:
        """Check if room is accepting new players."""
        return self.status == "Waiting"

    def get_active_participants_count(self) -> int:
        """Get count of active (not left) participants."""
        return sum(1 for p in self.participants if p.left_at is None)

    def is_ready_to_start(self) -> bool:
        """Check if room has enough players to start."""
        return self.get_active_participants_count() >= self.min_players

    def start(self):
        """Transition room to In Progress status."""
        self.status = "In Progress"
        self.started_at = datetime.utcnow()

    def complete(self):
        """Transition room to Completed status."""
        self.status = "Completed"
        self.completed_at = datetime.utcnow()

    def __repr__(self):
        return f"<GameRoom(id={self.id}, code={self.code}, status={self.status})>"
