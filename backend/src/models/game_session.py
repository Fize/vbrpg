"""GameSession model for historical game records."""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from src.models.base import Base


class GameSession(Base):
    """Historical record of a completed game.
    
    Created when a GameRoom transitions to 'Completed' status.
    Used for player statistics, analytics, and game history.
    """
    
    __tablename__ = "game_sessions"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Foreign keys
    game_room_id = Column(
        String(36),
        ForeignKey("game_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    game_type_id = Column(
        String(36),
        ForeignKey("game_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    winner_id = Column(
        String(36),
        ForeignKey("players.id", ondelete="SET NULL"),
        nullable=True,  # NULL for tie games
        index=True
    )
    
    # Timestamps
    started_at = Column(DateTime, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=False)
    
    # Game metrics
    duration_minutes = Column(Integer, nullable=False)
    participants_count = Column(Integer, nullable=False)
    ai_agents_count = Column(Integer, nullable=False)
    
    # Final game state snapshot (JSON stored as TEXT in SQLite)
    final_state = Column(Text, nullable=False)
    
    # Relationships
    game_room = relationship("GameRoom", back_populates="sessions")
    game_type = relationship("GameType")
    winner = relationship("Player")
    
    def __repr__(self):
        return (
            f"<GameSession(id={self.id}, "
            f"game_type_id={self.game_type_id}, "
            f"started_at={self.started_at}, "
            f"winner_id={self.winner_id})>"
        )
    
    @property
    def human_players_count(self) -> int:
        """Calculate number of human players."""
        return self.participants_count - self.ai_agents_count
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "game_room_id": str(self.game_room_id),
            "game_type_id": str(self.game_type_id),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "winner_id": str(self.winner_id) if self.winner_id else None,
            "duration_minutes": self.duration_minutes,
            "participants_count": self.participants_count,
            "ai_agents_count": self.ai_agents_count,
            "human_players_count": self.human_players_count,
            "final_state": self.final_state,
        }
