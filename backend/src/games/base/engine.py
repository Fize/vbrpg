"""Base game engine using LangGraph patterns."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from src.games.base.state import BaseGameState

class BaseGameEngine(ABC):
    """Abstract base for game-specific engines."""
    
    @abstractmethod
    def build_graph(self):
        """Build and return the LangGraph StateGraph for this game."""
        pass
    
    @abstractmethod
    def initialize_game(self, room_code: str, **kwargs) -> BaseGameState:
        """Initialize a new game state."""
        pass
    
    @abstractmethod
    def check_winner(self, state: BaseGameState) -> Optional[str]:
        """Check win condition. Returns winner team or None."""
        pass
