"""PlayerProfile model."""
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class PlayerProfile(Base):
    """Extended player information and statistics."""

    __tablename__ = "player_profiles"

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("players.id", ondelete="CASCADE"),
        primary_key=True
    )
    total_games: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    favorite_game_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("game_types.id", ondelete="SET NULL"),
        nullable=True
    )
    ui_preferences: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    player: Mapped["Player"] = relationship("Player", back_populates="profile")
    favorite_game: Mapped["GameType"] = relationship("GameType")

    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage."""
        if self.total_games == 0:
            return 0.0
        return (self.total_wins / self.total_games) * 100

    def __repr__(self):
        return f"<PlayerProfile(player_id={self.player_id}, games={self.total_games}, wins={self.total_wins})>"
