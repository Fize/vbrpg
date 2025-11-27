"""AIAgent model for single-user gaming."""
from datetime import datetime
from typing import Dict

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, UUIDMixin


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
