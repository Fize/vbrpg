"""Base AI agent for any game."""
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

class BaseGameAgent(ABC):
    """Abstract base for all game AI agents."""
    
    def __init__(self, player_id: str, player_name: str, seat_number: int,
                 personality: Optional[Dict[str, str]] = None):
        self.player_id = player_id
        self.player_name = player_name
        self.seat_number = seat_number
        self.personality = personality or {}
        self.is_alive = True
        self.memory: List[Dict[str, Any]] = []
    
    @property
    @abstractmethod
    def role_type(self) -> str:
        pass
    
    @abstractmethod
    def get_system_prompt(self, game_state: Dict[str, Any]) -> str:
        pass
    
    def add_memory(self, event: Dict[str, Any]) -> None:
        self.memory.append(event)
