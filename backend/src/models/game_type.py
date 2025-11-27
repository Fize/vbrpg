"""GameType model for single-user gaming."""
from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, UUIDMixin


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
