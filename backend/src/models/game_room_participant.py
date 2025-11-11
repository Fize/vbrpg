"""GameRoomParticipant model."""
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.models.game_room import GameRoom
    from src.models.player import Player


class GameRoomParticipant(Base, UUIDMixin):
    """Join table linking players and AI agents to game rooms."""

    __tablename__ = "game_room_participants"
    
    __table_args__ = (
        UniqueConstraint('game_room_id', 'player_id', name='uq_room_participant'),
        Index('idx_participant_owner', 'game_room_id', 'is_owner'),
        Index('idx_participant_join_time', 'game_room_id', 'join_timestamp'),
    )

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
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    left_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    replaced_by_ai: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Phase 2 Extensions: Ownership and join timestamp
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    join_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    game_room: Mapped["GameRoom"] = relationship("GameRoom", back_populates="participants")
    player: Mapped["Player"] = relationship("Player")

    def is_active(self) -> bool:
        """Check if participant is still in the game."""
        return self.left_at is None

    def leave(self):
        """Mark participant as having left."""
        self.left_at = datetime.utcnow()
    
    @classmethod
    async def get_earliest_human(
        cls,
        room_id: str,
        session: "AsyncSession"
    ) -> Optional["GameRoomParticipant"]:
        """Get the earliest-joined human participant in a room.
        
        Args:
            room_id: Game room ID
            session: Database session
            
        Returns:
            Earliest human participant or None if no humans exist
        """
        result = await session.execute(
            select(cls)
            .where(
                cls.game_room_id == room_id,
                cls.is_ai_agent == False,  # noqa: E712
                cls.left_at == None  # noqa: E711
            )
            .order_by(cls.join_timestamp.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    def __repr__(self):
        participant_type = "AI" if self.is_ai_agent else "Human"
        return f"<GameRoomParticipant(id={self.id}, type={participant_type}, active={self.is_active()})>"
