# -*- coding: utf-8 -*-
"""Werewolf game engine for managing game state and flow."""

import logging
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class WerewolfPhase(str, Enum):
    """Game phases for werewolf game."""

    WAITING = "waiting"  # Waiting for game to start
    NIGHT = "night"  # Night phase
    NIGHT_WEREWOLF = "night_werewolf"  # Night - werewolf action sub-phase
    NIGHT_SEER = "night_seer"  # Night - seer action sub-phase
    NIGHT_WITCH = "night_witch"  # Night - witch action sub-phase
    DAY = "day"  # Day phase - general
    DAY_ANNOUNCEMENT = "day_announcement"  # Day announcement phase
    DAY_DISCUSSION = "day_discussion"  # Day discussion phase
    DAY_VOTE = "day_vote"  # Day voting phase
    DISCUSSION = "discussion"  # Discussion sub-phase (legacy)
    VOTE = "vote"  # Voting sub-phase (legacy)
    LAST_WORDS = "last_words"  # Last words phase
    HUNTER_SHOOT = "hunter_shoot"  # Hunter shooting phase
    GAME_OVER = "game_over"  # Game has ended
    ENDED = "ended"  # Game has ended (legacy)


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
    is_human: bool = False  # 是否为人类玩家（与 is_ai 互斥）
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
class GameLogEntry:
    """Entry for game log tracking all game events."""

    id: str
    type: str  # speech, host_announcement, death, vote, skill
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
class WerewolfGameState:
    """Complete state of a werewolf game."""

    room_code: str
    game_id: str = field(default_factory=lambda: str(uuid.uuid4()))  # Unique game instance ID
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

    # === 新增字段: 游戏控制 ===
    is_paused: bool = False  # 是否暂停
    is_started: bool = False  # 是否已开始
    is_stopped: bool = False  # 是否已停止（用户离开房间时设置）
    current_speaker_seat: Optional[int] = None  # 当前发言者座位
    waiting_for_player_input: bool = False  # 是否等待玩家输入
    speech_reminder_count: int = 0  # 发言提醒次数

    # === 新增字段: 游戏日志 ===
    game_logs: List[GameLogEntry] = field(default_factory=list)  # 完整日志列表

    # === 新增字段: 人类玩家参与 ===
    human_player_seat: Optional[int] = None  # 人类玩家座位号
    waiting_for_human_action: bool = False  # 是否等待人类行动
    human_action_type: Optional[str] = None  # 等待的行动类型 (speech/vote/night_action/last_words)
    human_action_timeout: Optional[int] = None  # 超时时间（秒）
    human_action_start_time: Optional[datetime] = None  # 行动开始时间

    # === 新增字段: 狼人私密讨论 ===
    werewolf_private_chat: List[Dict[str, Any]] = field(default_factory=list)  # 狼人私密讨论记录

    # === 新增字段: 遗言与观战模式 (Phase 5) ===
    last_words_seat: Optional[int] = None  # 当前需要遗言的玩家座位号
    last_words_reason: Optional[str] = None  # 死亡原因
    is_spectator_after_death: bool = False  # 人类玩家死后是否进入观战模式


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

    def _assign_random_seat(self, total_seats: int = 10) -> int:
        """
        随机分配一个座位号给人类玩家。

        :param total_seats: 总座位数，默认为10
        :return: 随机选择的座位号（1-10）
        """
        return random.randint(1, total_seats)

    def initialize_game_with_human_player(
        self,
        room_code: str,
        player_names: List[str],
        human_player_id: str,
        human_role: Optional[str] = None,
    ) -> WerewolfGameState:
        """
        初始化带人类玩家的游戏。

        与 initialize_game 的区别：
        - 座位号随机分配（不固定为1号位）
        - 人类玩家明确标记为 is_human=True, is_ai=False
        - 支持角色选择（human_role）或随机分配（human_role=None）

        :param room_code: 房间代码
        :param player_names: 10个玩家名称列表
        :param human_player_id: 人类玩家ID
        :param human_role: 人类玩家选择的角色（None表示随机分配）
        :return: 初始化后的游戏状态
        """
        if len(player_names) != 10:
            raise ValueError(f"Werewolf 10P requires exactly 10 players, got {len(player_names)}")

        self.state = WerewolfGameState(
            room_code=room_code,
            is_spectator_mode=False,
        )

        # 1. 生成角色列表
        roles = []
        for role, count in WEREWOLF_10P_CONFIG.items():
            roles.extend([role] * count)
        random.shuffle(roles)

        # 2. 随机选择人类玩家的座位号
        human_seat = self._assign_random_seat()
        self.state.human_player_seat = human_seat
        self.state.user_seat_number = human_seat

        # 3. 如果人类玩家指定了角色，确保分配给该座位
        if human_role and human_role in roles:
            # 找到该角色在列表中的位置
            role_index = roles.index(human_role)
            # 将该角色与人类座位位置的角色交换
            human_seat_index = human_seat - 1  # 座位号从1开始，索引从0开始
            roles[role_index], roles[human_seat_index] = roles[human_seat_index], roles[role_index]

        # 4. 创建所有玩家状态
        for i, (name, role) in enumerate(zip(player_names, roles), start=1):
            team = "werewolf" if role == "werewolf" else "villager"
            is_human = (i == human_seat)

            self.state.players[i] = PlayerState(
                player_id=human_player_id if is_human else f"ai_player_{i}",
                player_name=name,
                seat_number=i,
                role=role,
                team=team,
                is_ai=not is_human,
                is_human=is_human,
            )

        logger.info(
            f"Game initialized with human player: room={room_code}, "
            f"human_seat={human_seat}, human_role={self.state.players[human_seat].role}"
        )

        return self.state

    def start_game(self) -> None:
        """Start the game, entering first night."""
        if not self.state:
            raise RuntimeError("Game not initialized")

        self.state.day_number = 1
        self.state.phase = WerewolfPhase.NIGHT
        self.state.sub_phase = NightSubPhase.WEREWOLF_ACTION.value
        self.state.current_night_actions = NightActions()
        self.state.is_started = True  # 标记游戏已开始

        logger.info(f"Game started: entering Night 1")

    def add_game_log(
        self,
        log_type: str,
        content: str,
        player_id: Optional[str] = None,
        player_name: Optional[str] = None,
        seat_number: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        is_public: bool = True,
    ) -> GameLogEntry:
        """
        添加游戏日志条目。

        :param log_type: 日志类型 (speech, host_announcement, death, vote, skill, system)
        :param content: 日志内容
        :param player_id: 玩家 ID（可选）
        :param player_name: 玩家名称（可选）
        :param seat_number: 座位号（可选）
        :param metadata: 附加元数据（可选）
        :param is_public: 是否公开日志（默认 True）
        :return: 创建的日志条目
        """
        if not self.state:
            raise RuntimeError("Game not initialized")

        log_entry = GameLogEntry.create(
            log_type=log_type,
            content=content,
            day=self.state.day_number,
            phase=self.state.phase.value if self.state.phase else "unknown",
            player_id=player_id,
            player_name=player_name,
            seat_number=seat_number,
            metadata=metadata,
            is_public=is_public,
        )

        self.state.game_logs.append(log_entry)
        logger.debug(f"Game log added: {log_type} - {content[:50]}...")
        return log_entry

    def get_game_logs(
        self,
        log_type: Optional[str] = None,
        player_id: Optional[str] = None,
        day: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[GameLogEntry]:
        """
        获取游戏日志。

        :param log_type: 按类型过滤（可选）
        :param player_id: 按玩家过滤（可选）
        :param day: 按天数过滤（可选）
        :param limit: 返回条数限制（可选）
        :return: 日志条目列表
        """
        if not self.state:
            return []

        logs = self.state.game_logs

        if log_type:
            logs = [log for log in logs if log.type == log_type]

        if player_id:
            logs = [log for log in logs if log.player_id == player_id]

        if day is not None:
            logs = [log for log in logs if log.day == day]

        if limit:
            logs = logs[-limit:]

        return logs

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

    # =========================================================================
    # 外部状态操作方法 (接受 game_state 参数)
    # =========================================================================

    def process_werewolf_action(
        self,
        game_state: WerewolfGameState,
        target_seat: Optional[int]
    ) -> None:
        """Process werewolf kill action on external game state."""
        game_state.current_night_actions.werewolf_kill_target = target_seat
        logger.info(f"Werewolf kill target set: {target_seat}")

    def process_seer_action(
        self,
        game_state: WerewolfGameState,
        target_seat: int
    ) -> bool:
        """Process seer check action on external game state. Returns True if target is werewolf."""
        game_state.current_night_actions.seer_check_target = target_seat
        player = game_state.players.get(target_seat)
        is_werewolf = player.role == "werewolf" if player else False
        logger.info(f"Seer check: seat {target_seat} is werewolf={is_werewolf}")
        return is_werewolf

    def process_witch_action(
        self,
        game_state: WerewolfGameState,
        save_target: Optional[int] = None,
        poison_target: Optional[int] = None
    ) -> None:
        """Process witch action on external game state."""
        if save_target and game_state.witch_has_antidote:
            game_state.current_night_actions.witch_save = True
            game_state.witch_has_antidote = False
            logger.info(f"Witch saved seat {save_target}")

        if poison_target and game_state.witch_has_poison:
            game_state.current_night_actions.witch_poison_target = poison_target
            game_state.witch_has_poison = False
            logger.info(f"Witch poisoned seat {poison_target}")

    def advance_to_day(self, game_state: WerewolfGameState) -> List[int]:
        """
        Process night actions and advance to day on external game state.
        Returns list of dead player seat numbers.
        """
        deaths = []
        actions = game_state.current_night_actions

        # Process werewolf kill
        if actions.werewolf_kill_target and not actions.witch_save:
            target = game_state.players.get(actions.werewolf_kill_target)
            if target and target.is_alive:
                target.is_alive = False
                target.death_reason = DeathReason.KILLED
                target.death_day = game_state.day_number
                deaths.append(target.seat_number)
                logger.info(f"Player {target.seat_number} killed by werewolf")

        # Process witch poison
        if actions.witch_poison_target:
            target = game_state.players.get(actions.witch_poison_target)
            if target and target.is_alive:
                target.is_alive = False
                target.death_reason = DeathReason.POISONED
                target.death_day = game_state.day_number
                deaths.append(target.seat_number)
                logger.info(f"Player {target.seat_number} poisoned by witch")

        # Reset night actions
        game_state.current_night_actions = NightActions()
        
        # Advance day
        game_state.day_number += 1
        game_state.phase = WerewolfPhase.DAY

        return deaths

    def process_vote(
        self,
        game_state: WerewolfGameState,
        voter_seat: int,
        target_seat: Optional[int]
    ) -> None:
        """Process a vote on external game state."""
        if target_seat is not None:
            game_state.current_votes[voter_seat] = target_seat
        logger.info(f"Vote: seat {voter_seat} -> {target_seat}")

    def process_vote_result(
        self,
        game_state: WerewolfGameState
    ) -> tuple[Optional[int], bool, dict[int, int]]:
        """
        Process vote result on external game state.
        Returns (eliminated_seat, is_tie, vote_counts).
        """
        # Count votes
        vote_counts: dict[int, int] = {}
        for voter, target in game_state.current_votes.items():
            if target is not None:
                vote_counts[target] = vote_counts.get(target, 0) + 1

        if not vote_counts:
            return None, False, vote_counts

        # Find max votes
        max_votes = max(vote_counts.values())
        max_players = [seat for seat, count in vote_counts.items() if count == max_votes]

        # Check tie
        is_tie = len(max_players) > 1
        eliminated = None

        if not is_tie:
            eliminated = max_players[0]
            player = game_state.players.get(eliminated)
            if player:
                player.is_alive = False
                player.death_reason = DeathReason.VOTED
                player.death_day = game_state.day_number
                logger.info(f"Player {eliminated} eliminated by vote")

        # Clear votes
        game_state.current_votes = {}

        return eliminated, is_tie, vote_counts

    def check_winner(self, game_state: WerewolfGameState) -> Optional[str]:
        """Check win condition on external game state. Returns 'werewolf', 'villager', or None."""
        alive_wolves = 0
        alive_villagers = 0

        for player in game_state.players.values():
            if player.is_alive:
                if player.team == "werewolf":
                    alive_wolves += 1
                else:
                    alive_villagers += 1

        if alive_wolves == 0:
            logger.info("Game over: Villagers win")
            return "villager"
        if alive_wolves >= alive_villagers:
            logger.info("Game over: Werewolves win")
            return "werewolf"

        return None

    def process_hunter_shoot(
        self,
        game_state: WerewolfGameState,
        target_seat: int
    ) -> None:
        """Process hunter shoot on external game state."""
        target = game_state.players.get(target_seat)
        if target and target.is_alive:
            target.is_alive = False
            target.death_reason = DeathReason.SHOT
            target.death_day = game_state.day_number
            logger.info(f"Player {target_seat} shot by hunter")
