# -*- coding: utf-8 -*-
"""Werewolf-specific state definitions extending base game state."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from src.games.base.state import BaseGameState, BasePlayerState


class WerewolfPhase(str, Enum):
    """Game phases for werewolf game."""

    WAITING = "waiting"
    NIGHT = "night"
    NIGHT_WEREWOLF = "night_werewolf"
    NIGHT_SEER = "night_seer"
    NIGHT_WITCH = "night_witch"
    DAY = "day"
    DAY_ANNOUNCEMENT = "day_announcement"
    DAY_DISCUSSION = "day_discussion"
    DAY_VOTE = "day_vote"
    DISCUSSION = "discussion"
    VOTE = "vote"
    LAST_WORDS = "last_words"
    HUNTER_SHOOT = "hunter_shoot"
    GAME_OVER = "game_over"
    ENDED = "ended"


class NightSubPhase(str, Enum):
    """Night sub-phases for werewolf game."""

    WEREWOLF_ACTION = "werewolf_action"
    SEER_ACTION = "seer_action"
    WITCH_ACTION = "witch_action"


class DeathReason(str, Enum):
    """Reasons for player death."""

    KILLED = "killed"       # Killed by werewolves
    POISONED = "poisoned"   # Poisoned by witch
    VOTED = "voted"         # Voted out
    SHOT = "shot"           # Shot by hunter


# 10-player role configuration
WEREWOLF_10P_CONFIG: dict[str, int] = {
    "werewolf": 3,
    "seer": 1,
    "witch": 1,
    "hunter": 1,
    "villager": 4,
}


@dataclass
class NightActions:
    """Actions taken during the night phase."""

    werewolf_kill_target: Optional[int] = None   # Seat number
    seer_check_target: Optional[int] = None      # Seat number
    witch_save: bool = False
    witch_poison_target: Optional[int] = None    # Seat number


@dataclass
class GameLogEntry:
    """Entry for game log tracking all game events."""

    id: str
    type: str          # speech, host_announcement, death, vote, skill
    content: str
    day: int
    phase: str
    time: datetime
    player_id: Optional[str] = None
    player_name: Optional[str] = None
    seat_number: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    is_public: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "day": self.day,
            "phase": self.phase,
            "time": self.time.isoformat(),
            "player_id": self.player_id,
            "player_name": self.player_name,
            "seat_number": self.seat_number,
            "metadata": self.metadata,
            "is_public": self.is_public,
        }

    @classmethod
    def create(
        cls,
        log_type: str,
        content: str,
        day: int,
        phase: str,
        player_id: Optional[str] = None,
        player_name: Optional[str] = None,
        seat_number: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        is_public: bool = True,
    ) -> "GameLogEntry":
        """Factory method to create a new log entry with auto-generated id and timestamp."""
        return cls(
            id=str(uuid.uuid4()),
            type=log_type,
            content=content,
            day=day,
            phase=phase,
            time=datetime.now(),
            player_id=player_id,
            player_name=player_name,
            seat_number=seat_number,
            metadata=metadata,
            is_public=is_public,
        )


@dataclass
class PlayerState(BasePlayerState):
    """State of a player in a werewolf game, extending BasePlayerState."""

    role: str = ""                         # werewolf, seer, witch, hunter, villager
    team: str = ""                         # werewolf, villager
    death_reason: Optional[DeathReason] = None
    death_day: Optional[int] = None


@dataclass
class WerewolfGameState(BaseGameState):
    """Complete state of a werewolf game, extending BaseGameState."""

    # Override phase with WerewolfPhase
    phase: str = WerewolfPhase.WAITING.value
    sub_phase: Optional[str] = None

    # Night actions for current night
    current_night_actions: NightActions = field(default_factory=NightActions)

    # Witch potion status
    witch_has_antidote: bool = True
    witch_has_poison: bool = True

    # Vote tracking
    current_votes: Dict[int, int] = field(default_factory=dict)  # voter_seat -> target_seat

    # Game history
    speech_history: List[Dict[str, Any]] = field(default_factory=list)
    vote_history: List[Dict[str, Any]] = field(default_factory=list)
    death_history: List[Dict[str, Any]] = field(default_factory=list)

    # Game logs
    game_logs: List[GameLogEntry] = field(default_factory=list)

    # User player info
    user_seat_number: Optional[int] = None
    is_spectator_mode: bool = False

    # Game control
    current_speaker_seat: Optional[int] = None
    waiting_for_player_input: bool = False
    speech_reminder_count: int = 0

    # Human player action tracking
    waiting_for_human_action: bool = False
    human_action_type: Optional[str] = None
    human_action_timeout: Optional[int] = None
    human_action_start_time: Optional[datetime] = None

    # Werewolf private chat
    werewolf_private_chat: List[Dict[str, Any]] = field(default_factory=list)

    # Last words and spectator mode
    last_words_seat: Optional[int] = None
    last_words_reason: Optional[str] = None
    is_spectator_after_death: bool = False
