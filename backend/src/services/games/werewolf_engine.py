# -*- coding: utf-8 -*-
"""Werewolf game engine for managing game state and flow."""

import logging
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class WerewolfPhase(str, Enum):
    """Game phases for werewolf game."""

    WAITING = "waiting"  # Waiting for game to start
    NIGHT = "night"  # Night phase
    DAY = "day"  # Day phase - general
    DISCUSSION = "discussion"  # Discussion sub-phase
    VOTE = "vote"  # Voting sub-phase
    LAST_WORDS = "last_words"  # Last words phase
    ENDED = "ended"  # Game has ended


class NightSubPhase(str, Enum):
    """Night sub-phases for werewolf game."""

    WEREWOLF_ACTION = "werewolf_action"
    SEER_ACTION = "seer_action"
    WITCH_ACTION = "witch_action"


class DeathReason(str, Enum):
    """Reasons for player death."""

    KILLED = "killed"  # Killed by werewolves
    POISONED = "poisoned"  # Poisoned by witch
    VOTED = "voted"  # Voted out
    SHOT = "shot"  # Shot by hunter


# 10-player role configuration
WEREWOLF_10P_CONFIG = {
    "werewolf": 3,
    "seer": 1,
    "witch": 1,
    "hunter": 1,
    "villager": 4,
}


@dataclass
class PlayerState:
    """State of a player in the game."""

    player_id: str
    player_name: str
    seat_number: int
    role: str  # werewolf, seer, witch, hunter, villager
    team: str  # werewolf, villager
    is_alive: bool = True
    is_ai: bool = True
    death_reason: Optional[DeathReason] = None
    death_day: Optional[int] = None


@dataclass
class NightActions:
    """Actions taken during night."""

    werewolf_kill_target: Optional[int] = None  # Seat number
    seer_check_target: Optional[int] = None  # Seat number
    witch_save: bool = False
    witch_poison_target: Optional[int] = None  # Seat number


@dataclass
class WerewolfGameState:
    """Complete state of a werewolf game."""

    room_code: str
    players: Dict[int, PlayerState] = field(default_factory=dict)  # seat_number -> PlayerState
    day_number: int = 0
    phase: WerewolfPhase = WerewolfPhase.WAITING
    sub_phase: Optional[str] = None

    # Night actions for current night
    current_night_actions: NightActions = field(default_factory=NightActions)

    # Witch potion status
    witch_has_antidote: bool = True
    witch_has_poison: bool = True

    # Vote tracking
    current_votes: Dict[int, int] = field(default_factory=dict)  # voter_seat -> target_seat

    # Game history
    death_history: List[Dict[str, Any]] = field(default_factory=list)
    speech_history: List[Dict[str, Any]] = field(default_factory=list)
    vote_history: List[Dict[str, Any]] = field(default_factory=list)

    # Winner
    winner: Optional[str] = None  # "werewolf" or "villager"

    # User player info
    user_seat_number: Optional[int] = None
    is_spectator_mode: bool = False


class WerewolfEngine:
    """
    Game engine for werewolf game.

    Handles:
    - Game initialization and role assignment
    - Phase transitions
    - Night action processing
    - Day discussion and voting
    - Win condition checking
    """

    def __init__(self):
        """Initialize the engine."""
        self.state: Optional[WerewolfGameState] = None

    def initialize_game(
        self,
        room_code: str,
        player_names: List[str],
        user_role: Optional[str] = None,
        is_spectator: bool = False,
    ) -> WerewolfGameState:
        """
        Initialize a new game.

        :param room_code: Room code for the game.
        :param player_names: List of 10 player names.
        :param user_role: Role for the user (if player mode).
        :param is_spectator: Whether user is in spectator mode.
        :return: Initialized game state.
        """
        if len(player_names) != 10:
            raise ValueError(f"Werewolf 10P requires exactly 10 players, got {len(player_names)}")

        self.state = WerewolfGameState(
            room_code=room_code,
            is_spectator_mode=is_spectator,
        )

        # Assign roles
        roles = self._assign_roles(user_role)

        # Create player states
        for i, (name, role) in enumerate(zip(player_names, roles), start=1):
            team = "werewolf" if role == "werewolf" else "villager"
            is_user = (i == 1 and not is_spectator)  # User is always seat 1 if playing

            self.state.players[i] = PlayerState(
                player_id=f"player_{i}",
                player_name=name,
                seat_number=i,
                role=role,
                team=team,
                is_ai=not is_user,
            )

            if is_user:
                self.state.user_seat_number = i

        logger.info(
            f"Game initialized: room={room_code}, "
            f"user_role={user_role}, spectator={is_spectator}"
        )

        return self.state

    def _assign_roles(self, user_role: Optional[str] = None) -> List[str]:
        """
        Assign roles to players.

        :param user_role: Specific role for the user (seat 1).
        :return: List of 10 roles.
        """
        roles = []
        for role, count in WEREWOLF_10P_CONFIG.items():
            roles.extend([role] * count)

        # If user requested a specific role, ensure they get it
        if user_role and user_role in roles:
            roles.remove(user_role)
            random.shuffle(roles)
            roles.insert(0, user_role)  # User is always seat 1
        else:
            random.shuffle(roles)

        return roles

    def start_game(self) -> None:
        """Start the game, entering first night."""
        if not self.state:
            raise RuntimeError("Game not initialized")

        self.state.day_number = 1
        self.state.phase = WerewolfPhase.NIGHT
        self.state.sub_phase = NightSubPhase.WEREWOLF_ACTION.value
        self.state.current_night_actions = NightActions()

        logger.info(f"Game started: entering Night 1")

    def get_alive_players(self) -> List[PlayerState]:
        """Get list of alive players."""
        if not self.state:
            return []
        return [p for p in self.state.players.values() if p.is_alive]

    def get_alive_player_by_seat(self, seat: int) -> Optional[PlayerState]:
        """Get alive player by seat number."""
        if not self.state:
            return None
        player = self.state.players.get(seat)
        if player and player.is_alive:
            return player
        return None

    def get_player_by_seat(self, seat: int) -> Optional[PlayerState]:
        """Get player by seat number (alive or dead)."""
        if not self.state:
            return None
        return self.state.players.get(seat)

    def get_werewolf_teammates(self, seat: int) -> List[PlayerState]:
        """Get werewolf teammates for a player."""
        if not self.state:
            return []
        player = self.state.players.get(seat)
        if not player or player.role != "werewolf":
            return []
        return [
            p for p in self.state.players.values()
            if p.role == "werewolf" and p.seat_number != seat
        ]

    def count_teams(self) -> Tuple[int, int]:
        """
        Count alive players by team.

        :return: (werewolf_count, good_count)
        """
        if not self.state:
            return (0, 0)

        werewolf_count = sum(
            1 for p in self.state.players.values()
            if p.is_alive and p.team == "werewolf"
        )
        good_count = sum(
            1 for p in self.state.players.values()
            if p.is_alive and p.team == "villager"
        )
        return (werewolf_count, good_count)

    # Night action processing

    def set_werewolf_kill(self, target_seat: Optional[int]) -> None:
        """
        Set werewolf kill target.

        :param target_seat: Seat number to kill, or None for empty kill.
        """
        if not self.state:
            return
        self.state.current_night_actions.werewolf_kill_target = target_seat
        logger.info(f"Werewolf kill target set: {target_seat}")

    def set_seer_check(self, target_seat: int) -> bool:
        """
        Set seer check target and return result.

        :param target_seat: Seat number to check.
        :return: True if target is werewolf.
        """
        if not self.state:
            return False
        self.state.current_night_actions.seer_check_target = target_seat
        player = self.state.players.get(target_seat)
        is_werewolf = player.role == "werewolf" if player else False
        logger.info(f"Seer check: seat {target_seat} is werewolf={is_werewolf}")
        return is_werewolf

    def set_witch_action(
        self,
        save: bool = False,
        poison_target: Optional[int] = None,
    ) -> None:
        """
        Set witch action.

        :param save: Whether to use antidote.
        :param poison_target: Seat number to poison, or None.
        """
        if not self.state:
            return

        if save and self.state.witch_has_antidote:
            self.state.current_night_actions.witch_save = True
            self.state.witch_has_antidote = False
            logger.info("Witch used antidote")

        if poison_target and self.state.witch_has_poison:
            self.state.current_night_actions.witch_poison_target = poison_target
            self.state.witch_has_poison = False
            logger.info(f"Witch poisoned seat {poison_target}")

    def process_night(self) -> List[Dict[str, Any]]:
        """
        Process night actions and return deaths.

        :return: List of death info dicts.
        """
        if not self.state:
            return []

        deaths = []
        actions = self.state.current_night_actions

        # Process werewolf kill
        if actions.werewolf_kill_target and not actions.witch_save:
            target = self.state.players.get(actions.werewolf_kill_target)
            if target and target.is_alive:
                self._kill_player(target.seat_number, DeathReason.KILLED)
                deaths.append({
                    "seat_number": target.seat_number,
                    "player_name": target.player_name,
                    "reason": DeathReason.KILLED.value,
                })

        # Process witch poison
        if actions.witch_poison_target:
            target = self.state.players.get(actions.witch_poison_target)
            if target and target.is_alive:
                self._kill_player(target.seat_number, DeathReason.POISONED)
                deaths.append({
                    "seat_number": target.seat_number,
                    "player_name": target.player_name,
                    "reason": DeathReason.POISONED.value,
                })

        # Record deaths
        if deaths:
            self.state.death_history.extend([
                {**d, "day": self.state.day_number, "phase": "night"}
                for d in deaths
            ])

        # Reset night actions for next night
        self.state.current_night_actions = NightActions()

        logger.info(f"Night {self.state.day_number} processed: {len(deaths)} deaths")

        return deaths

    def _kill_player(self, seat: int, reason: DeathReason) -> None:
        """Kill a player."""
        if not self.state:
            return
        player = self.state.players.get(seat)
        if player:
            player.is_alive = False
            player.death_reason = reason
            player.death_day = self.state.day_number

    # Day phase processing

    def start_day(self) -> None:
        """Transition to day phase."""
        if not self.state:
            return
        self.state.phase = WerewolfPhase.DAY
        self.state.sub_phase = "announcement"

    def start_discussion(self, speaking_order: Optional[List[int]] = None) -> List[int]:
        """
        Start discussion phase.

        :param speaking_order: Optional custom speaking order.
        :return: Speaking order (list of seat numbers).
        """
        if not self.state:
            return []

        self.state.phase = WerewolfPhase.DISCUSSION

        if speaking_order:
            return speaking_order

        # Default: alive players in seat order
        return [p.seat_number for p in self.get_alive_players()]

    def add_speech(
        self,
        seat: int,
        content: str,
    ) -> None:
        """
        Record a player's speech.

        :param seat: Speaker's seat number.
        :param content: Speech content.
        """
        if not self.state:
            return

        player = self.state.players.get(seat)
        if not player:
            return

        self.state.speech_history.append({
            "day": self.state.day_number,
            "seat_number": seat,
            "player_name": player.player_name,
            "content": content,
        })

    def start_vote(self) -> None:
        """Start voting phase."""
        if not self.state:
            return
        self.state.phase = WerewolfPhase.VOTE
        self.state.current_votes = {}

    def cast_vote(self, voter_seat: int, target_seat: Optional[int]) -> None:
        """
        Cast a vote.

        :param voter_seat: Voter's seat number.
        :param target_seat: Target's seat number, or None for abstain.
        """
        if not self.state:
            return
        if target_seat is not None:
            self.state.current_votes[voter_seat] = target_seat
        # Abstain: don't record

    def tally_votes(self) -> Tuple[Dict[int, int], Optional[int], bool]:
        """
        Tally votes and determine result.

        :return: (vote_counts, eliminated_seat, is_tie)
        """
        if not self.state:
            return ({}, None, False)

        # Count votes per target
        vote_counts: Dict[int, int] = {}
        for target in self.state.current_votes.values():
            vote_counts[target] = vote_counts.get(target, 0) + 1

        if not vote_counts:
            return ({}, None, True)  # All abstained

        # Find max votes
        max_votes = max(vote_counts.values())
        top_candidates = [s for s, c in vote_counts.items() if c == max_votes]

        # Check for tie
        if len(top_candidates) > 1:
            return (vote_counts, None, True)

        eliminated_seat = top_candidates[0]
        return (vote_counts, eliminated_seat, False)

    def execute_vote_result(self, eliminated_seat: Optional[int]) -> Optional[Dict[str, Any]]:
        """
        Execute vote result.

        :param eliminated_seat: Seat number to eliminate, or None if tie.
        :return: Death info dict, or None if no elimination.
        """
        if not self.state or eliminated_seat is None:
            return None

        target = self.state.players.get(eliminated_seat)
        if not target or not target.is_alive:
            return None

        self._kill_player(eliminated_seat, DeathReason.VOTED)

        death_info = {
            "seat_number": eliminated_seat,
            "player_name": target.player_name,
            "role": target.role,
            "reason": DeathReason.VOTED.value,
        }

        self.state.death_history.append({
            **death_info,
            "day": self.state.day_number,
            "phase": "vote",
        })

        self.state.vote_history.append({
            "day": self.state.day_number,
            "votes": dict(self.state.current_votes),
            "eliminated": eliminated_seat,
        })

        return death_info

    # Hunter shoot

    def can_hunter_shoot(self, seat: int, death_reason: DeathReason) -> bool:
        """
        Check if hunter can shoot.

        :param seat: Hunter's seat number.
        :param death_reason: How the hunter died.
        :return: True if can shoot.
        """
        if not self.state:
            return False

        player = self.state.players.get(seat)
        if not player or player.role != "hunter":
            return False

        # Cannot shoot if poisoned
        return death_reason != DeathReason.POISONED

    def hunter_shoot(self, hunter_seat: int, target_seat: int) -> Optional[Dict[str, Any]]:
        """
        Execute hunter shoot.

        :param hunter_seat: Hunter's seat number.
        :param target_seat: Target's seat number.
        :return: Death info dict, or None if failed.
        """
        if not self.state:
            return None

        target = self.state.players.get(target_seat)
        if not target or not target.is_alive:
            return None

        self._kill_player(target_seat, DeathReason.SHOT)

        death_info = {
            "seat_number": target_seat,
            "player_name": target.player_name,
            "role": target.role,
            "reason": DeathReason.SHOT.value,
            "hunter_seat": hunter_seat,
        }

        self.state.death_history.append({
            **death_info,
            "day": self.state.day_number,
            "phase": "hunter_shoot",
        })

        logger.info(f"Hunter {hunter_seat} shot {target_seat}")

        return death_info

    # Win condition

    def check_win_condition(self) -> Optional[str]:
        """
        Check if game has ended.

        :return: Winner ("werewolf" or "villager"), or None if game continues.
        """
        if not self.state:
            return None

        werewolf_count, good_count = self.count_teams()

        # Werewolves win if they equal or outnumber good players
        if werewolf_count >= good_count:
            self.state.winner = "werewolf"
            self.state.phase = WerewolfPhase.ENDED
            logger.info("Game ended: werewolf wins")
            return "werewolf"

        # Good team wins if all werewolves are dead
        if werewolf_count == 0:
            self.state.winner = "villager"
            self.state.phase = WerewolfPhase.ENDED
            logger.info("Game ended: villager wins")
            return "villager"

        return None

    # Phase transitions

    def advance_night_sub_phase(self) -> Optional[str]:
        """
        Advance to next night sub-phase.

        :return: Next sub-phase, or None if night ends.
        """
        if not self.state:
            return None

        current = self.state.sub_phase

        if current == NightSubPhase.WEREWOLF_ACTION.value:
            self.state.sub_phase = NightSubPhase.SEER_ACTION.value
        elif current == NightSubPhase.SEER_ACTION.value:
            self.state.sub_phase = NightSubPhase.WITCH_ACTION.value
        elif current == NightSubPhase.WITCH_ACTION.value:
            # Night ends
            return None
        else:
            return None

        return self.state.sub_phase

    def transition_to_next_night(self) -> None:
        """Transition to next night."""
        if not self.state:
            return

        self.state.day_number += 1
        self.state.phase = WerewolfPhase.NIGHT
        self.state.sub_phase = NightSubPhase.WEREWOLF_ACTION.value
        self.state.current_night_actions = NightActions()
        self.state.current_votes = {}

        logger.info(f"Transitioning to Night {self.state.day_number}")

    # Serialization

    def get_public_state(self) -> Dict[str, Any]:
        """
        Get public game state (safe to send to all clients).

        :return: Public state dict.
        """
        if not self.state:
            return {}

        alive_players = [
            {
                "seat_number": p.seat_number,
                "player_name": p.player_name,
                "is_alive": p.is_alive,
                "is_ai": p.is_ai,
            }
            for p in self.state.players.values()
        ]

        dead_players = [
            {
                "seat_number": p.seat_number,
                "player_name": p.player_name,
                "role": p.role if self.state.phase == WerewolfPhase.ENDED else None,
                "death_reason": p.death_reason.value if p.death_reason else None,
                "death_day": p.death_day,
            }
            for p in self.state.players.values()
            if not p.is_alive
        ]

        return {
            "room_code": self.state.room_code,
            "day_number": self.state.day_number,
            "phase": self.state.phase.value,
            "sub_phase": self.state.sub_phase,
            "alive_players": alive_players,
            "dead_players": dead_players,
            "winner": self.state.winner,
        }

    def get_player_state(self, seat: int) -> Optional[Dict[str, Any]]:
        """
        Get state for a specific player (includes role info).

        :param seat: Player's seat number.
        :return: Player state dict.
        """
        if not self.state:
            return None

        player = self.state.players.get(seat)
        if not player:
            return None

        state = {
            "seat_number": player.seat_number,
            "player_name": player.player_name,
            "role": player.role,
            "team": player.team,
            "is_alive": player.is_alive,
        }

        # Add teammates for werewolf
        if player.role == "werewolf":
            state["teammates"] = [
                {"seat_number": p.seat_number, "player_name": p.player_name, "is_alive": p.is_alive}
                for p in self.get_werewolf_teammates(seat)
            ]

        # Add potion status for witch
        if player.role == "witch":
            state["has_antidote"] = self.state.witch_has_antidote
            state["has_poison"] = self.state.witch_has_poison

        return state
