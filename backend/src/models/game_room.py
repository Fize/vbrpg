"""GameRoom model for single-user gaming."""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from src.models.game_room_participant import GameRoomParticipant
    from src.models.game_session import GameSession
    from src.models.game_state import GameState
    from src.models.game_type import GameType


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
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # AI-related fields for single-user experience
    ai_agent_counter: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    game_type: Mapped["GameType"] = relationship("GameType")
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
