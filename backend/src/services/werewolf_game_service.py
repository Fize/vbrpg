"""Werewolf game service for managing single-player werewolf games."""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.game import GameRoom, GameRoomParticipant, GameSession, GameState
from src.services.games.werewolf_engine import (
    WerewolfEngine,
    WerewolfPhase,
    WerewolfGameState,
    PlayerState,
    GameLogEntry,
)
from src.services.ai_agents import (
    WerewolfAgent,
    SeerAgent,
    WitchAgent,
    HunterAgent,
    VillagerAgent,
)
from src.services.ai_agents.host import WerewolfHost
from src.websocket import (
    broadcast_host_announcement,
    stream_host_announcement,
    broadcast_game_state_update,
    broadcast_phase_change,
    notify_werewolf_turn,
    notify_seer_turn,
    notify_seer_result,
    notify_witch_turn,
    notify_hunter_shoot,
    stream_ai_speech,
    broadcast_vote_update,
    broadcast_vote_result,
    broadcast_game_over,
    broadcast_role_assignment,
    broadcast_ai_action,
    broadcast_waiting_for_human,
    broadcast_speech_options,
    broadcast_human_speech_complete,
    broadcast_player_speech,
    broadcast_last_words_options,
    broadcast_spectator_mode,
    broadcast_vote_options,
    broadcast_human_vote_complete,
    broadcast_human_night_action_complete,
    broadcast_ai_takeover,
)
from src.utils.errors import BadRequestError, NotFoundError

logger = logging.getLogger(__name__)


class WerewolfGameService:
    """Service for managing werewolf game sessions.
    
    This service handles:
    - Game initialization with AI players
    - Night phase execution (werewolf/seer/witch actions)
    - Day phase execution (AI speeches and voting)
    - Human player action processing
    - Win condition checking
    """
    
    def __init__(self, db: AsyncSession):
        """Initialize service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.engine = WerewolfEngine()
        self.host = WerewolfHost()
        self._ai_agents: dict[int, Any] = {}  # seat_number -> agent
        self._game_states: dict[str, WerewolfGameState] = {}  # room_code -> state
    
    def _validate_game_state(self, room_code: str, game_id: str) -> WerewolfGameState | None:
        """Validate that the current game state matches the expected game ID."""
        game_state = self._game_states.get(room_code)
        if not game_state:
            return None
        if game_state.game_id != game_id:
            logger.info(f"Game ID mismatch for room {room_code}: expected {game_id}, got {game_state.game_id}")
            return None
        if game_state.is_stopped:
            return None
        return game_state

    # =========================================================================
    # T12-T16: 人类玩家交互辅助方法
    # =========================================================================
    
    def _is_human_player(self, room_code: str, seat_number: int) -> bool:
        """
        T12: 检查指定座位号的玩家是否为人类玩家。
        
        判断逻辑：
        1. 检查游戏状态中的 human_player_seat 字段
        2. 或者检查该座位号是否不在 AI agents 字典中
        
        :param room_code: 房间代码
        :param seat_number: 座位号
        :return: 如果是人类玩家返回 True，否则返回 False
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return False
        
        # 优先使用 human_player_seat 字段判断
        if game_state.human_player_seat is not None:
            return seat_number == game_state.human_player_seat
        
        # 兼容旧逻辑：检查是否不在 AI agents 中
        return seat_number not in self._ai_agents
    
    def _set_waiting_for_human(
        self,
        room_code: str,
        action_type: str,
        timeout: int = 60
    ) -> bool:
        """
        T13: 设置等待人类玩家输入的状态。
        
        :param room_code: 房间代码
        :param action_type: 动作类型，如 'speech', 'vote', 'night_action', 'last_words'
        :param timeout: 超时时间（秒），默认60秒
        :return: 设置成功返回 True，否则返回 False
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return False
        
        game_state.waiting_for_human_action = True
        game_state.human_action_type = action_type
        game_state.human_action_timeout = timeout
        game_state.human_action_start_time = datetime.now()
        
        logger.info(f"Set waiting for human action: {action_type}, timeout: {timeout}s, room: {room_code}")
        return True
    
    def _clear_waiting_for_human(self, room_code: str) -> bool:
        """
        清除等待人类玩家输入的状态。
        
        :param room_code: 房间代码
        :return: 清除成功返回 True，否则返回 False
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return False
        
        game_state.waiting_for_human_action = False
        game_state.human_action_type = None
        game_state.human_action_timeout = None
        game_state.human_action_start_time = None
        
        logger.info(f"Cleared waiting for human action, room: {room_code}")
        return True

    def _create_temp_agent(self, game_state: WerewolfGameState, player: PlayerState):
        """为人类玩家创建临时 AI 代理，用于超时代打。"""
        agent = self._create_agent_for_role(
            role=player.role,
            seat_number=player.seat_number,
            player_name=player.player_name,
            player_id=player.player_id,
        )

        if not agent:
            return None

        if player.role == "werewolf":
            teammates = [
                {"seat_number": p.seat_number, "name": p.player_name}
                for p in game_state.players.values()
                if p.role == "werewolf" and p.seat_number != player.seat_number
            ]
            if hasattr(agent, "set_teammates"):
                agent.set_teammates(teammates)

        if player.role == "witch":
            # 同步药水剩余数量，避免临时代理使用不存在的药水
            try:
                if not game_state.witch_has_antidote and hasattr(agent, "use_antidote"):
                    agent.use_antidote()
                if not game_state.witch_has_poison and hasattr(agent, "use_poison"):
                    agent.use_poison()
            except Exception as error:
                logger.warning("Sync witch potions for temp agent failed: %s", error)

        return agent

    @staticmethod
    def _build_player_lists(game_state: WerewolfGameState) -> tuple[list[dict], list[dict]]:
        alive_players = [
            {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
            for p in game_state.players.values()
            if p.is_alive
        ]
        dead_players = [
            {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
            for p in game_state.players.values()
            if not p.is_alive
        ]
        return alive_players, dead_players

    def _build_speech_summary(self, game_state: WerewolfGameState, limit: int = 12) -> str:
        recent_speeches = self._format_speech_entries(game_state.speech_history, limit=limit)
        return self._speeches_to_text(recent_speeches)

    async def _ai_takeover_speech(self, room_code: str, game_state: WerewolfGameState, player: PlayerState):
        agent = self._create_temp_agent(game_state, player)
        if not agent:
            logger.warning("AI takeover speech skipped: temp agent missing")
            await broadcast_ai_takeover(
                room_code=room_code,
                seat_number=player.seat_number,
                action_type="speech",
                metadata={"reason": "agent_missing"},
            )
            self._clear_waiting_for_human(room_code)
            return

        alive_players, dead_players = self._build_player_lists(game_state)
        agent_game_state = {
            "day_number": game_state.day_number,
            "alive_players": alive_players,
            "dead_players": dead_players,
        }
        previous_speeches = self._format_speech_entries(game_state.speech_history, limit=12)

        speech_stream = agent.generate_speech_stream(
            game_state=agent_game_state,
            previous_speeches=previous_speeches,
        )
        speech_content = await stream_ai_speech(
            room_code=room_code,
            speaker_seat=player.seat_number,
            speaker_name=player.player_name,
            speech_stream=speech_stream,
        )

        game_state.game_logs.append(
            f"第{game_state.day_number}天 - {player.seat_number}号发言: {speech_content} (AI代打)"
        )
        self._record_speech_entry(
            game_state,
            seat_number=player.seat_number,
            player_name=player.player_name,
            content=speech_content,
        )

        await broadcast_ai_takeover(
            room_code=room_code,
            seat_number=player.seat_number,
            action_type="speech",
        )
        self._clear_waiting_for_human(room_code)

    async def _ai_takeover_vote(self, room_code: str, game_state: WerewolfGameState, player: PlayerState):
        agent = self._create_temp_agent(game_state, player)
        vote_target: int | None = None

        if agent:
            alive_players, dead_players = self._build_player_lists(game_state)
            agent_game_state = {
                "day_number": game_state.day_number,
                "alive_players": alive_players,
                "dead_players": dead_players,
            }
            speech_summary = self._build_speech_summary(game_state)
            voteable_players = [
                {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                for p in game_state.players.values()
                if p.is_alive and p.seat_number != player.seat_number
            ]

            try:
                result = await agent.decide_vote(
                    game_state=agent_game_state,
                    speech_summary=speech_summary,
                    voteable_players=voteable_players,
                )
                raw_target = result.get("target") if isinstance(result, dict) else result
                vote_target = self._normalize_seat_number(raw_target)
            except Exception as error:
                logger.error("AI takeover vote decision failed: %s", error)

        self.engine.process_vote(game_state, player.seat_number, vote_target)

        await broadcast_vote_update(
            room_code=room_code,
            voter_seat=player.seat_number,
            voter_name=player.player_name,
            target_seat=vote_target,
            target_name=f"玩家{vote_target}" if vote_target else None,
        )
        await broadcast_human_vote_complete(
            room_code=room_code,
            voter_seat=player.seat_number,
            target_seat=vote_target,
            voter_name=player.player_name,
            target_name=f"玩家{vote_target}" if vote_target else None,
        )

        game_state.game_logs.append(
            f"投票: {player.seat_number}号投给{vote_target}号 (AI代打)" if vote_target else f"投票: {player.seat_number}号弃票 (AI代打)"
        )

        await broadcast_ai_takeover(
            room_code=room_code,
            seat_number=player.seat_number,
            action_type="vote",
            metadata={"target_seat": vote_target},
        )
        self._clear_waiting_for_human(room_code)

    async def _ai_takeover_werewolf_kill(
        self,
        room_code: str,
        game_state: WerewolfGameState,
        player: PlayerState,
    ) -> None:
        agent = self._create_temp_agent(game_state, player)
        target_seat: int | None = None

        if agent:
            alive_players, dead_players = self._build_player_lists(game_state)
            speech_history_text = ""
            if game_state.day_number > 1 and game_state.speech_history:
                speech_history_text = self._speeches_to_text(game_state.speech_history)

            agent_game_state = {
                "day_number": game_state.day_number,
                "alive_players": alive_players,
                "dead_players": dead_players,
                "speech_history": speech_history_text,
            }
            available_targets = [
                {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                for p in game_state.players.values()
                if p.is_alive and p.role != "werewolf"
            ]
            try:
                result = await agent.decide_night_action(
                    game_state=agent_game_state,
                    available_targets=available_targets,
                )
                raw_target = result.get("target") if isinstance(result, dict) else result
                target_seat = self._normalize_seat_number(raw_target)
            except Exception as error:
                logger.error("AI takeover werewolf decision failed: %s", error)

        self.engine.process_werewolf_action(game_state, target_seat)
        game_state.game_logs.append(
            f"夜晚：狼人AI代打选择击杀{target_seat if target_seat is not None else '空刀'}"
        )
        await broadcast_ai_takeover(
            room_code=room_code,
            seat_number=player.seat_number,
            action_type="werewolf_kill",
            metadata={"target_seat": target_seat},
        )
        self._clear_waiting_for_human(room_code)

    async def _ai_takeover_seer_check(
        self,
        room_code: str,
        game_state: WerewolfGameState,
        player: PlayerState,
    ) -> None:
        agent = self._create_temp_agent(game_state, player)
        target_seat: int | None = None
        is_werewolf = False

        if agent:
            alive_players, dead_players = self._build_player_lists(game_state)
            speech_history_text = ""
            if game_state.day_number > 1 and game_state.speech_history:
                speech_history_text = self._speeches_to_text(game_state.speech_history)

            agent_game_state = {
                "day_number": game_state.day_number,
                "alive_players": alive_players,
                "dead_players": dead_players,
                "speech_history": speech_history_text,
            }
            available_targets = [
                {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                for p in game_state.players.values()
                if p.is_alive and p.seat_number != player.seat_number
            ]
            try:
                result = await agent.decide_night_action(
                    game_state=agent_game_state,
                    available_targets=available_targets,
                )
                raw_target = result.get("target") if isinstance(result, dict) else result
                target_seat = self._normalize_seat_number(raw_target)
            except Exception as error:
                logger.error("AI takeover seer decision failed: %s", error)

        if target_seat:
            is_werewolf = self.engine.process_seer_action(game_state, target_seat)
            target_player = game_state.players.get(target_seat)
            target_name = target_player.player_name if target_player else f"玩家{target_seat}"
            if agent and hasattr(agent, "add_check_result"):
                agent.add_check_result(target_seat, target_name, is_werewolf, game_state.day_number)
            game_state.game_logs.append(
                f"夜晚：预言家AI代打查验{target_seat}号，结果是{'狼人' if is_werewolf else '好人'}"
            )

        await broadcast_ai_takeover(
            room_code=room_code,
            seat_number=player.seat_number,
            action_type="seer_check",
            metadata={"target_seat": target_seat, "result": "werewolf" if is_werewolf else "villager"},
        )
        self._clear_waiting_for_human(room_code)

    async def _ai_takeover_witch_action(
        self,
        room_code: str,
        game_state: WerewolfGameState,
        player: PlayerState,
    ) -> None:
        agent = self._create_temp_agent(game_state, player)
        save_target = None
        poison_target = None

        killed_seat = game_state.current_night_actions.werewolf_kill_target

        if agent:
            alive_players, dead_players = self._build_player_lists(game_state)
            agent_game_state = {
                "day_number": game_state.day_number,
                "alive_players": alive_players,
                "dead_players": dead_players,
            }
            available_targets = [
                {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                for p in game_state.players.values()
                if p.is_alive and p.seat_number != player.seat_number
            ]
            killed_player_info = None
            if killed_seat:
                killed_p = game_state.players.get(killed_seat)
                if killed_p:
                    killed_player_info = {
                        "seat_number": killed_p.seat_number,
                        "name": killed_p.player_name,
                        "player_id": killed_p.player_id,
                    }

            try:
                result = await agent.decide_night_action(
                    game_state=agent_game_state,
                    available_targets=available_targets,
                    killed_player=killed_player_info,
                )
                if isinstance(result, dict):
                    action = result.get("action", "pass")
                    raw_target = result.get("target")
                    if action == "save":
                        save_target = self._normalize_seat_number(raw_target)
                    elif action == "poison":
                        poison_target = self._normalize_seat_number(raw_target)
            except Exception as error:
                logger.error("AI takeover witch decision failed: %s", error)

        self.engine.process_witch_action(
            game_state,
            save_target=save_target,
            poison_target=poison_target,
        )

        if save_target:
            game_state.game_logs.append(f"夜晚：女巫AI代打使用解药救了{save_target}号")
        if poison_target:
            game_state.game_logs.append(f"夜晚：女巫AI代打使用毒药毒了{poison_target}号")
        if not save_target and not poison_target:
            game_state.game_logs.append("夜晚：女巫AI代打未使用任何药水")

        await broadcast_ai_takeover(
            room_code=room_code,
            seat_number=player.seat_number,
            action_type="witch_action",
            metadata={"save_target": save_target, "poison_target": poison_target},
        )
        self._clear_waiting_for_human(room_code)

    async def _ai_takeover_hunter_shoot(
        self,
        room_code: str,
        game_state: WerewolfGameState,
        player: PlayerState,
    ) -> None:
        agent = self._create_temp_agent(game_state, player)
        shoot_target: int | None = None

        if agent:
            alive_players, dead_players = self._build_player_lists(game_state)
            speech_history_text = self._speeches_to_text(game_state.speech_history) if game_state.speech_history else ""
            agent_game_state = {
                "day_number": game_state.day_number,
                "alive_players": alive_players,
                "dead_players": dead_players,
                "speech_history": speech_history_text,
            }
            available_targets = [
                {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                for p in game_state.players.values()
                if p.is_alive and p.seat_number != player.seat_number
            ]
            death_reason = player.death_reason.value if player.death_reason else "unknown"
            try:
                result = await agent.decide_shoot(
                    game_state=agent_game_state,
                    death_reason=death_reason,
                    available_targets=available_targets,
                )
                raw_target = result.get("target") if isinstance(result, dict) else result
                shoot_target = self._normalize_seat_number(raw_target)
            except Exception as error:
                logger.error("AI takeover hunter decision failed: %s", error)

        if shoot_target:
            self.engine.process_hunter_shoot(game_state, shoot_target)
            game_state.game_logs.append(f"猎人AI代打开枪带走了{shoot_target}号")
            await broadcast_host_announcement(
                room_code=room_code,
                announcement_type="hunter_shoot",
                content=f"猎人AI代打，带走了{shoot_target}号玩家！",
                metadata={"target_seat": shoot_target},
            )
        else:
            game_state.game_logs.append("猎人AI代打放弃开枪")

        await broadcast_ai_takeover(
            room_code=room_code,
            seat_number=player.seat_number,
            action_type="hunter_shoot",
            metadata={"target_seat": shoot_target},
        )
        self._clear_waiting_for_human(room_code)

    async def _ai_takeover_night_action(
        self,
        room_code: str,
        game_state: WerewolfGameState,
        player: PlayerState,
        action_type: str,
    ) -> None:
        if action_type == "werewolf_kill":
            await self._ai_takeover_werewolf_kill(room_code, game_state, player)
        elif action_type == "seer_check":
            await self._ai_takeover_seer_check(room_code, game_state, player)
        elif action_type == "witch_action":
            await self._ai_takeover_witch_action(room_code, game_state, player)
        elif action_type == "hunter_shoot":
            await self._ai_takeover_hunter_shoot(room_code, game_state, player)
        else:
            logger.warning("Unsupported night action for AI takeover: %s", action_type)
            self._clear_waiting_for_human(room_code)

    async def _check_human_timeout(self, room_code: str, game_id: str) -> bool:
        """检查人类玩家等待是否超时，超时则触发AI代打。"""
        game_state = self._validate_game_state(room_code, game_id)
        if not game_state or not game_state.waiting_for_human_action:
            return False

        if not game_state.human_action_start_time or not game_state.human_action_timeout:
            return False

        elapsed = (datetime.now() - game_state.human_action_start_time).total_seconds()
        if elapsed < game_state.human_action_timeout:
            return False

        human_seat = game_state.human_player_seat
        if human_seat is None:
            logger.warning("Human seat missing during timeout check")
            self._clear_waiting_for_human(room_code)
            return True

        player = game_state.players.get(human_seat)
        if not player:
            logger.warning("Player state missing during timeout check")
            self._clear_waiting_for_human(room_code)
            return True

        action_type = game_state.human_action_type
        logger.info(
            "Human action timeout detected: room=%s seat=%s action=%s", room_code, human_seat, action_type
        )

        if action_type == "speech":
            await self._ai_takeover_speech(room_code, game_state, player)
        elif action_type == "vote":
            await self._ai_takeover_vote(room_code, game_state, player)
        elif action_type in {"werewolf_kill", "seer_check", "witch_action", "hunter_shoot"}:
            await self._ai_takeover_night_action(room_code, game_state, player, action_type)
        else:
            self._clear_waiting_for_human(room_code)
        return True
    
    def generate_speech_options(
        self,
        room_code: str,
        seat_number: int
    ) -> list[dict]:
        """
        T16: 生成动态预设发言选项。
        
        根据玩家角色和当前游戏状态生成适合的发言选项。
        
        :param room_code: 房间代码
        :param seat_number: 玩家座位号
        :return: 预设发言选项列表
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return []
        
        player = game_state.players.get(seat_number)
        if not player:
            return []
        
        options = []
        role = player.role
        day_number = game_state.day_number
        
        # 获取存活玩家列表
        alive_seats = [p.seat_number for p in game_state.players.values() if p.is_alive and p.seat_number != seat_number]
        
        # 通用选项
        options.append({
            "id": "pass",
            "text": "我没什么想说的，过。",
            "type": "neutral"
        })
        
        options.append({
            "id": "innocent",
            "text": "我是好人，请大家相信我。",
            "type": "defense"
        })
        
        # 第一天特殊选项
        if day_number == 1:
            options.append({
                "id": "first_day_peace",
                "text": "第一天信息不足，建议大家多观察。",
                "type": "neutral"
            })
        
        # 根据角色生成特定选项
        if role == "werewolf":
            # 狼人伪装选项
            options.append({
                "id": "wolf_disguise_villager",
                "text": "我是普通村民，昨晚没有任何信息。",
                "type": "disguise"
            })
            options.append({
                "id": "wolf_disguise_seer",
                "text": "我是预言家，昨晚验了一个人，是好人。",
                "type": "disguise"
            })
            if alive_seats:
                suspect = alive_seats[0]
                options.append({
                    "id": f"wolf_accuse_{suspect}",
                    "text": f"我觉得{suspect}号很可疑，建议大家重点关注。",
                    "type": "accusation"
                })
        
        elif role == "seer":
            # 预言家选项
            options.append({
                "id": "seer_reveal",
                "text": "我是预言家，我有查验信息要分享。",
                "type": "reveal"
            })
            options.append({
                "id": "seer_hide",
                "text": "我昨晚的信息暂时不方便说，但我是好人。",
                "type": "neutral"
            })
        
        elif role == "witch":
            # 女巫选项
            options.append({
                "id": "witch_reveal",
                "text": "我是女巫，我有重要信息。",
                "type": "reveal"
            })
            options.append({
                "id": "witch_hide",
                "text": "我是好人，但我的身份比较重要，暂时不方便说。",
                "type": "neutral"
            })
        
        elif role == "hunter":
            # 猎人选项
            options.append({
                "id": "hunter_reveal",
                "text": "我是猎人，如果我被投出去，我会带走一个人。",
                "type": "reveal"
            })
            options.append({
                "id": "hunter_hide",
                "text": "我是好人，请不要投我。",
                "type": "neutral"
            })
        
        elif role == "villager":
            # 村民选项
            options.append({
                "id": "villager_observe",
                "text": "我是村民，我仔细听了大家的发言，我觉得...",
                "type": "neutral"
            })
        
        # 如果有死亡信息，添加相关选项
        dead_players = [p for p in game_state.players.values() if not p.is_alive]
        if dead_players and day_number > 1:
            options.append({
                "id": "analyze_death",
                "text": "根据昨晚的死亡情况分析，我认为狼人可能是...",
                "type": "analysis"
            })
        
        return options

    async def process_human_speech(
        self,
        room_code: str,
        player_id: str,
        content: str
    ) -> dict:
        """T14: 处理人类玩家发言.
        
        接收并处理人类玩家提交的发言内容，记录到发言历史，
        并清除等待状态以继续游戏流程。
        
        Args:
            room_code: 房间代码
            player_id: 玩家ID
            content: 发言内容
            
        Returns:
            dict: 处理结果，包含success状态和相关信息
        """
        state = self._game_states.get(room_code)
        if not state:
            return {"success": False, "error": "游戏不存在"}
        
        # 验证是否在等待人类玩家发言
        if not state.waiting_for_human_action:
            return {"success": False, "error": "当前不在等待人类玩家行动"}
        
        if state.human_action_type != "speech":
            return {"success": False, "error": f"当前等待的行动类型不是发言，而是 {state.human_action_type}"}
        
        # 验证是否是正确的玩家
        human_seat = state.human_player_seat
        if human_seat is None:
            return {"success": False, "error": "找不到人类玩家座位"}
        
        # 验证player_id对应的座位
        player_seat = None
        for seat_num, player_state in state.players.items():
            if player_state.player_id == player_id:
                player_seat = seat_num
                break
        
        if player_seat != human_seat:
            return {"success": False, "error": "只有人类玩家可以提交发言"}
        
        # 获取玩家信息
        player_state = state.players.get(human_seat)
        if not player_state:
            return {"success": False, "error": "找不到玩家状态"}
        
        # 记录发言到历史
        speech_entry = {
            "day": state.day_number,
            "phase": "day",
            "seat_number": human_seat,
            "player_name": player_state.player_name,
            "content": content,
            "is_human": True
        }
        state.speech_history.append(speech_entry)
        
        # 清除等待状态
        self._clear_waiting_for_human(room_code)
        
        return {
            "success": True,
            "seat_number": human_seat,
            "player_name": player_state.player_name,
            "content": content,
            "day": state.day_number
        }

    # =========================================================================
    # Phase 3: 投票交互 (T23-T25)
    # =========================================================================

    def generate_vote_options(self, room_code: str, voter_seat: int) -> list[dict]:
        """T24: 生成投票选项列表.
        
        生成当前可以投票的玩家列表（排除自己）。
        
        Args:
            room_code: 房间代码
            voter_seat: 投票者座位号
            
        Returns:
            可投票选项列表，每项包含 seat_number, player_name
        """
        state = self._game_states.get(room_code)
        if not state:
            return []
        
        options = []
        for seat_num, player_state in state.players.items():
            # 排除自己和已死亡玩家
            if seat_num != voter_seat and player_state.is_alive:
                options.append({
                    "seat_number": seat_num,
                    "player_name": player_state.player_name,
                    "player_id": player_state.player_id
                })
        
        # 按座位号排序
        options.sort(key=lambda x: x["seat_number"])
        return options

    async def process_human_vote(
        self,
        room_code: str,
        player_id: str,
        target_seat: int | None
    ) -> dict:
        """T24: 处理人类玩家投票.
        
        接收并处理人类玩家提交的投票，记录投票结果，
        并清除等待状态以继续游戏流程。
        
        Args:
            room_code: 房间代码
            player_id: 玩家ID
            target_seat: 目标座位号（None 表示弃票）
            
        Returns:
            dict: 处理结果，包含success状态和相关信息
        """
        state = self._game_states.get(room_code)
        if not state:
            return {"success": False, "error": "游戏不存在"}
        
        # 验证是否在等待人类玩家投票
        if not state.waiting_for_human_action:
            return {"success": False, "error": "当前不在等待人类玩家行动"}
        
        if state.human_action_type != "vote":
            return {"success": False, "error": f"当前等待的行动类型不是投票，而是 {state.human_action_type}"}
        
        # 验证是否是正确的玩家
        human_seat = state.human_player_seat
        if human_seat is None:
            return {"success": False, "error": "找不到人类玩家座位"}
        
        # 验证player_id对应的座位
        player_seat = None
        for seat_num, player_state in state.players.items():
            if player_state.player_id == player_id:
                player_seat = seat_num
                break
        
        if player_seat != human_seat:
            return {"success": False, "error": "只有人类玩家可以提交投票"}
        
        # 获取玩家信息
        player_state = state.players.get(human_seat)
        if not player_state:
            return {"success": False, "error": "找不到玩家状态"}
        
        # 验证投票目标（如果不是弃票）
        normalized_target = self._normalize_seat_number(target_seat)
        if normalized_target is not None:
            target_player = state.players.get(normalized_target)
            if not target_player:
                return {"success": False, "error": f"找不到目标玩家 {normalized_target}"}
            if not target_player.is_alive:
                return {"success": False, "error": f"目标玩家 {normalized_target} 已死亡"}
            if normalized_target == human_seat:
                return {"success": False, "error": "不能投票给自己"}
        
        # 处理投票
        self.engine.process_vote(state, human_seat, normalized_target)
        
        # 记录日志
        target_name = f"玩家{normalized_target}" if normalized_target else None
        state.game_logs.append(
            f"投票: {human_seat}号投给{normalized_target}号" if normalized_target 
            else f"投票: {human_seat}号弃票"
        )
        
        # 广播投票结果
        await broadcast_vote_update(
            room_code=room_code,
            voter_seat=human_seat,
            voter_name=f"玩家{human_seat}",
            target_seat=normalized_target,
            target_name=target_name
        )
        
        # 广播人类投票完成
        await broadcast_human_vote_complete(
            room_code=room_code,
            voter_seat=human_seat,
            target_seat=normalized_target,
            voter_name=player_state.player_name,
            target_name=target_name
        )
        
        # 清除等待状态
        self._clear_waiting_for_human(room_code)
        
        return {
            "success": True,
            "seat_number": human_seat,
            "player_name": player_state.player_name,
            "target_seat": normalized_target,
            "day": state.day_number
        }

    async def process_human_night_action(
        self,
        room_code: str,
        player_id: str,
        action_type: str,
        target_seat: int | None = None,
        witch_action: str | None = None
    ) -> dict:
        """T35: 处理人类玩家夜间行动.
        
        统一处理所有角色的夜间行动：狼人杀人、预言家查验、女巫救毒、猎人开枪。
        
        Args:
            room_code: 房间代码
            player_id: 玩家ID
            action_type: 行动类型 ('werewolf_kill', 'seer_check', 'witch_action', 'hunter_shoot')
            target_seat: 目标座位号（None表示不行动）
            witch_action: 女巫专用 - 'save'|'poison'|'pass'
            
        Returns:
            dict: 处理结果，包含success状态和相关信息
        """
        state = self._game_states.get(room_code)
        if not state:
            return {"success": False, "error": "游戏不存在"}
        
        # 验证是否在等待人类玩家行动
        if not state.waiting_for_human_action:
            return {"success": False, "error": "当前不在等待人类玩家行动"}
        
        # 验证行动类型是否匹配
        expected_types = {
            "werewolf_kill": "werewolf_kill",
            "seer_check": "seer_check", 
            "witch_action": "witch_action",
            "hunter_shoot": "hunter_shoot"
        }
        if state.human_action_type != expected_types.get(action_type):
            return {"success": False, "error": f"行动类型不匹配，期望 {state.human_action_type}，收到 {action_type}"}
        
        # 获取人类玩家座位
        human_seat = state.human_player_seat
        if human_seat is None:
            return {"success": False, "error": "找不到人类玩家座位"}
        
        # 验证player_id对应的座位
        player_seat = None
        for seat_num, player_state in state.players.items():
            if player_state.player_id == player_id:
                player_seat = seat_num
                break
        
        if player_seat != human_seat:
            return {"success": False, "error": "只有人类玩家可以提交夜间行动"}
        
        # 获取玩家信息
        player = state.players.get(human_seat)
        if not player:
            return {"success": False, "error": "找不到玩家状态"}
        
        # 验证玩家角色与行动类型匹配
        role_action_map = {
            "werewolf": "werewolf_kill",
            "seer": "seer_check",
            "witch": "witch_action",
            "hunter": "hunter_shoot"
        }
        expected_role = None
        for role, act in role_action_map.items():
            if act == action_type:
                expected_role = role
                break
        
        if expected_role and player.role != expected_role:
            return {"success": False, "error": f"角色不匹配，期望 {expected_role}，实际 {player.role}"}
        
        # 规范化目标座位号
        normalized_target = self._normalize_seat_number(target_seat)
        
        # 根据行动类型处理
        result = {"success": True}
        
        if action_type == "werewolf_kill":
            # 狼人杀人
            if normalized_target is not None:
                target_player = state.players.get(normalized_target)
                if not target_player:
                    return {"success": False, "error": f"找不到目标玩家 {normalized_target}"}
                if not target_player.is_alive:
                    return {"success": False, "error": f"目标玩家 {normalized_target} 已死亡"}
                # 狼人不能杀同伴
                if target_player.role == "werewolf":
                    return {"success": False, "error": "不能击杀狼人同伴"}
            
            self.engine.process_werewolf_action(state, normalized_target)
            if normalized_target:
                state.game_logs.append(f"夜晚：狼人选择击杀{normalized_target}号玩家")
            else:
                state.game_logs.append("夜晚：狼人选择空刀")
            
            result["target_seat"] = normalized_target
            result["action"] = "kill" if normalized_target else "skip"
            
        elif action_type == "seer_check":
            # 预言家查验
            if normalized_target is not None:
                target_player = state.players.get(normalized_target)
                if not target_player:
                    return {"success": False, "error": f"找不到目标玩家 {normalized_target}"}
                if not target_player.is_alive:
                    return {"success": False, "error": f"目标玩家 {normalized_target} 已死亡"}
                if normalized_target == human_seat:
                    return {"success": False, "error": "不能查验自己"}
                
                is_werewolf = self.engine.process_seer_action(state, normalized_target)
                state.game_logs.append(f"夜晚：预言家查验了{normalized_target}号玩家，结果是{'狼人' if is_werewolf else '好人'}")
                
                result["target_seat"] = normalized_target
                result["is_werewolf"] = is_werewolf
                result["check_result"] = "狼人" if is_werewolf else "好人"
            else:
                state.game_logs.append("夜晚：预言家未查验任何人")
                result["target_seat"] = None
                result["check_result"] = None
                
        elif action_type == "witch_action":
            # 女巫救毒
            if witch_action not in ["save", "poison", "pass", None]:
                return {"success": False, "error": f"无效的女巫行动: {witch_action}"}
            
            save_target = None
            poison_target = None
            
            if witch_action == "save":
                # 救人
                if not state.witch_has_antidote:
                    return {"success": False, "error": "解药已用完"}
                killed_seat = state.current_night_actions.werewolf_kill_target
                if normalized_target != killed_seat:
                    return {"success": False, "error": "只能救今晚被杀的玩家"}
                # 检查自救限制
                if normalized_target == human_seat and state.day_number > 1:
                    return {"success": False, "error": "首夜之后不能自救"}
                save_target = normalized_target
                state.game_logs.append(f"夜晚：女巫救了{save_target}号玩家")
                
            elif witch_action == "poison":
                # 毒人
                if not state.witch_has_poison:
                    return {"success": False, "error": "毒药已用完"}
                if normalized_target is None:
                    return {"success": False, "error": "毒人必须指定目标"}
                target_player = state.players.get(normalized_target)
                if not target_player:
                    return {"success": False, "error": f"找不到目标玩家 {normalized_target}"}
                if not target_player.is_alive:
                    return {"success": False, "error": f"目标玩家 {normalized_target} 已死亡"}
                if normalized_target == human_seat:
                    return {"success": False, "error": "不能毒自己"}
                poison_target = normalized_target
                state.game_logs.append(f"夜晚：女巫毒了{poison_target}号玩家")
            else:
                # pass - 不使用药水
                state.game_logs.append("夜晚：女巫未使用任何药水")
            
            self.engine.process_witch_action(state, save_target=save_target, poison_target=poison_target)
            
            # 更新药水状态
            if save_target:
                state.witch_has_antidote = False
            if poison_target:
                state.witch_has_poison = False
            
            result["witch_action"] = witch_action
            result["save_target"] = save_target
            result["poison_target"] = poison_target
            
        elif action_type == "hunter_shoot":
            # 猎人开枪
            if normalized_target is not None:
                target_player = state.players.get(normalized_target)
                if not target_player:
                    return {"success": False, "error": f"找不到目标玩家 {normalized_target}"}
                if not target_player.is_alive:
                    return {"success": False, "error": f"目标玩家 {normalized_target} 已死亡"}
                
                self.engine.process_hunter_shoot(state, normalized_target)
                state.game_logs.append(f"猎人开枪带走了{normalized_target}号玩家")
                
                # 广播猎人开枪
                await broadcast_host_announcement(
                    room_code=room_code,
                    announcement_type="hunter_shoot",
                    content=f"猎人发动技能，带走了{normalized_target}号玩家！",
                    metadata={"target_seat": normalized_target}
                )
            else:
                state.game_logs.append("猎人选择不开枪")
            
            result["target_seat"] = normalized_target
            result["action"] = "shoot" if normalized_target else "skip"
        
        # 广播人类夜间行动完成
        await broadcast_human_night_action_complete(
            room_code=room_code,
            seat_number=human_seat,
            action_type=action_type,
            result=result
        )
        
        # 清除等待状态
        self._clear_waiting_for_human(room_code)
        
        result["seat_number"] = human_seat
        result["player_name"] = player.player_name
        return result

    # =========================================================================
    # Phase 4.1: 狼人私密讨论 (T40-T45)
    # =========================================================================

    def _get_werewolf_teammates(self, room_code: str, seat_number: int) -> list[dict]:
        """
        获取指定狼人玩家的狼队友列表。
        
        Args:
            room_code: 房间代码
            seat_number: 当前狼人座位号
            
        Returns:
            狼队友列表，每项包含 seat_number, player_name
        """
        state = self._game_states.get(room_code)
        if not state:
            return []
        
        teammates = []
        for seat_num, player in state.players.items():
            if player.role == "werewolf" and player.is_alive and seat_num != seat_number:
                teammates.append({
                    "seat_number": seat_num,
                    "player_name": player.player_name,
                    "player_id": player.player_id
                })
        
        return teammates

    def _get_all_werewolves(self, room_code: str) -> list[dict]:
        """
        获取所有存活的狼人玩家列表。
        
        Args:
            room_code: 房间代码
            
        Returns:
            狼人列表，每项包含 seat_number, player_name, player_id
        """
        state = self._game_states.get(room_code)
        if not state:
            return []
        
        werewolves = []
        for seat_num, player in state.players.items():
            if player.role == "werewolf" and player.is_alive:
                werewolves.append({
                    "seat_number": seat_num,
                    "player_name": player.player_name,
                    "player_id": player.player_id
                })
        
        return werewolves

    async def process_werewolf_chat(
        self,
        room_code: str,
        player_id: str,
        content: str
    ) -> dict:
        """
        T41: 处理狼人私密讨论消息。
        
        接收狼人玩家的讨论消息，记录到 werewolf_private_chat，
        并广播给所有狼人（仅狼人可见）。
        
        Args:
            room_code: 房间代码
            player_id: 发言狼人的玩家ID
            content: 消息内容
            
        Returns:
            dict: 处理结果，包含success状态和消息信息
        """
        from src.websocket import broadcast_wolf_chat_message
        
        state = self._game_states.get(room_code)
        if not state:
            return {"success": False, "error": "游戏不存在"}
        
        # 验证当前是狼人行动阶段
        if state.phase != WerewolfPhase.NIGHT_WEREWOLF:
            return {"success": False, "error": "当前不是狼人行动阶段"}
        
        # 查找发言者座位号
        sender_seat = None
        sender_player = None
        for seat_num, player in state.players.items():
            if player.player_id == player_id:
                sender_seat = seat_num
                sender_player = player
                break
        
        if sender_seat is None:
            return {"success": False, "error": "找不到玩家"}
        
        # 验证发言者是狼人
        if sender_player.role != "werewolf":
            return {"success": False, "error": "只有狼人可以使用私密讨论"}
        
        # 验证发言者存活
        if not sender_player.is_alive:
            return {"success": False, "error": "已死亡的玩家不能发言"}
        
        # 验证消息内容
        if not content or not content.strip():
            return {"success": False, "error": "消息内容不能为空"}
        
        content = content.strip()
        
        # 创建讨论消息记录
        chat_entry = {
            "night_number": state.day_number,
            "seat_number": sender_seat,
            "player_name": sender_player.player_name,
            "player_id": player_id,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "is_human": sender_seat == state.human_player_seat
        }
        
        # 记录到 werewolf_private_chat
        state.werewolf_private_chat.append(chat_entry)
        
        logger.info(f"Werewolf chat recorded: seat={sender_seat}, content_length={len(content)}")
        
        # 获取所有狼人的 player_id 用于广播
        werewolves = self._get_all_werewolves(room_code)
        werewolf_player_ids = [w["player_id"] for w in werewolves]
        
        # 广播给所有狼人
        await broadcast_wolf_chat_message(
            room_code=room_code,
            sender_seat=sender_seat,
            sender_name=sender_player.player_name,
            content=content,
            werewolf_player_ids=werewolf_player_ids
        )
        
        return {
            "success": True,
            "seat_number": sender_seat,
            "player_name": sender_player.player_name,
            "content": content,
            "night_number": state.day_number
        }

    def get_werewolf_chat_history(
        self,
        room_code: str,
        night_number: int | None = None
    ) -> list[dict]:
        """
        获取狼人私密讨论历史记录。
        
        Args:
            room_code: 房间代码
            night_number: 指定夜晚（可选，None 表示所有夜晚）
            
        Returns:
            讨论记录列表
        """
        state = self._game_states.get(room_code)
        if not state:
            return []
        
        if night_number is None:
            return list(state.werewolf_private_chat)
        
        return [
            entry for entry in state.werewolf_private_chat
            if entry.get("night_number") == night_number
        ]

    # =========================================================================
    # T48-T49: 遗言处理方法
    # =========================================================================

    def _generate_last_words_options(
        self,
        game_state: WerewolfGameState,
        seat_number: int,
        death_reason: str
    ) -> list[dict]:
        """
        T48: 生成遗言预设选项。
        
        Args:
            game_state: 游戏状态
            seat_number: 玩家座位号
            death_reason: 死亡原因
            
        Returns:
            预设选项列表
        """
        player = game_state.players.get(seat_number)
        if not player:
            return []
        
        role = player.role
        options = []
        
        # 通用选项
        options.append({
            "id": "no_words",
            "text": "我没什么想说的，走了。",
            "type": "skip"
        })
        
        # 根据角色生成特定选项
        if role == "werewolf":
            # 狼人遗言选项 - 可能需要保护队友
            options.extend([
                {
                    "id": "protect_teammate",
                    "text": "我是好人，请相信我的发言，找到真正的狼人。",
                    "type": "deception"
                },
                {
                    "id": "fake_seer",
                    "text": "我是预言家，我验过的人里面有狼！",
                    "type": "deception"
                },
                {
                    "id": "random_accusation",
                    "text": "我确定X号就是狼人，请大家投他！",
                    "type": "accusation",
                    "needs_target": True
                }
            ])
        elif role == "seer":
            # 预言家遗言选项 - 需要传递信息
            options.extend([
                {
                    "id": "reveal_identity",
                    "text": "我是真预言家！请相信我的验人结果！",
                    "type": "reveal"
                },
                {
                    "id": "share_check_result",
                    "text": "我验过X号，他是好人/狼人！",
                    "type": "information",
                    "needs_target": True
                }
            ])
        elif role == "witch":
            # 女巫遗言选项
            options.extend([
                {
                    "id": "reveal_identity",
                    "text": "我是女巫，我的药已经用完了。",
                    "type": "reveal"
                },
                {
                    "id": "share_poison_info",
                    "text": "我毒过X号，他是狼人！",
                    "type": "information",
                    "needs_target": True
                }
            ])
        elif role == "hunter":
            # 猎人遗言选项（猎人死亡后会有开枪环节）
            options.extend([
                {
                    "id": "reveal_identity",
                    "text": "我是猎人，我会带走一个狼人！",
                    "type": "reveal"
                }
            ])
        else:
            # 村民遗言选项
            options.extend([
                {
                    "id": "innocent_plea",
                    "text": "我是好人，你们投错了！",
                    "type": "plea"
                },
                {
                    "id": "suspicion",
                    "text": "我怀疑X号是狼人，请大家注意。",
                    "type": "suspicion",
                    "needs_target": True
                }
            ])
        
        # 根据死亡原因添加特定选项
        if death_reason == "vote":
            options.append({
                "id": "wrongful_death",
                "text": "你们会后悔的，我是好人！",
                "type": "plea"
            })
        elif death_reason == "night_kill":
            options.append({
                "id": "wolf_analysis",
                "text": "杀我的狼人可能是昨天发言中最可疑的那个...",
                "type": "analysis"
            })
        
        return options

    async def process_human_last_words(
        self,
        room_code: str,
        player_id: str,
        content: str
    ) -> dict:
        """
        T49: 处理人类玩家的遗言输入。
        
        Args:
            room_code: 房间代码
            player_id: 玩家ID
            content: 遗言内容
            
        Returns:
            处理结果字典
        """
        state = self._game_states.get(room_code)
        if not state:
            return {"success": False, "error": "游戏不存在"}
        
        # 验证是否在等待遗言
        if not state.waiting_for_human_action or state.human_action_type != "last_words":
            return {"success": False, "error": "当前不是遗言阶段"}
        
        # 验证玩家
        dead_seat = state.last_words_seat
        if dead_seat is None:
            return {"success": False, "error": "没有等待遗言的玩家"}
        
        player = state.players.get(dead_seat)
        if not player:
            return {"success": False, "error": "玩家不存在"}
        
        # 验证玩家身份
        if player.player_id != player_id:
            return {"success": False, "error": "不是你的遗言回合"}
        
        # 记录遗言
        if content and content.strip():
            state.game_logs.append(
                f"第{state.day_number}天 - {dead_seat}号遗言: {content}"
            )
            self._record_speech_entry(
                state,
                seat_number=dead_seat,
                player_name=player.player_name,
                content=content,
                speech_type="last_words"
            )
            
            # 广播遗言
            await broadcast_player_speech(
                room_code=room_code,
                seat_number=dead_seat,
                player_name=player.player_name,
                content=content,
                speech_type="last_words"
            )
        else:
            # 跳过遗言
            state.game_logs.append(
                f"第{state.day_number}天 - {dead_seat}号选择不发表遗言"
            )
        
        # 清除等待状态
        self._clear_waiting_for_human(room_code)
        state.last_words_seat = None
        state.last_words_reason = None
        
        # T53: 切换到观战模式
        if state.human_player_seat == dead_seat:
            state.is_spectator_after_death = True
            await broadcast_spectator_mode(
                room_code=room_code,
                player_id=player_id,
                seat_number=dead_seat
            )
        
        return {
            "success": True,
            "seat_number": dead_seat,
            "content": content,
            "is_spectator": state.is_spectator_after_death
        }

    # =========================================================================
    # B34: 游戏启动流程
    # =========================================================================
    
    async def start_game(
        self,
        room_code: str,
        human_player_id: str,
        human_role: str | None = None
    ) -> WerewolfGameState:
        """Start a new werewolf game.
        
        注意：此方法只初始化游戏状态，不执行游戏流程。
        游戏流程需要通过 run_game() 方法启动，以便在 WebSocket 连接建立后执行。
        
        Args:
            room_code: Room code for the game
            human_player_id: The human player's ID
            human_role: Optional role for human player (for testing)
            
        Returns:
            Initialized game state
        """
        logger.info(f"Initializing werewolf game in room {room_code}")
        
        # 生成10个玩家名称
        player_names = [f"玩家{i}" for i in range(1, 11)]
        
        # 判断是否为观战模式（没有指定角色）
        is_spectator = human_role is None
        
        # Check for existing game and stop it
        if room_code in self._game_states:
            old_state = self._game_states[room_code]
            old_state.is_stopped = True
            logger.info(f"Stopping existing game in room {room_code} before starting new one")
            # Give the old loop a chance to see the flag and exit
            await asyncio.sleep(0.5)

        # Initialize game state with human player support
        game_state = self.engine.initialize_game_with_human_player(
            room_code=room_code,
            player_names=player_names,
            human_player_id=human_player_id,
            human_role=human_role
        )
        
        # Store state
        self._game_states[room_code] = game_state
        
        # Create AI agents for all non-human players
        await self._create_ai_agents(game_state, human_player_id)
        
        logger.info(f"Game state initialized for room {room_code}, waiting for run_game()")
        
        return game_state
    
    async def run_game(self, room_code: str):
        """运行游戏流程（在 WebSocket 连接建立后调用）。
        
        此方法执行：
        - 广播角色分配信息（观战模式）
        - 广播游戏开始公告
        - 启动第一个夜晚阶段
        
        Args:
            room_code: 房间代码
        """
        print(f"[DEBUG] run_game called for room {room_code}")
        
        game_state = self._game_states.get(room_code)
        if not game_state:
            print(f"[DEBUG] run_game: state not found for {room_code}")
            logger.error(f"Cannot run game: state not found for {room_code}")
            return
        
        if game_state.is_started:
            print(f"[DEBUG] run_game: game already started for {room_code}")
            logger.warning(f"Game already started for {room_code}")
            return
        
        game_state.is_started = True
        game_id = game_state.game_id
        print(f"[DEBUG] run_game: starting game for {room_code} (ID: {game_id})")
        logger.info(f"Running game for room {room_code} (ID: {game_id})")
        
        # Initialize day_number and phase
        self.engine.start_game()
        
        # 广播角色分配信息（观战模式下可见所有角色）
        if game_state.is_spectator_mode:
            players_info = [
                {
                    "seat_number": p.seat_number,
                    "player_name": p.player_name,
                    "role": p.role,
                    "team": p.team,
                }
                for p in game_state.players.values()
            ]
            await broadcast_role_assignment(room_code, players_info)
        
        # Broadcast game start announcement
        print(f"[DEBUG] run_game: calling _announce_game_start")
        await self._announce_game_start(room_code, game_state)
        
        # Start the first night
        print(f"[DEBUG] run_game: calling _start_night_phase")
        await self._start_night_phase(room_code, game_id)
    
    async def _create_ai_agents(
        self,
        game_state: WerewolfGameState,
        human_player_id: str
    ):
        """Create AI agents for non-human players."""
        for player in game_state.players.values():
            if player.player_id == human_player_id:
                continue
            
            # Create agent based on role
            agent = self._create_agent_for_role(
                role=player.role,
                seat_number=player.seat_number,
                player_name=f"玩家{player.seat_number}",
                player_id=player.player_id
            )
            
            if agent:
                self._ai_agents[player.seat_number] = agent
                
                # Set teammates for werewolves
                if player.role == "werewolf":
                    teammates = [
                        {"seat_number": p.seat_number, "name": f"玩家{p.seat_number}"}
                        for p in game_state.players.values()
                        if p.role == "werewolf" and p.seat_number != player.seat_number
                    ]
                    agent.set_teammates(teammates)
        
        logger.info(f"Created {len(self._ai_agents)} AI agents")
    
    def _create_agent_for_role(
        self,
        role: str,
        seat_number: int,
        player_name: str,
        player_id: str
    ):
        """Create an AI agent for a specific role."""
        if role == "werewolf":
            return WerewolfAgent(
                player_id=player_id,
                player_name=player_name,
                seat_number=seat_number
            )
        elif role == "seer":
            return SeerAgent(
                player_id=player_id,
                player_name=player_name,
                seat_number=seat_number
            )
        elif role == "witch":
            return WitchAgent(
                player_id=player_id,
                player_name=player_name,
                seat_number=seat_number
            )
        elif role == "hunter":
            return HunterAgent(
                player_id=player_id,
                player_name=player_name,
                seat_number=seat_number
            )
        elif role == "villager":
            return VillagerAgent(
                player_id=player_id,
                player_name=player_name,
                seat_number=seat_number
            )
        return None

    @staticmethod
    def _normalize_seat_number(value: Any) -> int | None:
        """Normalize different seat representations returned by LLMs/UI into ints."""
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, dict):
            for key in ("seat_number", "seat", "target"):
                if key in value:
                    normalized = WerewolfGameService._normalize_seat_number(value[key])
                    if normalized is not None:
                        return normalized
        if isinstance(value, str):
            digits = re.search(r"\d+", value)
            if digits:
                return int(digits.group())
        return None

    @staticmethod
    def _format_speech_entries(speeches: list[dict], limit: int = 10) -> list[dict]:
        """Return a copy of the most recent speech entries for prompts."""
        if not speeches:
            return []
        return list(speeches[-limit:])

    @staticmethod
    def _speeches_to_text(speeches: list[dict]) -> str:
        """Render speech history into text for vote prompts with day grouping."""
        if not speeches:
            return "暂无发言记录"
        
        # Group speeches by day
        speeches_by_day: dict[int, list[dict]] = {}
        for speech in speeches:
            day = speech.get("day", 1)
            if day not in speeches_by_day:
                speeches_by_day[day] = []
            speeches_by_day[day].append(speech)
        
        lines: list[str] = []
        for day in sorted(speeches_by_day.keys()):
            day_speeches = speeches_by_day[day]
            lines.append(f"\n=== 第{day}天发言 ===")
            for speech in day_speeches:
                seat = speech.get("seat_number", "?")
                name = speech.get("player_name", f"玩家{seat}")
                content = speech.get("content", "")
                speech_type = speech.get("type", "speech")
                
                type_marker = ""
                if speech_type == "last_words":
                    type_marker = "[遗言] "
                elif speech_type == "vote_speech":
                    type_marker = "[投票发言] "
                
                lines.append(f"{seat}号 {name}{type_marker}: {content}")
        
        return "\n".join(lines)

    @staticmethod
    def _record_speech_entry(
        game_state: WerewolfGameState,
        seat_number: int,
        player_name: str,
        content: str,
        speech_type: str = "speech",
    ) -> None:
        """Append a structured speech entry to the game state's speech history.
        
        Args:
            game_state: Current game state
            seat_number: Speaker's seat number
            player_name: Speaker's name
            content: Speech content
            speech_type: Type of speech ('speech', 'last_words', 'vote_speech')
        """
        if not content:
            return
        entry = {
            "day": game_state.day_number,
            "seat_number": seat_number,
            "player_name": player_name,
            "content": content.strip(),
            "type": speech_type,
        }
        game_state.speech_history.append(entry)
    
    async def _announce_game_start(
        self,
        room_code: str,
        game_state: WerewolfGameState
    ):
        """Announce game start with role assignment."""
        # 角色配置描述
        role_config = "3狼人 + 1预言家 + 1女巫 + 1猎人 + 4村民"
        
        # Stream host announcement
        announcement_stream = self.host.announce_game_start(
            player_count=len(game_state.players),
            role_config=role_config,
            stream=True
        )
        
        await stream_host_announcement(
            room_code=room_code,
            announcement_type="game_start",
            content_stream=announcement_stream,
            metadata={
                "player_count": len(game_state.players),
                "werewolf_count": 3
            }
        )
        
        # Send initial game state
        alive_players = [
            {
                "seat_number": p.seat_number,
                "display_name": p.player_name
            }
            for p in game_state.players.values()
            if p.is_alive
        ]
        await broadcast_game_state_update(
            room_code=room_code,
            phase=game_state.phase.value,
            day_number=game_state.day_number,
            alive_players=alive_players,
            dead_players=[],
            current_speaker=None
        )
        
        # Also broadcast phase change
        await broadcast_phase_change(
            room_code=room_code,
            from_phase="waiting",
            to_phase=game_state.phase.value,
            day_number=game_state.day_number
        )
    
    # =========================================================================
    # B35: 夜晚执行流程
    # =========================================================================
    
    async def _start_night_phase(self, room_code: str, game_id: str):
        """Start the night phase."""
        # 检查是否暂停或停止
        if not await self._check_paused_or_stopped(room_code, game_id):
            return
        
        game_state = self._validate_game_state(room_code, game_id)
        if not game_state:
            return
        
        # 计算存活玩家数
        alive_count = sum(1 for p in game_state.players.values() if p.is_alive)
        
        # Announce night start
        announcement_stream = self.host.announce_night(
            day_number=game_state.day_number,
            alive_count=alive_count,
            stream=True
        )
        await stream_host_announcement(
            room_code=room_code,
            announcement_type="night_start",
            content_stream=announcement_stream,
            metadata={"day_number": game_state.day_number}
        )
        
        # Update phase
        old_phase = game_state.phase
        game_state.phase = WerewolfPhase.NIGHT_WEREWOLF
        await broadcast_phase_change(
            room_code=room_code,
            from_phase=old_phase.value,
            to_phase=game_state.phase.value,
            day_number=game_state.day_number
        )
        
        # Start werewolf action
        await self._execute_werewolf_action(room_code, game_id)
    
    async def _execute_werewolf_action(self, room_code: str, game_id: str):
        """Execute werewolf kill action (AI only, human waits)."""
        # 检查是否暂停或停止
        if not await self._check_paused_or_stopped(room_code, game_id):
            return
        
        game_state = self._validate_game_state(room_code, game_id)
        if not game_state:
            return
        
        # 公告狼人睁眼
        werewolf_wake_stream = self.host.announce_werewolf_wake(stream=True)
        await stream_host_announcement(
            room_code=room_code,
            announcement_type="werewolf_wake",
            content_stream=werewolf_wake_stream,
            metadata={"phase": "night_werewolf"}
        )
        
        # 短暂延迟，让用户看到阶段变化
        await asyncio.sleep(1.5)
        
        # Get alive werewolves and targets
        werewolves = [
            p for p in game_state.players.values()
            if p.role == "werewolf" and p.is_alive
        ]
        targets = [
            {"seat_number": p.seat_number, "display_name": f"玩家{p.seat_number}"}
            for p in game_state.players.values()
            if p.is_alive
        ]
        
        # Check if human is werewolf
        human_werewolf = None
        ai_werewolves = []
        for wolf in werewolves:
            if wolf.seat_number in self._ai_agents:
                ai_werewolves.append(wolf)
            else:
                human_werewolf = wolf
        
        if human_werewolf:
            # T31: 人类狼人夜间行动 - 等待玩家选择击杀目标
            timeout_seconds = 60  # 60秒超时
            self._set_waiting_for_human(room_code, "werewolf_kill", timeout_seconds)
            
            # 生成击杀目标选项（排除自己和其他狼人）
            kill_options = [
                {
                    "seat_number": p.seat_number,
                    "display_name": f"玩家{p.seat_number}",
                    "player_name": p.player_name
                }
                for p in game_state.players.values()
                if p.is_alive and p.role != "werewolf"
            ]
            # 添加空刀选项
            kill_options.append({
                "seat_number": None,
                "display_name": "空刀（不击杀任何人）",
                "player_name": None
            })
            
            # 广播等待人类狼人行动
            await broadcast_waiting_for_human(
                room_code=room_code,
                action_type="werewolf_kill",
                seat_number=human_werewolf.seat_number,
                timeout_seconds=timeout_seconds,
                metadata={
                    "role": "werewolf",
                    "night_number": game_state.day_number,
                    "options": kill_options
                }
            )
            
            # 通知人类狼人该行动了
            await notify_werewolf_turn(
                room_code=room_code,
                werewolf_player_ids=[human_werewolf.player_id],
                alive_targets=targets
            )
            
            # 等待人类玩家输入或超时
            while game_state.waiting_for_human_action:
                if await self._check_human_timeout(room_code, game_id):
                    break
                
                # 检查是否暂停或停止
                if not await self._check_paused_or_stopped(room_code, game_id):
                    return
                
                # 短暂休眠，避免忙等待
                await asyncio.sleep(0.1)
            
            # 狼人闭眼公告
            werewolf_sleep_stream = self.host.announce_werewolf_sleep(stream=True)
            await stream_host_announcement(
                room_code=room_code,
                announcement_type="werewolf_sleep",
                content_stream=werewolf_sleep_stream,
                metadata={"phase": "night_werewolf_end"}
            )
            await asyncio.sleep(1.0)
            
            # 进入预言家阶段
            await self._execute_seer_action(room_code, game_id)
            return
        
        # All werewolves are AI - let them discuss and decide together
        if ai_werewolves:
            # Build game_state dict for agent
            alive_players = [
                {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                for p in game_state.players.values() if p.is_alive
            ]
            dead_players = [
                {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                for p in game_state.players.values() if not p.is_alive
            ]
            
            # 获取发言历史用于分析（非首夜时）
            speech_history_text = ""
            if game_state.day_number > 1 and game_state.speech_history:
                speech_history_text = self._speeches_to_text(game_state.speech_history)
            
            agent_game_state = {
                "day_number": game_state.day_number,
                "alive_players": alive_players,
                "dead_players": dead_players,
                "speech_history": speech_history_text,  # 添加发言历史
            }
            # Build available targets (exclude werewolf teammates)
            available_targets = [
                {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                for p in game_state.players.values()
                if p.is_alive and p.role != "werewolf"
            ]
            
            # Phase 1: 每个狼人发表意见
            discussion_history = []
            for wolf in ai_werewolves:
                wolf_agent = self._ai_agents.get(wolf.seat_number)
                if wolf_agent and hasattr(wolf_agent, 'discuss_night_target'):
                    try:
                        discussion_result = await wolf_agent.discuss_night_target(
                            game_state=agent_game_state,
                            available_targets=available_targets,
                            previous_opinions=discussion_history
                        )
                        
                        suggested_target = discussion_result.get("suggested_target")
                        opinion = discussion_result.get("opinion", "")
                        
                        # 记录讨论历史（使用 discuss_night_target 返回的格式）
                        discussion_entry = {
                            "seat_number": wolf.seat_number,
                            "name": wolf.player_name,
                            "suggested_target": suggested_target,
                            "opinion": opinion
                        }
                        discussion_history.append(discussion_entry)
                        
                        logger.info(f"[AI Discussion] Werewolf {wolf.seat_number} suggests target {suggested_target}: {opinion[:50] if opinion else ''}...")
                        
                        # 广播狼人讨论（用于详细日志模式）
                        await broadcast_ai_action(
                            room_code=room_code,
                            ai_player_id=wolf.player_id,
                            action={
                                "action_type": "werewolf_discussion",
                                "seat_number": wolf.seat_number,
                                "role": "werewolf",
                                "player_name": wolf.player_name,
                                "suggested_target": suggested_target,
                                "opinion": opinion,
                            }
                        )
                        
                        # 短暂延迟，让用户看到讨论过程
                        await asyncio.sleep(1.0)
                        
                    except Exception as e:
                        logger.error(f"Error in werewolf discussion for seat {wolf.seat_number}: {e}")
            
            # Phase 2: 由一个狼人做最终决定
            decision_wolf = ai_werewolves[0]  # 使用第一个狼人做最终决定
            decision_agent = self._ai_agents.get(decision_wolf.seat_number)
            
            if decision_agent:
                try:
                    # 检查是否有 make_final_kill_decision 方法
                    if hasattr(decision_agent, 'make_final_kill_decision'):
                        result = await decision_agent.make_final_kill_decision(
                            game_state=agent_game_state,
                            available_targets=available_targets,
                            teammate_opinions=discussion_history
                        )
                    else:
                        # 回退到原有方法
                        result = await decision_agent.decide_night_action(
                            game_state=agent_game_state,
                            available_targets=available_targets
                        )
                    
                    raw_target = result.get("target") if isinstance(result, dict) else result
                    target_seat = self._normalize_seat_number(raw_target)
                    reasoning = result.get("reasoning", "") if isinstance(result, dict) else ""
                    
                    logger.info(f"[AI Final Decision] Werewolf {decision_wolf.seat_number} final target: {target_seat}, reasoning: {reasoning[:50]}...")
                    
                    # 广播最终决定（用于详细日志模式）
                    await broadcast_ai_action(
                        room_code=room_code,
                        ai_player_id=decision_wolf.player_id,
                        action={
                            "action_type": "werewolf_final_decision",
                            "seat_number": decision_wolf.seat_number,
                            "role": "werewolf",
                            "player_name": decision_wolf.player_name,
                            "target": target_seat,
                            "reasoning": reasoning,
                            "discussion_summary": [
                                {"seat": d["seat_number"], "target": d["suggested_target"]} 
                                for d in discussion_history
                            ]
                        }
                    )
                    
                    # Process the kill
                    self.engine.process_werewolf_action(game_state, target_seat)
                    if target_seat:
                        game_state.game_logs.append(f"夜晚：狼人选择击杀{target_seat}号玩家")
                    else:
                        game_state.game_logs.append("夜晚：狼人选择空刀")
                        
                except Exception as e:
                    logger.error(f"Error in werewolf final decision: {e}")
                    # 回退处理：使用简单的投票
                    if discussion_history:
                        targets_count = {}
                        for d in discussion_history:
                            t = d.get("suggested_target")
                            if t:
                                targets_count[t] = targets_count.get(t, 0) + 1
                        if targets_count:
                            target_seat = max(targets_count, key=targets_count.get)
                            self.engine.process_werewolf_action(game_state, target_seat)
                            game_state.game_logs.append(f"夜晚：狼人选择击杀{target_seat}号玩家")
        
        # 公告狼人闭眼
        werewolf_sleep_stream = self.host.announce_werewolf_sleep(stream=True)
        await stream_host_announcement(
            room_code=room_code,
            announcement_type="werewolf_sleep",
            content_stream=werewolf_sleep_stream,
            metadata={"phase": "night_werewolf_end"}
        )
        
        # 短暂延迟
        await asyncio.sleep(1.0)
        
        # Move to seer phase
        await self._execute_seer_action(room_code, game_id)
    
    async def _execute_seer_action(self, room_code: str, game_id: str):
        """Execute seer check action."""
        # 检查是否暂停或停止
        if not await self._check_paused_or_stopped(room_code, game_id):
            return
        
        game_state = self._validate_game_state(room_code, game_id)
        if not game_state:
            return
        
        old_phase = game_state.phase
        game_state.phase = WerewolfPhase.NIGHT_SEER
        
        # Broadcast phase change
        await broadcast_phase_change(
            room_code=room_code,
            from_phase=old_phase.value,
            to_phase=game_state.phase.value,
            day_number=game_state.day_number
        )
        
        # Find alive seer
        seer = next(
            (p for p in game_state.players.values() if p.role == "seer" and p.is_alive),
            None
        )
        
        if not seer:
            # Seer is dead, skip to witch
            await self._execute_witch_action(room_code, game_id)
            return
        
        # 公告预言家睁眼
        seer_wake_stream = self.host.announce_seer_wake(stream=True)
        await stream_host_announcement(
            room_code=room_code,
            announcement_type="seer_wake",
            content_stream=seer_wake_stream,
            metadata={"phase": "night_seer"}
        )
        
        # 短暂延迟
        await asyncio.sleep(1.5)
        
        targets = [
            {"seat_number": p.seat_number, "display_name": f"玩家{p.seat_number}"}
            for p in game_state.players.values()
            if p.is_alive and p.seat_number != seer.seat_number
        ]
        
        if seer.seat_number in self._ai_agents:
            # AI seer
            seer_agent = self._ai_agents[seer.seat_number]
            # Build game_state dict for agent
            alive_players = [
                {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                for p in game_state.players.values() if p.is_alive
            ]
            dead_players = [
                {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                for p in game_state.players.values() if not p.is_alive
            ]
            
            # 获取发言历史用于分析（非首夜时）
            speech_history_text = ""
            if game_state.day_number > 1 and game_state.speech_history:
                speech_history_text = self._speeches_to_text(game_state.speech_history)
            
            agent_game_state = {
                "day_number": game_state.day_number,
                "alive_players": alive_players,
                "dead_players": dead_players,
                "speech_history": speech_history_text,  # 添加发言历史
            }
            # Build available targets (exclude self)
            available_targets = [
                {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                for p in game_state.players.values()
                if p.is_alive and p.seat_number != seer.seat_number
            ]
            
            result = await seer_agent.decide_night_action(
                game_state=agent_game_state,
                available_targets=available_targets
            )
            raw_target = result.get("target") if isinstance(result, dict) else result
            target_seat = self._normalize_seat_number(raw_target)
            reasoning = result.get("reasoning", "") if isinstance(result, dict) else ""
            
            if target_seat:
                is_werewolf = self.engine.process_seer_action(game_state, target_seat)
                # 从 players 字典中获取目标玩家信息（key 是座位号，value 是 PlayerState）
                target_player = game_state.players.get(target_seat)
                target_name = target_player.player_name if target_player else f"玩家{target_seat}"
                seer_agent.add_check_result(target_seat, target_name, is_werewolf, game_state.day_number)
                game_state.game_logs.append(f"夜晚：预言家查验了{target_seat}号玩家，结果是{'狼人' if is_werewolf else '好人'}")
                
                # 广播 AI 行动详情（用于详细日志模式）
                await broadcast_ai_action(
                    room_code=room_code,
                    ai_player_id=seer.player_id,
                    action={
                        "action_type": "seer_check",
                        "seat_number": seer.seat_number,
                        "role": "seer",
                        "player_name": seer.player_name,
                        "target": target_seat,
                        "target_name": target_name,
                        "reasoning": reasoning,
                        "result": "狼人" if is_werewolf else "好人",
                    }
                )
            
            # 公告预言家闭眼
            seer_sleep_stream = self.host.announce_seer_sleep(stream=True)
            await stream_host_announcement(
                room_code=room_code,
                announcement_type="seer_sleep",
                content_stream=seer_sleep_stream,
                metadata={"phase": "night_seer_end"}
            )
            
            # 短暂延迟
            await asyncio.sleep(1.0)
            
            # Move to witch
            await self._execute_witch_action(room_code, game_id)
        else:
            # T32: 人类预言家夜间行动 - 等待玩家选择查验目标
            timeout_seconds = 60  # 60秒超时
            self._set_waiting_for_human(room_code, "seer_check", timeout_seconds)
            
            # 生成查验目标选项
            check_options = [
                {
                    "seat_number": p.seat_number,
                    "display_name": f"玩家{p.seat_number}",
                    "player_name": p.player_name
                }
                for p in game_state.players.values()
                if p.is_alive and p.seat_number != seer.seat_number
            ]
            
            # 广播等待人类预言家行动
            await broadcast_waiting_for_human(
                room_code=room_code,
                action_type="seer_check",
                seat_number=seer.seat_number,
                timeout_seconds=timeout_seconds,
                metadata={
                    "role": "seer",
                    "night_number": game_state.day_number,
                    "options": check_options
                }
            )
            
            # 通知人类预言家该行动了
            await notify_seer_turn(
                room_code=room_code,
                seer_player_id=seer.player_id,
                alive_targets=targets
            )
            
            # 等待人类玩家输入或超时
            while game_state.waiting_for_human_action:
                if await self._check_human_timeout(room_code, game_id):
                    break
                
                # 检查是否暂停或停止
                if not await self._check_paused_or_stopped(room_code, game_id):
                    return
                
                # 短暂休眠，避免忙等待
                await asyncio.sleep(0.1)
            
            # 预言家闭眼公告
            seer_sleep_stream = self.host.announce_seer_sleep(stream=True)
            await stream_host_announcement(
                room_code=room_code,
                announcement_type="seer_sleep",
                content_stream=seer_sleep_stream,
                metadata={"phase": "night_seer_end"}
            )
            await asyncio.sleep(1.0)
            
            # 进入女巫阶段
            await self._execute_witch_action(room_code, game_id)
    
    async def _execute_witch_action(self, room_code: str, game_id: str):
        """Execute witch save/poison action."""
        # 检查是否暂停或停止
        if not await self._check_paused_or_stopped(room_code, game_id):
            return
        
        game_state = self._validate_game_state(room_code, game_id)
        if not game_state:
            return
        
        old_phase = game_state.phase
        game_state.phase = WerewolfPhase.NIGHT_WITCH
        
        # Broadcast phase change
        await broadcast_phase_change(
            room_code=room_code,
            from_phase=old_phase.value,
            to_phase=game_state.phase.value,
            day_number=game_state.day_number
        )
        
        # Find alive witch
        witch = next(
            (p for p in game_state.players.values() if p.role == "witch" and p.is_alive),
            None
        )
        
        if not witch:
            # Witch is dead, process night and go to day
            await self._end_night_phase(room_code, game_id)
            return
        
        # Get killed player info
        killed_seat = game_state.current_night_actions.werewolf_kill_target
        killed_player_desc = None
        if killed_seat:
            killed_p = game_state.players.get(killed_seat)
            if killed_p:
                killed_player_desc = f"{killed_seat}号玩家"
        
        # 公告女巫睁眼
        witch_wake_stream = self.host.announce_witch_wake(
            killed_player=killed_player_desc,
            stream=True
        )
        await stream_host_announcement(
            room_code=room_code,
            announcement_type="witch_wake",
            content_stream=witch_wake_stream,
            metadata={"phase": "night_witch", "killed_seat": killed_seat}
        )
        
        # 短暂延迟
        await asyncio.sleep(1.5)
        
        # Get killed player info for notification
        killed_player = None
        if killed_seat:
            killed_p = game_state.players.get(killed_seat)
            if killed_p:
                killed_player = {
                    "seat_number": killed_seat,
                    "display_name": f"玩家{killed_seat}"
                }
        
        # Check witch potions
        has_antidote = game_state.witch_has_antidote
        has_poison = game_state.witch_has_poison
        can_self_save = game_state.day_number == 1  # First night (day 1) can self-save
        
        targets = [
            {"seat_number": p.seat_number, "display_name": f"玩家{p.seat_number}"}
            for p in game_state.players.values()
            if p.is_alive and p.seat_number != witch.seat_number
        ]
        
        if witch.seat_number in self._ai_agents:
            # AI witch
            witch_agent = self._ai_agents[witch.seat_number]
            # Build game_state dict for agent
            alive_players = [
                {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                for p in game_state.players.values() if p.is_alive
            ]
            dead_players = [
                {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                for p in game_state.players.values() if not p.is_alive
            ]
            agent_game_state = {
                "day_number": game_state.day_number,
                "alive_players": alive_players,
                "dead_players": dead_players,
            }
            # Build available targets (exclude self)
            available_targets = [
                {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                for p in game_state.players.values()
                if p.is_alive and p.seat_number != witch.seat_number
            ]
            # Build killed_player info
            killed_player_info = None
            if killed_seat:
                killed_p = game_state.players.get(killed_seat)
                if killed_p:
                    killed_player_info = {
                        "seat_number": killed_p.seat_number,
                        "name": killed_p.player_name,
                        "player_id": killed_p.player_id
                    }
            
            result = await witch_agent.decide_night_action(
                game_state=agent_game_state,
                available_targets=available_targets,
                killed_player=killed_player_info
            )
            # Parse witch decision: format is {"action": "save"|"poison"|"pass", "target": seat_number}
            save_target = None
            poison_target = None
            reasoning = ""
            if isinstance(result, dict):
                action = result.get("action", "pass")
                raw_target = result.get("target")
                reasoning = result.get("reasoning", "")
                if action == "save":
                    save_target = self._normalize_seat_number(raw_target)
                elif action == "poison":
                    poison_target = self._normalize_seat_number(raw_target)
            
            self.engine.process_witch_action(
                game_state,
                save_target=save_target,
                poison_target=poison_target
            )
            
            # Update witch agent potion status
            if save_target:
                witch_agent.use_antidote()
                game_state.game_logs.append(f"夜晚：女巫救了{save_target}号玩家")
                # 广播 AI 行动详情（用于详细日志模式）
                await broadcast_ai_action(
                    room_code=room_code,
                    ai_player_id=witch.player_id,
                    action={
                        "action_type": "witch_save",
                        "seat_number": witch.seat_number,
                        "role": "witch",
                        "player_name": witch.player_name,
                        "target": save_target,
                        "reasoning": reasoning,
                    }
                )
            if poison_target:
                witch_agent.use_poison()
                game_state.game_logs.append(f"夜晚：女巫毒了{poison_target}号玩家")
                # 广播 AI 行动详情（用于详细日志模式）
                await broadcast_ai_action(
                    room_code=room_code,
                    ai_player_id=witch.player_id,
                    action={
                        "action_type": "witch_poison",
                        "seat_number": witch.seat_number,
                        "role": "witch",
                        "player_name": witch.player_name,
                        "target": poison_target,
                        "reasoning": reasoning,
                    }
                )
            if not save_target and not poison_target:
                # 广播女巫选择不行动
                await broadcast_ai_action(
                    room_code=room_code,
                    ai_player_id=witch.player_id,
                    action={
                        "action_type": "witch_pass",
                        "seat_number": witch.seat_number,
                        "role": "witch",
                        "player_name": witch.player_name,
                        "target": None,
                        "reasoning": reasoning,
                    }
                )
            
            # 公告女巫闭眼
            witch_sleep_stream = self.host.announce_witch_sleep(stream=True)
            await stream_host_announcement(
                room_code=room_code,
                announcement_type="witch_sleep",
                content_stream=witch_sleep_stream,
                metadata={"phase": "night_witch_end"}
            )
            
            # 短暂延迟
            await asyncio.sleep(1.0)
            
            # End night
            await self._end_night_phase(room_code, game_id)
        else:
            # T33: 人类女巫夜间行动 - 等待玩家选择救人/毒人
            timeout_seconds = 60  # 60秒超时
            self._set_waiting_for_human(room_code, "witch_action", timeout_seconds)
            
            # 生成女巫行动选项
            witch_options = []
            
            # 救人选项（如果有解药且有人被杀）
            if has_antidote and killed_seat:
                killed_p = game_state.players.get(killed_seat)
                # 检查是否能自救（首夜可以自救，后续不能）
                if killed_seat != witch.seat_number or can_self_save:
                    witch_options.append({
                        "action": "save",
                        "target_seat": killed_seat,
                        "display_name": f"使用解药救{killed_seat}号玩家" + (f"({killed_p.player_name})" if killed_p else ""),
                        "description": "使用解药救活今晚被狼人杀死的玩家"
                    })
            
            # 毒人选项（如果有毒药）
            if has_poison:
                for p in game_state.players.values():
                    if p.is_alive and p.seat_number != witch.seat_number:
                        witch_options.append({
                            "action": "poison",
                            "target_seat": p.seat_number,
                            "display_name": f"毒杀{p.seat_number}号玩家({p.player_name})",
                            "description": "使用毒药毒杀该玩家"
                        })
            
            # 不行动选项
            witch_options.append({
                "action": "pass",
                "target_seat": None,
                "display_name": "不使用任何药水",
                "description": "本夜不使用解药和毒药"
            })
            
            # 广播等待人类女巫行动
            await broadcast_waiting_for_human(
                room_code=room_code,
                action_type="witch_action",
                seat_number=witch.seat_number,
                timeout_seconds=timeout_seconds,
                metadata={
                    "role": "witch",
                    "night_number": game_state.day_number,
                    "has_antidote": has_antidote,
                    "has_poison": has_poison,
                    "killed_seat": killed_seat,
                    "can_self_save": can_self_save,
                    "options": witch_options
                }
            )
            
            # 通知人类女巫该行动了
            await notify_witch_turn(
                room_code=room_code,
                witch_player_id=witch.player_id,
                killed_player=killed_player,
                has_antidote=has_antidote,
                has_poison=has_poison,
                can_self_save=can_self_save,
                alive_targets=targets
            )
            
            # 等待人类玩家输入或超时
            while game_state.waiting_for_human_action:
                if await self._check_human_timeout(room_code, game_id):
                    break
                
                # 检查是否暂停或停止
                if not await self._check_paused_or_stopped(room_code, game_id):
                    return
                
                # 短暂休眠，避免忙等待
                await asyncio.sleep(0.1)
            
            # 女巫闭眼公告
            witch_sleep_stream = self.host.announce_witch_sleep(stream=True)
            await stream_host_announcement(
                room_code=room_code,
                announcement_type="witch_sleep",
                content_stream=witch_sleep_stream,
                metadata={"phase": "night_witch_end"}
            )
            await asyncio.sleep(1.0)
            
            # 结束夜晚
            await self._end_night_phase(room_code, game_id)
    
    async def _end_night_phase(self, room_code: str, game_id: str):
        """End night phase and transition to day."""
        # 检查是否暂停或停止
        if not await self._check_paused_or_stopped(room_code, game_id):
            return
        
        game_state = self._validate_game_state(room_code, game_id)
        if not game_state:
            return
        
        # Process night deaths
        deaths = self.engine.advance_to_day(game_state)
        
        # Broadcast phase change to DAY with updated day_number
        await broadcast_phase_change(
            room_code=room_code,
            from_phase="night",
            to_phase=game_state.phase.value,
            day_number=game_state.day_number
        )
        
        # Announce dawn
        dead_info = [
            {"seat_number": d, "name": f"玩家{d}"}
            for d in deaths
        ] if deaths else []
        death_reasons = ["killed"] * len(deaths) if deaths else []
        
        announcement_stream = self.host.announce_dawn(
            dead_players=dead_info,
            death_reasons=death_reasons,
            stream=True
        )
        await stream_host_announcement(
            room_code=room_code,
            announcement_type="dawn",
            content_stream=announcement_stream,
            metadata={"dead_players": dead_info}
        )
        
        # Check win condition
        winner = self.engine.check_winner(game_state)
        if winner:
            await self._end_game(room_code, winner)
            return
        
        # Handle last words for dead players (before hunter shoot check)
        for death_seat in deaths:
            player = game_state.players.get(death_seat)
            if player:
                # Let dead player speak last words
                await self._handle_last_words(room_code, death_seat, "night_kill", game_id)
                
                # Handle hunter shoot if applicable
                if player.role == "hunter":
                    await self._handle_hunter_shoot(room_code, death_seat, game_id)
                    # After hunter action, check win again
                    winner = self.engine.check_winner(game_state)
                    if winner:
                        await self._end_game(room_code, winner)
                        return
        
        # Start day discussion
        await self._start_day_discussion(room_code, game_id)
    
    # =========================================================================
    # B36: 白天执行流程
    # =========================================================================
    
    async def _start_day_discussion(self, room_code: str, game_id: str):
        """Start day discussion phase."""
        # 检查是否暂停或停止
        if not await self._check_paused_or_stopped(room_code, game_id):
            return
        
        game_state = self._validate_game_state(room_code, game_id)
        if not game_state:
            return
        
        old_phase = game_state.phase
        game_state.phase = WerewolfPhase.DAY_DISCUSSION
        
        # Broadcast phase change
        await broadcast_phase_change(
            room_code=room_code,
            from_phase=old_phase.value,
            to_phase=game_state.phase.value,
            day_number=game_state.day_number
        )
        
        # Announce discussion start
        await broadcast_host_announcement(
            room_code=room_code,
            announcement_type="discussion_start",
            content=f"第{game_state.day_number}天，请各位玩家依次发言，从1号开始。"
        )
        
        # Execute speeches in order
        await self._execute_speeches(room_code, game_id)
    
    async def _execute_speeches(self, room_code: str, game_id: str):
        """Execute all player speeches in seat order."""
        game_state = self._validate_game_state(room_code, game_id)
        if not game_state:
            return
        
        # Get alive players in seat order
        alive_players = sorted(
            [p for p in game_state.players.values() if p.is_alive],
            key=lambda p: p.seat_number
        )
        
        for idx, player in enumerate(alive_players):
            # 在每个玩家发言前检查是否暂停或停止
            if not await self._check_paused_or_stopped(room_code, game_id):
                return
            
            player_name = f"玩家{player.seat_number}"
            is_human = player.seat_number not in self._ai_agents
            
            # 1. 主持人点名发言
            await broadcast_host_announcement(
                room_code=room_code,
                announcement_type="request_speech",
                content=f"请{player.seat_number}号玩家发言。",
                metadata={"seat_number": player.seat_number, "is_human": is_human}
            )
            
            # 设置当前发言者
            game_state.current_speaker_seat = player.seat_number
            
            # 等待0.5秒，让点名公告显示
            await asyncio.sleep(0.5)
            
            if player.seat_number in self._ai_agents:
                # AI speech with streaming
                agent = self._ai_agents[player.seat_number]
                
                # Build game_state dict for agent
                agent_alive_players = [
                    {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                    for p in game_state.players.values() if p.is_alive
                ]
                agent_dead_players = [
                    {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                    for p in game_state.players.values() if not p.is_alive
                ]
                agent_game_state = {
                    "day_number": game_state.day_number,
                    "alive_players": agent_alive_players,
                    "dead_players": agent_dead_players,
                }
                # Use structured speech history for context
                previous_speeches = self._format_speech_entries(
                    game_state.speech_history,
                    limit=12
                )
                
                speech_stream = agent.generate_speech_stream(
                    game_state=agent_game_state,
                    previous_speeches=previous_speeches
                )
                
                speech_content = await stream_ai_speech(
                    room_code=room_code,
                    speaker_seat=player.seat_number,
                    speaker_name=player_name,
                    speech_stream=speech_stream
                )
                
                game_state.game_logs.append(f"第{game_state.day_number}天 - {player.seat_number}号发言: {speech_content}")
                self._record_speech_entry(
                    game_state,
                    seat_number=player.seat_number,
                    player_name=player.player_name,
                    content=speech_content
                )
                
                # AI发言间隔：每个AI之间等待1秒
                await asyncio.sleep(1)
            else:
                # T15: 人类玩家发言 - 等待玩家输入
                # 1. 设置等待状态
                timeout_seconds = 120  # 2分钟超时
                self._set_waiting_for_human(room_code, "speech", timeout_seconds)
                
                # 2. 生成发言选项
                speech_options = self.generate_speech_options(room_code, player.seat_number)
                
                # 3. 广播等待人类玩家发言
                await broadcast_waiting_for_human(
                    room_code=room_code,
                    action_type="speech",
                    seat_number=player.seat_number,
                    timeout_seconds=timeout_seconds,
                    metadata={"day_number": game_state.day_number}
                )
                
                # 4. 发送发言选项
                await broadcast_speech_options(
                    room_code=room_code,
                    seat_number=player.seat_number,
                    options=speech_options
                )
                
                # 5. 等待人类玩家发言或超时
                # 轮询检查 waiting_for_human_action 状态
                while game_state.waiting_for_human_action:
                    if await self._check_human_timeout(room_code, game_id):
                        break
                    
                    # 检查是否暂停或停止
                    if not await self._check_paused_or_stopped(room_code, game_id):
                        return
                    
                    # 短暂休眠，避免忙等待
                    await asyncio.sleep(0.1)
                
                # 如果发言成功，广播发言完成
                # （发言内容已经在 process_human_speech 中记录）
            
            # 2. 清除当前发言者
            game_state.current_speaker_seat = None
            
            # 3. 发言结束公告（除了最后一个玩家）
            if idx < len(alive_players) - 1:
                await broadcast_host_announcement(
                    room_code=room_code,
                    announcement_type="speech_end_transition",
                    content=f"{player.seat_number}号玩家发言结束。",
                    metadata={"seat_number": player.seat_number}
                )
                # 等待1秒，让发言结束公告显示
                await asyncio.sleep(1)
        
        # 所有玩家发言完成后，等待0.5秒
        await asyncio.sleep(0.5)
        
        # Start voting
        await self._start_voting(room_code, game_id)
    
    async def _start_voting(self, room_code: str, game_id: str):
        """Start voting phase."""
        # 检查是否暂停或停止
        if not await self._check_paused_or_stopped(room_code, game_id):
            return
        
        game_state = self._validate_game_state(room_code, game_id)
        if not game_state:
            return
        
        old_phase = game_state.phase
        game_state.phase = WerewolfPhase.DAY_VOTE
        game_state.current_votes = {}  # Reset votes for this round
        
        # Broadcast phase change
        await broadcast_phase_change(
            room_code=room_code,
            from_phase=old_phase.value,
            to_phase=game_state.phase.value,
            day_number=game_state.day_number
        )
        
        # Announce voting
        await broadcast_host_announcement(
            room_code=room_code,
            announcement_type="vote_start",
            content="发言结束，请投票选出今天要放逐的玩家。"
        )
        
        # Execute votes
        await self._execute_votes(room_code, game_id)
    
    async def _execute_votes(self, room_code: str, game_id: str):
        """Execute all player votes."""
        game_state = self._validate_game_state(room_code, game_id)
        if not game_state:
            return
        
        alive_players = [p for p in game_state.players.values() if p.is_alive]
        alive_seats = [p.seat_number for p in alive_players]
        
        for player in alive_players:
            # 在每个玩家投票前检查是否暂停或停止
            if not await self._check_paused_or_stopped(room_code, game_id):
                return
            
            if player.seat_number in self._ai_agents:
                # AI vote
                agent = self._ai_agents[player.seat_number]
                
                # Build game_state dict for agent
                agent_alive_players = [
                    {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                    for p in game_state.players.values() if p.is_alive
                ]
                agent_dead_players = [
                    {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                    for p in game_state.players.values() if not p.is_alive
                ]
                agent_game_state = {
                    "day_number": game_state.day_number,
                    "alive_players": agent_alive_players,
                    "dead_players": agent_dead_players,
                }
                # Build speech summary from structured speech history
                recent_speeches = self._format_speech_entries(game_state.speech_history, limit=12)
                speech_summary = self._speeches_to_text(recent_speeches)
                # Build voteable players
                voteable_players = [
                    {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                    for p in game_state.players.values()
                    if p.is_alive and p.seat_number != player.seat_number
                ]
                
                result = await agent.decide_vote(
                    game_state=agent_game_state,
                    speech_summary=speech_summary,
                    voteable_players=voteable_players
                )
                raw_target = result.get("target") if isinstance(result, dict) else result
                vote_target = self._normalize_seat_number(raw_target)
                
                self.engine.process_vote(game_state, player.seat_number, vote_target)
                
                # Broadcast vote
                target_name = f"玩家{vote_target}" if vote_target else None
                await broadcast_vote_update(
                    room_code=room_code,
                    voter_seat=player.seat_number,
                    voter_name=f"玩家{player.seat_number}",
                    target_seat=vote_target,
                    target_name=target_name
                )
                
                game_state.game_logs.append(
                    f"投票: {player.seat_number}号投给{vote_target}号" if vote_target 
                    else f"投票: {player.seat_number}号弃票"
                )
                
                await asyncio.sleep(0.3)
            else:
                # T23-T25: 人类玩家投票 - 等待玩家输入
                # 1. 设置等待状态
                timeout_seconds = 60  # 1分钟超时
                self._set_waiting_for_human(room_code, "vote", timeout_seconds)
                
                # 2. 生成投票选项（排除自己）
                vote_options = self.generate_vote_options(room_code, player.seat_number)
                
                # 3. 广播等待人类玩家投票
                await broadcast_waiting_for_human(
                    room_code=room_code,
                    action_type="vote",
                    seat_number=player.seat_number,
                    timeout_seconds=timeout_seconds,
                    metadata={"day_number": game_state.day_number}
                )
                
                # 4. 发送投票选项
                await broadcast_vote_options(
                    room_code=room_code,
                    seat_number=player.seat_number,
                    options=vote_options,
                    timeout_seconds=timeout_seconds
                )
                
                # 5. 等待人类玩家投票或超时
                while game_state.waiting_for_human_action:
                    if await self._check_human_timeout(room_code, game_id):
                        break
                    
                    # 检查是否暂停或停止
                    if not await self._check_paused_or_stopped(room_code, game_id):
                        return
                    
                    # 短暂休眠，避免忙等待
                    await asyncio.sleep(0.1)
        
        # Process vote result
        await self._process_vote_result(room_code, game_id)
    
    async def _process_vote_result(self, room_code: str, game_id: str):
        """Process voting result and eliminate player if applicable."""
        game_state = self._validate_game_state(room_code, game_id)
        if not game_state:
            return
        
        eliminated, is_tie, vote_counts = self.engine.process_vote_result(game_state)
        
        # Broadcast result
        eliminated_name = f"玩家{eliminated}" if eliminated else None
        await broadcast_vote_result(
            room_code=room_code,
            vote_counts=vote_counts,
            eliminated_seat=eliminated,
            eliminated_name=eliminated_name,
            is_tie=is_tie
        )
        
        if eliminated:
            game_state.game_logs.append(f"投票结果: {eliminated}号玩家被放逐")

            # Check win condition immediately after elimination
            winner = self.engine.check_winner(game_state)
            if winner:
                # Game ends, no need for last words
                await self._end_game(room_code, winner)
                return

            # Handle last words for eliminated player
            player = game_state.players.get(eliminated)
            if player:
                await self._handle_last_words(room_code, eliminated, "vote", game_id)

                # Check for hunter
                if player.role == "hunter":
                    await self._handle_hunter_shoot(room_code, eliminated, game_id)
                    # After hunter action, check win again
                    winner = self.engine.check_winner(game_state)
                    if winner:
                        await self._end_game(room_code, winner)
                        return
        else:
            game_state.game_logs.append("投票结果: 平票，无人出局")

        # Check win condition again (in case no elimination or after last words)
        winner = self.engine.check_winner(game_state)
        if winner:
            await self._end_game(room_code, winner)
            return
        
        # Start next night (day_number is already incremented in advance_to_day)
        await self._start_night_phase(room_code, game_id)
    
    # =========================================================================
    # B37: 用户行动处理
    # =========================================================================
    
    async def process_human_action(
        self,
        room_code: str,
        player_id: str,
        action_type: str,
        target_seat: int | None
    ):
        """Process action from human player.
        
        Args:
            room_code: Room code
            player_id: Human player ID
            action_type: Type of action (kill, check, save, poison, shoot, vote)
            target_seat: Target seat number (None for skip/abstain)
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            raise NotFoundError(f"Game not found for room {room_code}")
        
        # Find human player
        human_player = next(
            (p for p in game_state.players.values() if p.player_id == player_id),
            None
        )
        if not human_player:
            raise BadRequestError("Player not in game")
        
        normalized_target = self._normalize_seat_number(target_seat)
        
        if action_type == "kill":
            await self._handle_human_kill(room_code, human_player, normalized_target)
        elif action_type == "check":
            await self._handle_human_check(room_code, human_player, normalized_target)
        elif action_type == "save":
            await self._handle_human_save(room_code, human_player, normalized_target)
        elif action_type == "poison":
            await self._handle_human_poison(room_code, human_player, normalized_target)
        elif action_type == "shoot":
            await self._handle_human_shoot(room_code, human_player, normalized_target)
        elif action_type == "vote":
            await self._handle_human_vote(room_code, human_player, normalized_target)
        else:
            raise BadRequestError(f"Unknown action type: {action_type}")
    
    async def _handle_human_kill(
        self,
        room_code: str,
        player: PlayerState,
        target_seat: int | None
    ):
        """Handle human werewolf kill action."""
        game_state = self._game_states[room_code]
        
        if player.role != "werewolf":
            raise BadRequestError("Only werewolf can kill")
        if game_state.phase != WerewolfPhase.NIGHT_WEREWOLF:
            raise BadRequestError("Not werewolf action phase")
        
        self.engine.process_werewolf_action(game_state, target_seat)
        if target_seat:
            game_state.game_logs.append(f"夜晚：狼人选择击杀{target_seat}号玩家")
        else:
            game_state.game_logs.append("夜晚：狼人选择空刀")
        
        # Continue to seer phase
        await self._execute_seer_action(room_code)
    
    async def _handle_human_check(
        self,
        room_code: str,
        player: PlayerState,
        target_seat: int | None
    ):
        """Handle human seer check action."""
        game_state = self._game_states[room_code]
        
        if player.role != "seer":
            raise BadRequestError("Only seer can check")
        if game_state.phase != WerewolfPhase.NIGHT_SEER:
            raise BadRequestError("Not seer action phase")
        
        if target_seat:
            is_werewolf = self.engine.process_seer_action(game_state, target_seat)
            game_state.game_logs.append(
                f"夜晚：预言家查验了{target_seat}号玩家，结果是{'狼人' if is_werewolf else '好人'}"
            )
            
            # Notify human of result
            target_player = game_state.players.get(target_seat)
            await notify_seer_result(
                room_code=room_code,
                seer_player_id=player.player_id,
                target_seat=target_seat,
                target_name=f"玩家{target_seat}",
                is_werewolf=is_werewolf
            )
        
        # Continue to witch phase
        await self._execute_witch_action(room_code)
    
    async def _handle_human_save(
        self,
        room_code: str,
        player: PlayerState,
        target_seat: int | None
    ):
        """Handle human witch save action."""
        game_state = self._game_states[room_code]
        
        if player.role != "witch":
            raise BadRequestError("Only witch can save")
        if game_state.phase != WerewolfPhase.NIGHT_WITCH:
            raise BadRequestError("Not witch action phase")
        
        self.engine.process_witch_action(game_state, save_target=target_seat)
        if target_seat:
            game_state.game_logs.append(f"夜晚：女巫救了{target_seat}号玩家")
    
    async def _handle_human_poison(
        self,
        room_code: str,
        player: PlayerState,
        target_seat: int | None
    ):
        """Handle human witch poison action."""
        game_state = self._game_states[room_code]
        
        if player.role != "witch":
            raise BadRequestError("Only witch can poison")
        if game_state.phase != WerewolfPhase.NIGHT_WITCH:
            raise BadRequestError("Not witch action phase")
        
        self.engine.process_witch_action(game_state, poison_target=target_seat)
        if target_seat:
            game_state.game_logs.append(f"夜晚：女巫毒了{target_seat}号玩家")
        
        # End night phase
        await self._end_night_phase(room_code)
    
    async def _handle_human_shoot(
        self,
        room_code: str,
        player: PlayerState,
        target_seat: int | None
    ):
        """Handle human hunter shoot action."""
        game_state = self._game_states[room_code]
        game_id = game_state.game_id
        
        if player.role != "hunter":
            raise BadRequestError("Only hunter can shoot")
        
        if target_seat:
            self.engine.process_hunter_shoot(game_state, target_seat)
            game_state.game_logs.append(f"猎人开枪带走了{target_seat}号玩家")
            
            # Announce hunter shoot
            await broadcast_host_announcement(
                room_code=room_code,
                announcement_type="hunter_shoot",
                content=f"猎人发动技能，带走了{target_seat}号玩家！",
                metadata={"target_seat": target_seat}
            )
        
        # Check win and continue
        winner = self.engine.check_winner(game_state)
        if winner:
            await self._end_game(room_code, winner)
        elif game_state.phase == WerewolfPhase.DAY_ANNOUNCEMENT:
            await self._start_day_discussion(room_code, game_id)
        else:
            # day_number is already incremented in advance_to_day
            await self._start_night_phase(room_code, game_id)
    
    async def _handle_human_vote(
        self,
        room_code: str,
        player: PlayerState,
        target_seat: int | None
    ):
        """Handle human vote action."""
        game_state = self._game_states[room_code]
        
        if game_state.phase != WerewolfPhase.DAY_VOTE:
            raise BadRequestError("Not voting phase")
        
        self.engine.process_vote(game_state, player.seat_number, target_seat)
        game_state.game_logs.append(
            f"投票: {player.seat_number}号投给{target_seat}号" if target_seat 
            else f"投票: {player.seat_number}号弃票"
        )
    
    # =========================================================================
    # B38: 遗言处理
    # =========================================================================
    
    async def _handle_last_words(self, room_code: str, dead_seat: int, death_reason: str, game_id: str):
        """Handle last words from a dead player.
        
        Args:
            room_code: Room code
            dead_seat: Seat number of dead player
            death_reason: Reason of death ('night_kill', 'vote', 'poison', 'hunter_shot')
            game_id: Game ID
        """
        game_state = self._validate_game_state(room_code, game_id)
        if not game_state:
            return
        
        player = game_state.players.get(dead_seat)
        if not player:
            return
        
        # 检查是否暂停或停止
        if not await self._check_paused_or_stopped(room_code, game_id):
            return
        
        # Announce last words request
        reason_text = {
            "night_kill": "昨夜不幸遇害",
            "vote": "被放逐出局",
            "poison": "被毒杀",
            "hunter_shot": "被猎人带走"
        }.get(death_reason, "离开了游戏")
        
        await broadcast_host_announcement(
            room_code=room_code,
            announcement_type="last_words_request",
            content=f"{dead_seat}号玩家{reason_text}，请留下遗言。",
            metadata={"seat_number": dead_seat, "death_reason": death_reason}
        )
        
        if dead_seat in self._ai_agents:
            # AI player gives last words
            agent = self._ai_agents[dead_seat]
            
            # Build game_state dict for agent
            agent_alive_players = [
                {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                for p in game_state.players.values() if p.is_alive
            ]
            agent_dead_players = [
                {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                for p in game_state.players.values() if not p.is_alive
            ]
            agent_game_state = {
                "day_number": game_state.day_number,
                "alive_players": agent_alive_players,
                "dead_players": agent_dead_players,
            }
            
            # Get previous speeches for context
            previous_speeches = self._format_speech_entries(
                game_state.speech_history,
                limit=12
            )
            
            # Generate last words
            last_words_stream = agent.generate_last_words_stream(
                game_state=agent_game_state,
                death_reason=death_reason,
                previous_speeches=previous_speeches
            )
            
            last_words_content = await stream_ai_speech(
                room_code=room_code,
                speaker_seat=dead_seat,
                speaker_name=f"玩家{dead_seat}",
                speech_stream=last_words_stream
            )
            
            game_state.game_logs.append(
                f"第{game_state.day_number}天 - {dead_seat}号遗言: {last_words_content}"
            )
            self._record_speech_entry(
                game_state,
                seat_number=dead_seat,
                player_name=player.player_name,
                content=last_words_content,
                speech_type="last_words"
            )
        else:
            # T48: 人类玩家遗言 - 等待玩家输入
            timeout_seconds = 60  # 60秒超时
            self._set_waiting_for_human(room_code, "last_words", timeout_seconds)
            
            # 设置遗言元数据
            game_state.last_words_seat = dead_seat
            game_state.last_words_reason = death_reason
            
            # 生成遗言预设选项
            last_words_options = self._generate_last_words_options(game_state, dead_seat, death_reason)
            
            # 广播等待人类遗言
            await broadcast_waiting_for_human(
                room_code=room_code,
                action_type="last_words",
                seat_number=dead_seat,
                timeout_seconds=timeout_seconds,
                metadata={
                    "death_reason": death_reason,
                    "options": last_words_options
                }
            )
            
            # 广播遗言选项
            await broadcast_last_words_options(
                room_code=room_code,
                seat_number=dead_seat,
                options=last_words_options,
                death_reason=death_reason
            )
            
            logger.info(f"Waiting for human player {dead_seat} last words, timeout: {timeout_seconds}s")
            
            # 等待人类输入（通过 WebSocket 事件处理）
            # 超时处理将由 _check_human_timeout 处理
            await self._wait_for_human_action(room_code, "last_words")
    
    # =========================================================================
    # B39: 猎人技能和游戏结束
    # =========================================================================
    
    async def _handle_hunter_shoot(self, room_code: str, hunter_seat: int, game_id: str):
        """Handle hunter death and shooting."""
        game_state = self._validate_game_state(room_code, game_id)
        if not game_state:
            return
        
        old_phase = game_state.phase
        game_state.phase = WerewolfPhase.HUNTER_SHOOT
        
        # Broadcast phase change
        await broadcast_phase_change(
            room_code=room_code,
            from_phase=old_phase.value,
            to_phase=game_state.phase.value,
            day_number=game_state.day_number
        )
        
        hunter = game_state.players.get(hunter_seat)
        if not hunter:
            return
        
        # Get alive targets
        targets = [
            {"seat_number": p.seat_number, "display_name": f"玩家{p.seat_number}"}
            for p in game_state.players.values()
            if p.is_alive and p.seat_number != hunter_seat
        ]
        
        if hunter_seat in self._ai_agents:
            # AI hunter
            hunter_agent = self._ai_agents[hunter_seat]
            
            # Build game_state dict for agent
            agent_alive_players = [
                {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                for p in game_state.players.values() if p.is_alive
            ]
            agent_dead_players = [
                {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                for p in game_state.players.values() if not p.is_alive
            ]
            # 获取发言历史
            speech_history_text = ""
            if game_state.speech_history:
                speech_history_text = self._speeches_to_text(game_state.speech_history)
            
            agent_game_state = {
                "day_number": game_state.day_number,
                "alive_players": agent_alive_players,
                "dead_players": agent_dead_players,
                "speech_history": speech_history_text,  # 添加发言历史
            }
            # Build available targets
            available_targets = [
                {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
                for p in game_state.players.values()
                if p.is_alive and p.seat_number != hunter_seat
            ]
            # Determine death reason
            death_reason = hunter.death_reason.value if hunter.death_reason else "unknown"
            
            result = await hunter_agent.decide_shoot(
                game_state=agent_game_state,
                death_reason=death_reason,
                available_targets=available_targets
            )
            raw_target = result.get("target") if isinstance(result, dict) else result
            shoot_target = self._normalize_seat_number(raw_target)
            
            if shoot_target:
                self.engine.process_hunter_shoot(game_state, shoot_target)
                game_state.game_logs.append(f"猎人开枪带走了{shoot_target}号玩家")
                
                await broadcast_host_announcement(
                    room_code=room_code,
                    announcement_type="hunter_shoot",
                    content=f"猎人发动技能，带走了{shoot_target}号玩家！",
                    metadata={"target_seat": shoot_target}
                )
            
            # Note: Win check and next phase transition is handled by the caller
            # (_end_night_phase or vote processing)
        else:
            # T34: 人类猎人开枪 - 等待玩家选择目标
            timeout_seconds = 30  # 30秒超时（猎人开枪需要快速决定）
            self._set_waiting_for_human(room_code, "hunter_shoot", timeout_seconds)
            
            # 生成开枪目标选项
            shoot_options = [
                {
                    "seat_number": p.seat_number,
                    "display_name": f"玩家{p.seat_number}",
                    "player_name": p.player_name
                }
                for p in game_state.players.values()
                if p.is_alive and p.seat_number != hunter_seat
            ]
            # 添加不开枪选项
            shoot_options.append({
                "seat_number": None,
                "display_name": "不开枪",
                "player_name": None
            })
            
            # 广播等待人类猎人行动
            await broadcast_waiting_for_human(
                room_code=room_code,
                action_type="hunter_shoot",
                seat_number=hunter_seat,
                timeout_seconds=timeout_seconds,
                metadata={
                    "role": "hunter",
                    "death_reason": hunter.death_reason.value if hunter.death_reason else "unknown",
                    "options": shoot_options
                }
            )
            
            # 通知人类猎人该开枪了
            await notify_hunter_shoot(
                room_code=room_code,
                hunter_player_id=hunter.player_id,
                alive_targets=targets
            )
            
            # 等待人类玩家输入或超时
            while game_state.waiting_for_human_action:
                if await self._check_human_timeout(room_code, game_id):
                    break
                
                # 检查是否暂停或停止
                if not await self._check_paused_or_stopped(room_code, game_id):
                    return
                
                # 短暂休眠，避免忙等待
                await asyncio.sleep(0.1)
    
    async def _end_game(self, room_code: str, winner: str):
        """End the game and announce winner."""
        game_state = self._game_states.get(room_code)
        if not game_state:
            return
        
        old_phase = game_state.phase
        game_state.phase = WerewolfPhase.GAME_OVER
        game_state.winner = winner
        
        # Broadcast phase change
        await broadcast_phase_change(
            room_code=room_code,
            from_phase=old_phase.value,
            to_phase=game_state.phase.value,
            day_number=game_state.day_number
        )
        
        # 角色名称映射
        role_name_map = {
            "werewolf": "狼人",
            "seer": "预言家",
            "witch": "女巫",
            "hunter": "猎人",
            "villager": "村民"
        }
        
        # Prepare player info for reveal - 使用角色名称代替玩家X
        all_players = [
            {
                "seat_number": p.seat_number,
                "display_name": role_name_map.get(p.role, p.role),  # 使用角色中文名
                "role": p.role,
                "role_name": role_name_map.get(p.role, p.role),  # 添加角色中文名
                "team": p.team,
                "is_alive": p.is_alive
            }
            for p in game_state.players.values()
        ]
        
        winning_team = "werewolf" if winner == "werewolf" else "villager"
        winning_players = [p for p in all_players if p["team"] == winning_team]
        
        # Build werewolf and good player lists for announcement - 使用角色名称
        werewolf_players = [
            {"seat_number": p["seat_number"], "name": role_name_map.get("werewolf", "狼人")}
            for p in all_players if p["role"] == "werewolf"
        ]
        good_players = [
            {"seat_number": p["seat_number"], "name": p["role_name"]}
            for p in all_players if p["team"] == "villager"
        ]
        
        # Announce game over
        winner_team_name = "狼人阵营" if winner == "werewolf" else "好人阵营"
        announcement_stream = self.host.announce_game_end(
            winner_team=winner_team_name,
            werewolf_players=werewolf_players,
            good_players=good_players,
            total_days=game_state.day_number,
            stream=True
        )
        await stream_host_announcement(
            room_code=room_code,
            announcement_type="game_over",
            content_stream=announcement_stream,
            metadata={"winner": winner}
        )
        
        # Broadcast detailed results
        await broadcast_game_over(
            room_code=room_code,
            winner=winner,
            winning_players=winning_players,
            all_players=all_players
        )
        
        game_state.game_logs.append(f"游戏结束，{'狼人阵营' if winner == 'werewolf' else '好人阵营'}获胜！")
        
        # T45: 游戏结束时公开狼人私密讨论记录
        if game_state.werewolf_private_chat:
            # 添加分隔标记
            game_state.game_logs.append("===== 狼人私密讨论记录 =====")
            
            # 按夜晚分组公开讨论记录
            chat_by_night: dict[int, list[dict]] = {}
            for entry in game_state.werewolf_private_chat:
                night = entry.get("night_number", 1)
                if night not in chat_by_night:
                    chat_by_night[night] = []
                chat_by_night[night].append(entry)
            
            # 按夜晚顺序添加到日志
            for night in sorted(chat_by_night.keys()):
                game_state.game_logs.append(f"--- 第{night}夜 ---")
                for entry in chat_by_night[night]:
                    seat = entry.get("seat_number", "?")
                    player_name = entry.get("player_name", f"玩家{seat}")
                    content = entry.get("content", "")
                    is_human = entry.get("is_human", False)
                    human_marker = "[人类]" if is_human else "[AI]"
                    game_state.game_logs.append(
                        f"{seat}号{player_name}{human_marker}: {content}"
                    )
            
            game_state.game_logs.append("===== 讨论记录结束 =====")
            
            logger.info(f"Published {len(game_state.werewolf_private_chat)} wolf chat messages for room {room_code}")
        
        logger.info(f"Game ended in room {room_code}: {winner} wins")
        
        # Clean up
        self._cleanup_game(room_code)
    
    def _cleanup_game(self, room_code: str):
        """Clean up game resources."""
        if room_code in self._game_states:
            del self._game_states[room_code]
        
        # Clear AI agents for this game
        # Note: In production, agents should be scoped per game
        self._ai_agents.clear()

    # =========================================================================
    # 游戏控制方法 (Phase 3: B6, B7, B8, B9)
    # =========================================================================

    async def start_game_manual(self, room_code: str) -> bool:
        """手动开始游戏（由用户触发）。

        Args:
            room_code: 房间代码

        Returns:
            是否成功开始游戏

        Raises:
            NotFoundError: 游戏状态不存在
            BadRequestError: 游戏已开始
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            raise NotFoundError(f"游戏状态不存在: {room_code}")

        if game_state.is_started:
            raise BadRequestError("游戏已经开始")

        # 设置游戏已开始
        game_state.is_started = True
        game_state.is_paused = False

        logger.info(f"Game manually started in room {room_code}")

        # 记录日志
        self._add_game_log(
            room_code=room_code,
            log_type="system",
            content="游戏开始",
            metadata={"triggered_by": "manual"},
        )

        return True

    async def pause_game(self, room_code: str) -> bool:
        """暂停游戏，等待当前行动完成后生效。

        Args:
            room_code: 房间代码

        Returns:
            是否成功暂停

        Raises:
            NotFoundError: 游戏状态不存在
            BadRequestError: 游戏未开始或已暂停
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            raise NotFoundError(f"游戏状态不存在: {room_code}")

        if not game_state.is_started:
            raise BadRequestError("游戏尚未开始")

        if game_state.is_paused:
            raise BadRequestError("游戏已经暂停")

        # 标记暂停（当前行动完成后生效）
        game_state.is_paused = True

        logger.info(f"Game paused in room {room_code}")

        # 记录日志
        self._add_game_log(
            room_code=room_code,
            log_type="system",
            content="游戏暂停",
        )

        return True

    async def resume_game(self, room_code: str) -> bool:
        """继续游戏。

        Args:
            room_code: 房间代码

        Returns:
            是否成功继续

        Raises:
            NotFoundError: 游戏状态不存在
            BadRequestError: 游戏未暂停
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            raise NotFoundError(f"游戏状态不存在: {room_code}")

        if not game_state.is_paused:
            raise BadRequestError("游戏未暂停")

        # 取消暂停
        game_state.is_paused = False

        logger.info(f"Game resumed in room {room_code}")

        # 记录日志
        self._add_game_log(
            room_code=room_code,
            log_type="system",
            content="游戏继续",
        )

        return True

    async def stop_game(self, room_code: str) -> bool:
        """停止游戏（用户离开房间时调用）。

        此方法会立即停止游戏循环，不等待当前行动完成。

        Args:
            room_code: 房间代码

        Returns:
            是否成功停止
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            logger.info(f"Game state not found for stop_game: {room_code}")
            return False

        # 设置停止标志
        game_state.is_stopped = True
        game_state.is_paused = False  # 确保不会卡在暂停状态

        logger.info(f"Game stopped in room {room_code}")

        # 记录日志
        self._add_game_log(
            room_code=room_code,
            log_type="system",
            content="游戏已停止（用户离开）",
        )

        # 清理游戏资源
        self._cleanup_game(room_code)

        return True

    async def _check_paused_or_stopped(self, room_code: str, game_id: str | None = None) -> bool:
        """在执行下一个行动前检查是否暂停或停止。

        如果游戏暂停，此方法会阻塞直到游戏继续。
        如果游戏停止，此方法返回 False。

        Args:
            room_code: 房间代码
            game_id: 游戏ID（可选），用于验证游戏实例是否匹配

        Returns:
            True 表示可以继续执行，False 表示游戏已停止或状态不存在
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return False
            
        if game_id and game_state.game_id != game_id:
            return False

        # 如果已停止，直接返回 False
        if game_state.is_stopped:
            return False

        # 如果暂停，等待继续
        while game_state.is_paused:
            await asyncio.sleep(0.5)
            # 重新获取状态，以防游戏被清理或停止
            game_state = self._game_states.get(room_code)
            if not game_state or game_state.is_stopped:
                return False
            if game_id and game_state.game_id != game_id:
                return False

        return True

    async def _check_paused_before_next_action(self, room_code: str) -> bool:
        """在执行下一个行动前检查是否暂停。

        如果游戏暂停，此方法会阻塞直到游戏继续。

        Args:
            room_code: 房间代码

        Returns:
            True 表示可以继续执行，False 表示游戏状态不存在
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return False

        # 如果暂停，等待继续
        while game_state.is_paused:
            await asyncio.sleep(0.5)
            # 重新获取状态，以防游戏被清理
            game_state = self._game_states.get(room_code)
            if not game_state:
                return False

        return True

    # =========================================================================
    # 主持人公告广播 (Phase 4: B10)
    # =========================================================================

    async def _broadcast_host_announcement(
        self,
        room_code: str,
        announcement_type: str,
        metadata: dict | None = None,
    ) -> str:
        """广播主持人公告（流式）。

        流程：
        1. 调用 WerewolfHost 生成公告
        2. 发送 announcement_start 事件
        3. 循环发送 announcement_chunk 事件
        4. 发送 announcement_end 事件
        5. 记录到游戏日志

        Args:
            room_code: 房间代码
            announcement_type: 公告类型
            metadata: 额外元数据

        Returns:
            完整的公告内容
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            logger.warning(f"Cannot broadcast announcement: game state not found for {room_code}")
            return ""

        # 构建公告上下文
        context = self._build_announcement_context(game_state, announcement_type, metadata)

        # 使用流式输出广播公告
        content_stream = self.host.announce_stream(announcement_type, context)

        full_content = await stream_host_announcement(
            room_code=room_code,
            announcement_type=announcement_type,
            content_stream=content_stream,
            metadata=metadata,
        )

        # 记录到游戏日志
        self._add_game_log(
            room_code=room_code,
            log_type="host_announcement",
            content=full_content,
            metadata={
                "announcement_type": announcement_type,
                **(metadata or {}),
            },
            is_public=True,
        )

        return full_content

    def _build_announcement_context(
        self,
        game_state: WerewolfGameState,
        announcement_type: str,
        metadata: dict | None = None,
    ) -> dict:
        """为主持人公告构建上下文。

        Args:
            game_state: 游戏状态
            announcement_type: 公告类型
            metadata: 额外元数据

        Returns:
            上下文字典
        """
        base_context = {
            "day_number": game_state.day_number,
            "alive_count": len([p for p in game_state.players.values() if p.is_alive]),
        }

        # 根据公告类型添加特定上下文
        if announcement_type == "game_start":
            werewolf_count = len([
                p for p in game_state.players.values() if p.role == "werewolf"
            ])
            base_context.update({
                "player_count": len(game_state.players),
                "role_config": f"3狼人、1预言家、1女巫、1猎人、4村民",
            })

        elif announcement_type == "night_start":
            pass  # 基础上下文已足够

        elif announcement_type == "dawn":
            # 从 metadata 获取死亡信息
            dead_players = metadata.get("dead_players", []) if metadata else []
            dead_text = ", ".join([
                f"{p['seat_number']}号"
                for p in dead_players
            ]) if dead_players else "无"

            base_context.update({
                "dead_players": dead_text,
                "death_reasons": metadata.get("death_reasons", "无") if metadata else "无",
            })

        elif announcement_type == "discussion_start":
            alive_players = [
                p for p in game_state.players.values() if p.is_alive
            ]
            base_context.update({
                "alive_players": ", ".join([f"{p.seat_number}号" for p in alive_players]),
                "speaking_order": ", ".join([str(p.seat_number) for p in sorted(alive_players, key=lambda x: x.seat_number)]),
            })

        elif announcement_type == "vote_start":
            alive_players = [
                p for p in game_state.players.values() if p.is_alive
            ]
            base_context.update({
                "voters": ", ".join([f"{p.seat_number}号" for p in alive_players]),
                "candidates": ", ".join([f"{p.seat_number}号" for p in alive_players]),
            })

        elif announcement_type == "vote_result":
            if metadata:
                vote_counts = metadata.get("vote_counts", {})
                base_context.update({
                    "vote_counts": ", ".join([f"{k}号: {v}票" for k, v in vote_counts.items()]),
                    "highest_vote_player": metadata.get("eliminated_name", "无"),
                    "is_tie": metadata.get("is_tie", False),
                })

        elif announcement_type == "request_speech":
            if metadata:
                base_context.update({
                    "seat_number": metadata.get("seat_number"),
                    "player_name": metadata.get("player_name", ""),
                    "is_human": metadata.get("is_human", False),
                })

        elif announcement_type == "game_end":
            if metadata:
                base_context.update({
                    "winner_team": "狼人阵营" if metadata.get("winner") == "werewolf" else "好人阵营",
                    "werewolf_players": metadata.get("werewolf_players", ""),
                    "good_players": metadata.get("good_players", ""),
                    "total_days": game_state.day_number,
                })

        return base_context
    
    # =========================================================================
    # 讨论流程实现 (Phase 5: B11, B12, B13, B14)
    # =========================================================================

    async def _execute_discussion_phase(self, room_code: str) -> None:
        """执行讨论阶段主流程（主持人主导）。

        流程：
        1. 广播讨论开始公告
        2. 获取存活玩家列表（按座位号排序）
        3. 依次调用 _request_player_speech
        4. 广播发言结束公告

        Args:
            room_code: 房间代码
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            logger.warning(f"Cannot execute discussion: game state not found for {room_code}")
            return

        # 更新阶段
        old_phase = game_state.phase
        game_state.phase = WerewolfPhase.DAY_DISCUSSION

        await broadcast_phase_change(
            room_code=room_code,
            from_phase=old_phase.value if old_phase else "unknown",
            to_phase=game_state.phase.value,
            day_number=game_state.day_number,
        )

        # 1. 广播讨论开始公告
        await self._broadcast_host_announcement(
            room_code=room_code,
            announcement_type="discussion_start",
            metadata={"day_number": game_state.day_number},
        )

        # 2. 获取存活玩家列表（按座位号排序）
        alive_players = sorted(
            [p for p in game_state.players.values() if p.is_alive],
            key=lambda p: p.seat_number,
        )

        # 3. 依次调用 _request_player_speech
        for player in alive_players:
            # 检查暂停状态
            if not await self._check_paused_before_next_action(room_code):
                return

            # 点名发言
            await self._request_player_speech(room_code, player)

        # 等待0.5秒，确保最后一个发言结束公告显示完毕
        await asyncio.sleep(0.5)

        # 4. 广播发言结束公告
        await self._broadcast_host_announcement(
            room_code=room_code,
            announcement_type="discussion_end",
            metadata={"day_number": game_state.day_number},
        )

        logger.info(f"Discussion phase completed in room {room_code}")

    async def _request_player_speech(
        self,
        room_code: str,
        player: PlayerState,
    ) -> None:
        """主持人点名玩家发言。

        流程：
        1. 广播点名公告（使用 AI Host）
        2. 发送 werewolf:request_speech 事件
        3. 设置 current_speaker_seat
        4. 根据是否人类玩家选择等待或触发 AI 发言

        Args:
            room_code: 房间代码
            player: 玩家状态
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return

        is_human = player.seat_number not in self._ai_agents
        player_name = f"玩家{player.seat_number}"

        # 1. 广播点名公告
        announcement_content = await self.host.announce_request_speech(
            seat_number=player.seat_number,
            player_name=player_name,
            is_human=is_human,
            stream=False,
        )

        # 2. 发送 request_speech 事件（通过 WebSocket 广播）
        from src.websocket import broadcast_to_room

        await broadcast_to_room(
            room_code=room_code,
            event="werewolf:request_speech",
            data={
                "seat_number": player.seat_number,
                "player_name": player_name,
                "is_human": is_human,
                "announcement": announcement_content,
            },
        )

        # 3. 设置 current_speaker_seat
        game_state.current_speaker_seat = player.seat_number

        # 记录日志
        self._add_game_log(
            room_code=room_code,
            log_type="host_announcement",
            content=announcement_content,
            metadata={
                "announcement_type": "request_speech",
                "seat_number": player.seat_number,
                "is_human": is_human,
            },
            is_public=True,
        )

        # 4. 根据是否人类玩家选择处理方式
        if is_human:
            # 人类玩家：等待发言
            speech_content = await self._wait_for_human_speech(room_code, player)

            if speech_content:
                # 记录人类发言
                self._add_game_log(
                    room_code=room_code,
                    log_type="speech",
                    content=speech_content,
                    player_id=player.player_id,
                    player_name=player_name,
                    seat_number=player.seat_number,
                    is_public=True,
                )
        else:
            # AI 玩家：触发 AI 发言
            await self._execute_ai_speech(room_code, player)

        # 发言结束处理
        await self._handle_speech_end(room_code, player)

    async def _wait_for_human_speech(
        self,
        room_code: str,
        player: PlayerState,
    ) -> str | None:
        """等待人类玩家发言（无超时，无限等待）。

        流程：
        1. 设置 waiting_for_player_input = True
        2. 启动提醒任务（每30秒）
        3. 使用 asyncio.Event 等待发言
        4. 返回发言内容

        Args:
            room_code: 房间代码
            player: 玩家状态

        Returns:
            发言内容，如果超时或取消则返回 None
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return None

        # 1. 设置等待状态
        game_state.waiting_for_player_input = True
        game_state.speech_reminder_count = 0

        # 创建等待事件
        speech_event = asyncio.Event()
        speech_content: list[str] = []  # 使用列表来存储发言内容

        # 存储事件引用，供 process_player_speech 使用
        if not hasattr(game_state, "_speech_events"):
            game_state._speech_events = {}
        game_state._speech_events[player.seat_number] = {
            "event": speech_event,
            "content": speech_content,
        }

        # 2. 启动提醒任务
        reminder_task = asyncio.create_task(
            self._speech_reminder_loop(room_code, player)
        )

        try:
            # 3. 等待发言
            await speech_event.wait()

            # 4. 返回发言内容
            return speech_content[0] if speech_content else None

        finally:
            # 清理
            reminder_task.cancel()
            try:
                await reminder_task
            except asyncio.CancelledError:
                pass

            game_state.waiting_for_player_input = False
            if hasattr(game_state, "_speech_events"):
                game_state._speech_events.pop(player.seat_number, None)

    async def _speech_reminder_loop(
        self,
        room_code: str,
        player: PlayerState,
    ) -> None:
        """发言提醒循环（每30秒提醒一次）。

        Args:
            room_code: 房间代码
            player: 玩家状态
        """
        while True:
            await asyncio.sleep(30)  # 每30秒提醒一次
            await self._send_speech_reminder(room_code, player)

    async def _send_speech_reminder(
        self,
        room_code: str,
        player: PlayerState,
    ) -> None:
        """发送发言提醒（每30秒）。

        流程：
        1. 递增 speech_reminder_count
        2. 发送 werewolf:speech_reminder 事件

        Args:
            room_code: 房间代码
            player: 玩家状态
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return

        # 1. 递增提醒计数
        game_state.speech_reminder_count += 1

        # 2. 发送提醒事件
        from src.websocket import broadcast_to_room

        await broadcast_to_room(
            room_code=room_code,
            event="werewolf:speech_reminder",
            data={
                "seat_number": player.seat_number,
                "player_name": f"玩家{player.seat_number}",
                "reminder_count": game_state.speech_reminder_count,
                "message": f"请{player.seat_number}号玩家尽快发言，已等待{game_state.speech_reminder_count * 30}秒",
            },
        )

        logger.info(
            f"Sent speech reminder #{game_state.speech_reminder_count} to room {room_code} for player {player.seat_number}"
        )

    async def _execute_ai_speech(
        self,
        room_code: str,
        player: PlayerState,
    ) -> None:
        """执行 AI 玩家发言。

        Args:
            room_code: 房间代码
            player: AI 玩家状态
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return

        agent = self._ai_agents.get(player.seat_number)
        if not agent:
            logger.warning(f"No AI agent found for seat {player.seat_number}")
            return

        alive_players = [p for p in game_state.players.values() if p.is_alive]

        # B16/B18: 构建 AI 上下文
        ai_context = self._build_ai_context(room_code, current_seat=player.seat_number)

        # 更新 Agent 上下文
        agent.update_context(
            speeches=ai_context.get("current_round_speeches", []),
            host_context=ai_context.get("host_context"),
            game_state=ai_context,
        )

        # B18: 生成流式发言（使用增强的参数）
        speech_stream = agent.generate_speech_stream(
            game_state=ai_context,
            previous_speeches=ai_context.get("today_speeches", []),
            current_round_speeches=ai_context.get("current_round_speeches", []),
            host_context=ai_context.get("host_context"),
        )

        # 流式广播发言
        speech_content = await stream_ai_speech(
            room_code=room_code,
            speaker_seat=player.seat_number,
            speaker_name=f"玩家{player.seat_number}",
            speech_stream=speech_stream,
        )

        # 记录发言日志
        self._add_game_log(
            room_code=room_code,
            log_type="speech",
            content=speech_content,
            player_name=f"玩家{player.seat_number}",
            seat_number=player.seat_number,
            is_public=True,
        )

        logger.debug(f"AI player {player.seat_number} speech completed in room {room_code}")

    async def _handle_speech_end(
        self,
        room_code: str,
        player: PlayerState,
    ) -> None:
        """处理发言结束（发送过渡公告）。

        Args:
            room_code: 房间代码
            player: 刚完成发言的玩家
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return

        player_name = f"玩家{player.seat_number}"

        # 使用 AI Host 生成发言结束过渡公告
        transition_content = await self.host.announce_player_speech_end(
            seat_number=player.seat_number,
            player_name=player_name,
            stream=False,
        )

        # 广播发言结束事件
        from src.websocket import broadcast_to_room

        await broadcast_to_room(
            room_code=room_code,
            event="werewolf:speech_end",
            data={
                "seat_number": player.seat_number,
                "player_name": player_name,
                "announcement": transition_content,
            },
        )

        # 清除当前发言者
        game_state.current_speaker_seat = None

        # 等待1秒，确保发言结束公告有时间显示
        await asyncio.sleep(1)

        logger.debug(f"Speech end handled for player {player.seat_number} in room {room_code}")

    # =========================================================================
    # 玩家发言与上下文 (Phase 6: B15, B16)
    # =========================================================================

    async def process_player_speech(
        self,
        room_code: str,
        player_id: str,
        seat_number: int,
        content: str,
    ) -> bool:
        """处理玩家发言。

        流程：
        1. 验证是否轮到该玩家发言
        2. 创建 GameLogEntry 记录发言
        3. 广播 werewolf:player_speech 事件
        4. 设置 waiting_for_player_input = False
        5. 触发发言等待的 Event

        Args:
            room_code: 房间代码
            player_id: 玩家ID
            seat_number: 玩家座位号
            content: 发言内容

        Returns:
            是否成功处理发言

        Raises:
            NotFoundError: 游戏状态不存在
            BadRequestError: 未轮到该玩家发言
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            raise NotFoundError(f"游戏状态不存在: {room_code}")

        # 1. 验证是否轮到该玩家发言
        if game_state.current_speaker_seat != seat_number:
            raise BadRequestError(
                f"当前不是{seat_number}号玩家的发言时间，当前发言者: {game_state.current_speaker_seat}"
            )

        if not game_state.waiting_for_player_input:
            raise BadRequestError("系统未处于等待玩家发言状态")

        # 2. 创建 GameLogEntry 记录发言
        player_name = f"玩家{seat_number}"
        self._add_game_log(
            room_code=room_code,
            log_type="speech",
            content=content,
            player_id=player_id,
            player_name=player_name,
            seat_number=seat_number,
            is_public=True,
        )

        # 3. 广播 werewolf:player_speech 事件
        from src.websocket import broadcast_to_room

        await broadcast_to_room(
            room_code=room_code,
            event="werewolf:player_speech",
            data={
                "seat_number": seat_number,
                "player_name": player_name,
                "content": content,
            },
        )

        # 4. 设置 waiting_for_player_input = False
        game_state.waiting_for_player_input = False

        # 5. 触发发言等待的 Event
        if hasattr(game_state, "_speech_events"):
            speech_event_data = game_state._speech_events.get(seat_number)
            if speech_event_data:
                # 存储发言内容
                speech_event_data["content"].append(content)
                # 触发事件
                speech_event_data["event"].set()

        logger.info(f"Processed speech from player {seat_number} in room {room_code}")

        return True

    def _build_ai_context(
        self,
        room_code: str,
        current_seat: int | None = None,
    ) -> dict:
        """为 AI Agent 构建上下文。

        内容包括：
        - 游戏历史日志
        - 当天所有公开发言
        - 主持人公告摘要
        - 存活玩家信息
        - 本轮已有发言

        Args:
            room_code: 房间代码
            current_seat: 当前请求上下文的玩家座位号（可选）

        Returns:
            结构化的上下文字典
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return {}

        # 获取当天的公开发言
        today_speeches = []
        for log in game_state.game_logss:
            if log.day == game_state.day_number and log.type == "speech" and log.is_public:
                today_speeches.append({
                    "seat_number": log.seat_number,
                    "player_name": log.player_name or f"玩家{log.seat_number}",
                    "content": log.content,
                })

        # 获取主持人公告摘要
        host_announcements = []
        for log in game_state.game_logss:
            if log.type == "host_announcement" and log.is_public:
                announcement_type = log.metadata.get("announcement_type", "") if log.metadata else ""
                host_announcements.append({
                    "type": announcement_type,
                    "content": log.content[:100] + "..." if len(log.content) > 100 else log.content,
                    "day": log.day,
                })

        # 获取存活玩家信息
        alive_players = [
            {
                "seat_number": p.seat_number,
                "player_name": f"玩家{p.seat_number}",
            }
            for p in game_state.players.values()
            if p.is_alive
        ]

        # 获取死亡玩家信息
        dead_players = [
            {
                "seat_number": p.seat_number,
                "player_name": f"玩家{p.seat_number}",
                "death_day": p.death_day,
                "death_reason": p.death_reason,
            }
            for p in game_state.players.values()
            if not p.is_alive
        ]

        # 获取本轮已有发言（当前座位号之前的）
        current_round_speeches = []
        if current_seat is not None:
            for speech in today_speeches:
                if speech["seat_number"] and speech["seat_number"] < current_seat:
                    current_round_speeches.append(speech)

        # 构建完整历史日志（用于AI决策）
        game_history = []
        for log in game_state.game_logss:
            if log.is_public:
                game_history.append({
                    "day": log.day,
                    "phase": log.phase,
                    "type": log.type,
                    "content": log.content,
                    "seat_number": log.seat_number,
                    "player_name": log.player_name,
                })

        return {
            "day_number": game_state.day_number,
            "phase": game_state.phase.value if game_state.phase else "unknown",
            "alive_count": len(alive_players),
            "alive_players": alive_players,
            "dead_players": dead_players,
            "today_speeches": today_speeches,
            "current_round_speeches": current_round_speeches,
            "host_announcements": host_announcements,
            "game_history": game_history,
            "host_context": self._build_host_context_summary(game_state),
        }

    def _build_host_context_summary(self, game_state: WerewolfGameState) -> str:
        """构建主持人上下文摘要。

        Args:
            game_state: 游戏状态

        Returns:
            主持人上下文摘要文本
        """
        summary_parts = [
            f"当前是第{game_state.day_number}天，{game_state.phase.value if game_state.phase else '未知'}阶段。",
        ]

        # 添加存活信息
        alive_count = len([p for p in game_state.players.values() if p.is_alive])
        summary_parts.append(f"场上还有{alive_count}名玩家存活。")

        # 添加死亡信息
        dead_players = [p for p in game_state.players.values() if not p.is_alive]
        if dead_players:
            dead_info = ", ".join([
                f"{p.seat_number}号({p.death_reason or '未知原因'})"
                for p in dead_players
            ])
            summary_parts.append(f"已出局玩家: {dead_info}。")

        return " ".join(summary_parts)

    # =========================================================================
    # 辅助方法
    # =========================================================================

    def _add_game_log(
        self,
        room_code: str,
        log_type: str,
        content: str,
        player_id: str | None = None,
        player_name: str | None = None,
        seat_number: int | None = None,
        metadata: dict | None = None,
        is_public: bool = True,
    ) -> GameLogEntry | None:
        """添加游戏日志条目。

        Args:
            room_code: 房间代码
            log_type: 日志类型 (speech, host_announcement, death, vote, skill)
            content: 日志内容
            player_id: 玩家ID（可选）
            player_name: 玩家名称（可选）
            seat_number: 座位号（可选）
            metadata: 额外元数据（可选）
            is_public: 是否公开（用于日志级别过滤）

        Returns:
            创建的日志条目，如果游戏状态不存在则返回 None
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return None

        log_entry = GameLogEntry.create(
            log_type=log_type,
            content=content,
            day=game_state.day_number,
            phase=game_state.phase.value if game_state.phase else "unknown",
            player_id=player_id,
            player_name=player_name,
            seat_number=seat_number,
            metadata=metadata,
            is_public=is_public,
        )

        game_state.game_logs.append(log_entry)
        logger.debug(f"Added game log: [{log_type}] {content[:50]}...")

        return log_entry
    
    def get_game_state(self, room_code: str) -> WerewolfGameState | None:
        """Get current game state."""
        return self._game_states.get(room_code)
    
    def get_player_role(self, room_code: str, player_id: str) -> str | None:
        """Get a player's role (for their eyes only)."""
        game_state = self._game_states.get(room_code)
        if not game_state:
            return None
        
        for player in game_state.players.values():
            if player.player_id == player_id:
                return player.role
        return None
    
    def get_visible_state(
        self,
        room_code: str,
        player_id: str
    ) -> dict | None:
        """Get game state visible to a specific player."""
        game_state = self._game_states.get(room_code)
        if not game_state:
            return None
        
        # Find requesting player
        requesting_player = next(
            (p for p in game_state.players.values() if p.player_id == player_id),
            None
        )
        
        # Build visible state
        players_info = []
        for p in game_state.players.values():
            info = {
                "seat_number": p.seat_number,
                "display_name": f"玩家{p.seat_number}",
                "is_alive": p.is_alive
            }
            
            # Show role only for self or if game is over
            if p.player_id == player_id or game_state.phase == WerewolfPhase.GAME_OVER:
                info["role"] = p.role
                info["team"] = p.team
            
            # Show death info for dead players
            if not p.is_alive:
                info["death_reason"] = p.death_reason
                info["death_day"] = p.death_day
            
            players_info.append(info)
        
        return {
            "room_code": room_code,
            "phase": game_state.phase.value,
            "sub_phase": game_state.sub_phase,
            "day_number": game_state.day_number,
            "players": players_info,
            "winner": game_state.winner,
            "your_seat": requesting_player.seat_number if requesting_player else None,
            "your_role": requesting_player.role if requesting_player else None
        }
