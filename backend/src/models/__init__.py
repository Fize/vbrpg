"""Models package - import all models to ensure SQLAlchemy relationships work."""
from src.models.ai_agent import AIAgent
from src.models.base import Base
from src.models.game_room import GameRoom
from src.models.game_room_participant import GameRoomParticipant
from src.models.game_session import GameSession
from src.models.game_state import GameState
from src.models.game_type import GameType

# Legacy models to be removed after migration
from src.models.player import Player
from src.models.player_profile import PlayerProfile
from src.models.session import Session

__all__ = [
    "Base",
    "Session",
    "AIAgent",
    "GameType",
    "GameRoom",
    "GameRoomParticipant",
    "GameState",
    "GameSession",
    "Player",
    "PlayerProfile",
]
