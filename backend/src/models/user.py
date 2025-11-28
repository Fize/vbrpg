"""User-related models for single-user gaming.

This module consolidates all user-related database models:
- Player: Player model for both guest and registered players
- PlayerProfile: Extended player information and statistics
- Session: Local user session, replacing persistent player identity
- AIAgent: AI agent as game opponent for single-user experience
"""
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Dict, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin


# =============================================================================
# Player
# =============================================================================

class Player(Base, UUIDMixin):
    """Player model for both guest and registered players."""

    __tablename__ = "players"

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    is_guest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    last_active: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Relationships
    profile: Mapped[Optional["PlayerProfile"]] = relationship(
        "PlayerProfile",
        back_populates="player",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.is_guest and not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(days=30)

    def is_expired(self) -> bool:
        """Check if guest player has expired."""
        if not self.is_guest:
            return False
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def upgrade_to_permanent(self, username: str):
        """Upgrade guest account to permanent."""
        self.username = username
        self.is_guest = False
        self.expires_at = None

    def __repr__(self):
        return f"<Player(id={self.id}, username={self.username}, is_guest={self.is_guest})>"


# =============================================================================
# PlayerProfile
# =============================================================================

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
    favorite_game_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True
    )  # Stores game_type slug, no longer a foreign key
    ui_preferences: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # MySQL native JSON
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    player: Mapped["Player"] = relationship("Player", back_populates="profile")

    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage."""
        if self.total_games == 0:
            return 0.0
        return (self.total_wins / self.total_games) * 100

    def __repr__(self):
        return f"<PlayerProfile(player_id={self.player_id}, games={self.total_games}, wins={self.total_wins})>"


# =============================================================================
# Session
# =============================================================================

class Session(Base, UUIDMixin):
    """Local user session, replacing persistent player identity."""

    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    last_active: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    def is_expired(self) -> bool:
        """Check if session is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def extend_expiry(self, hours: int = 24) -> None:
        """Extend session expiry by specified hours."""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
        self.last_active = datetime.utcnow()

    @classmethod
    def create_new(cls, session_id: str, expires_hours: int = 24) -> "Session":
        """Create a new session with default expiry."""
        expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        return cls(
            session_id=session_id,
            expires_at=expires_at
        )


# =============================================================================
# AIAgent
# =============================================================================

class AIAgent(Base, UUIDMixin):
    """AI agent as game opponent for single-user experience."""

    __tablename__ = "ai_agents"

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    personality_type: Mapped[str] = mapped_column(String(30), nullable=False)  # aggressive, defensive, balanced
    difficulty_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1-5
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    def get_decision_weights(self) -> Dict[str, float]:
        """Get decision weights based on personality type.
        
        Returns:
            Dictionary with action weights for attack, defend, special
        """
        weights = {
            "aggressive": {"attack": 0.7, "defend": 0.2, "special": 0.1},
            "defensive": {"attack": 0.2, "defend": 0.7, "special": 0.1},
            "balanced": {"attack": 0.4, "defend": 0.4, "special": 0.2}
        }
        return weights.get(self.personality_type, weights["balanced"])

    def __repr__(self):
        return f"<AIAgent(id={self.id}, username={self.username}, personality={self.personality_type})>"
