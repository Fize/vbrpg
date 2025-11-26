"""Session model for single-user gaming experience."""
from datetime import datetime, timedelta

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, UUIDMixin


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
    expires_at: Mapped[datetime] = mapped_column(nullable=True)

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
