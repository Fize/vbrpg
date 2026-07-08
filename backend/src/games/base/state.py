import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime

class GamePhase(str, Enum):
    """Base game phases - extended by specific games."""
    pass

@dataclass
class BasePlayerState:
    """Base player state for any game."""
    player_id: str
    player_name: str
    seat_number: int
    is_alive: bool = True
    is_ai: bool = True
    is_human: bool = False

@dataclass
class BaseGameState:
    """Base game state for any game. Extended by specific games."""
    room_code: str
    game_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    phase: str = "waiting"
    day_number: int = 0
    players: Dict[int, BasePlayerState] = field(default_factory=dict)
    is_started: bool = False
    is_stopped: bool = False
    is_paused: bool = False
    winner: Optional[str] = None
    
    # Human player support
    human_player_seat: Optional[int] = None
    waiting_for_human_action: bool = False
    human_action_type: Optional[str] = None
    human_action_timeout: Optional[int] = None
    human_action_start_time: Optional[datetime] = None
    
    def get_alive_players(self) -> List[BasePlayerState]:
        return [p for p in self.players.values() if p.is_alive]
