"""Player model."""
from datetime import datetime, timedelta

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin


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
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    profile: Mapped["PlayerProfile"] = relationship(
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
