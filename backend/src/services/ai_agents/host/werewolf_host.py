# -*- coding: utf-8 -*-
"""Werewolf game host AI agent."""

import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from src.integrations.llm_client import LLMClient
from src.services.ai_agents.host.base_host import BaseGameHost
from src.services.ai_agents.prompts.host_prompts import (
    HOST_ANNOUNCEMENT_PROMPTS,
    HOST_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class WerewolfHost(BaseGameHost):
    """AI host for werewolf game."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize werewolf host.

        :param llm_client: LLM client for generating announcements.
        """
        super().__init__(llm_client)

    def get_system_prompt(self) -> str:
        """Get host system prompt."""
        return HOST_SYSTEM_PROMPT

    async def announce(
        self,
        announcement_type: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Generate a host announcement.

        :param announcement_type: Type of announcement (e.g., 'game_start', 'night_start').
        :param context: Context data for filling the prompt template.
        :return: Generated announcement text.
        """
        prompt_template = HOST_ANNOUNCEMENT_PROMPTS.get(announcement_type)
        if not prompt_template:
            logger.warning(f"Unknown announcement type: {announcement_type}")
            return self._get_fallback_announcement(announcement_type, context)

        try:
            prompt = prompt_template.format(**context)
            return await self._generate(prompt)
        except KeyError as e:
            logger.error(f"Missing context key for {announcement_type}: {e}")
            return self._get_fallback_announcement(announcement_type, context)
        except Exception as e:
            logger.error(f"Announcement generation failed: {e}")
            return self._get_fallback_announcement(announcement_type, context)

    async def announce_stream(
        self,
        announcement_type: str,
        context: Dict[str, Any],
    ) -> AsyncIterator[str]:
        """
        Generate a streaming host announcement.

        :param announcement_type: Type of announcement.
        :param context: Context data for filling the prompt template.
        :yields: Chunks of announcement text.
        """
        prompt_template = HOST_ANNOUNCEMENT_PROMPTS.get(announcement_type)
        if not prompt_template:
            logger.warning(f"Unknown announcement type: {announcement_type}")
            yield self._get_fallback_announcement(announcement_type, context)
            return

        try:
            prompt = prompt_template.format(**context)
            async for chunk in self._generate_stream(prompt):
                yield chunk
        except KeyError as e:
            logger.error(f"Missing context key for {announcement_type}: {e}")
            yield self._get_fallback_announcement(announcement_type, context)
        except Exception as e:
            logger.error(f"Streaming announcement failed: {e}")
            yield self._get_fallback_announcement(announcement_type, context)

    def _get_fallback_announcement(
        self,
        announcement_type: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Get a fallback announcement when LLM fails.

        :param announcement_type: Type of announcement.
        :param context: Context data.
        :return: Fallback announcement text.
        """
        fallbacks = {
            "game_start": "欢迎来到狼人杀游戏！游戏即将开始，请各位玩家准备好。天黑请闭眼。",
            "night_start": f"夜幕降临，第{context.get('day_number', '?')}天的夜晚开始了。所有玩家请闭眼。",
            "dawn": self._format_dawn_fallback(context),
            "discussion_start": "天亮了，讨论阶段开始。请各位玩家依次发言。",
            "vote_start": "讨论结束，投票阶段开始。请各位玩家进行投票。",
            "vote_result": self._format_vote_result_fallback(context),
            "hunter_shoot": f"猎人 {context.get('hunter_name', '?')} 开枪带走了 {context.get('target_name', '?')}！",
            "game_end": f"游戏结束！{context.get('winner_team', '?')}获胜！",
            "request_speech": f"请{context.get('seat_number', '?')}号玩家{context.get('player_name', '')}发言。",
            "speech_end_transition": f"请{context.get('next_seat_number', '?')}号玩家发言。",
        }
        return fallbacks.get(announcement_type, "游戏继续进行中...")

    def _format_dawn_fallback(self, context: Dict[str, Any]) -> str:
        """Format fallback dawn announcement."""
        dead_players = context.get("dead_players", [])
        if not dead_players or dead_players == "无":
            return "天亮了，昨晚是平安夜，无人死亡。"
        return f"天亮了，昨晚 {dead_players} 死亡。"

    def _format_vote_result_fallback(self, context: Dict[str, Any]) -> str:
        """Format fallback vote result announcement."""
        is_tie = context.get("is_tie", False)
        if is_tie:
            return "投票结束，平票，无人出局。"
        player = context.get("highest_vote_player", "?")
        return f"投票结束，{player} 被放逐。"

    # Convenience methods for specific announcements

    async def announce_game_start(
        self,
        player_count: int,
        role_config: str,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """
        Announce game start.

        :param player_count: Number of players.
        :param role_config: Role configuration description.
        :param stream: Whether to stream the announcement.
        :yields: Announcement text chunks.
        """
        context = {
            "player_count": player_count,
            "role_config": role_config,
        }

        if stream:
            async for chunk in self.announce_stream("game_start", context):
                yield chunk
        else:
            yield await self.announce("game_start", context)

    async def announce_night(
        self,
        day_number: int,
        alive_count: int,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """
        Announce night start.

        :param day_number: Current day number.
        :param alive_count: Number of alive players.
        :param stream: Whether to stream.
        :yields: Announcement chunks.
        """
        context = {
            "day_number": day_number,
            "alive_count": alive_count,
        }

        if stream:
            async for chunk in self.announce_stream("night_start", context):
                yield chunk
        else:
            yield await self.announce("night_start", context)

    async def announce_dawn(
        self,
        dead_players: List[Dict[str, Any]],
        death_reasons: List[str],
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """
        Announce dawn and death results.

        :param dead_players: List of players who died.
        :param death_reasons: List of death reasons.
        :param stream: Whether to stream.
        :yields: Announcement chunks.
        """
        dead_text = ", ".join([
            f"{p['seat_number']}号{p['name']}"
            for p in dead_players
        ]) if dead_players else "无"

        reasons_text = ", ".join(death_reasons) if death_reasons else "无"

        context = {
            "dead_players": dead_text,
            "death_reasons": reasons_text,
        }

        if stream:
            async for chunk in self.announce_stream("dawn", context):
                yield chunk
        else:
            yield await self.announce("dawn", context)

    async def announce_vote_result(
        self,
        vote_counts: Dict[str, int],
        eliminated_player: Optional[Dict[str, Any]],
        is_tie: bool = False,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """
        Announce vote result.

        :param vote_counts: Vote counts per player.
        :param eliminated_player: Player eliminated by vote (if any).
        :param is_tie: Whether it was a tie.
        :param stream: Whether to stream.
        :yields: Announcement chunks.
        """
        counts_text = ", ".join([
            f"{seat}号: {count}票"
            for seat, count in vote_counts.items()
        ]) if vote_counts else "无投票"

        highest_text = "无" if is_tie else (
            f"{eliminated_player['seat_number']}号{eliminated_player['name']}"
            if eliminated_player else "无"
        )

        context = {
            "vote_counts": counts_text,
            "highest_vote_player": highest_text,
            "is_tie": is_tie,
        }

        if stream:
            async for chunk in self.announce_stream("vote_result", context):
                yield chunk
        else:
            yield await self.announce("vote_result", context)

    async def announce_game_end(
        self,
        winner_team: str,
        werewolf_players: List[Dict[str, Any]],
        good_players: List[Dict[str, Any]],
        total_days: int,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """
        Announce game end.

        :param winner_team: Winning team name.
        :param werewolf_players: List of werewolf players.
        :param good_players: List of good players.
        :param total_days: Total game days.
        :param stream: Whether to stream.
        :yields: Announcement chunks.
        """
        werewolf_text = ", ".join([
            f"{p['seat_number']}号{p['name']}"
            for p in werewolf_players
        ])

        good_text = ", ".join([
            f"{p['seat_number']}号{p['name']}"
            for p in good_players
        ])

        context = {
            "winner_team": winner_team,
            "werewolf_players": werewolf_text,
            "good_players": good_text,
            "total_days": total_days,
        }

        if stream:
            async for chunk in self.announce_stream("game_end", context):
                yield chunk
        else:
            yield await self.announce("game_end", context)

    async def announce_request_speech(
        self,
        seat_number: int,
        player_name: str,
        is_human: bool = False,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """
        主持人点名玩家发言。

        :param seat_number: 被点名玩家的座位号
        :param player_name: 被点名玩家的名称
        :param is_human: 是否为人类玩家
        :param stream: 是否流式输出
        :yields: 公告片段
        """
        context = {
            "seat_number": seat_number,
            "player_name": player_name,
            "is_human": "是" if is_human else "否",
        }

        if stream:
            async for chunk in self.announce_stream("request_speech", context):
                yield chunk
        else:
            yield await self.announce("request_speech", context)

    async def announce_player_speech_end(
        self,
        current_seat_number: int,
        next_seat_number: Optional[int] = None,
        next_player_name: Optional[str] = None,
        stream: bool = False,
    ) -> str:
        """
        主持人确认玩家发言结束，并过渡到下一位（简短）。

        :param current_seat_number: 刚发言完的玩家座位号
        :param next_seat_number: 下一位发言玩家的座位号（可选）
        :param next_player_name: 下一位发言玩家的名称（可选）
        :param stream: 是否流式输出（默认非流式，因为内容简短）
        :return: 发言结束确认文本
        """
        # 如果没有下一位玩家，使用简单的确认语
        if next_seat_number is None:
            return f"{current_seat_number}号玩家发言结束。"

        context = {
            "current_seat_number": current_seat_number,
            "next_seat_number": next_seat_number,
            "next_player_name": next_player_name or f"玩家{next_seat_number}",
        }

        if stream:
            result = ""
            async for chunk in self.announce_stream("speech_end_transition", context):
                result += chunk
            return result
        else:
            return await self.announce("speech_end_transition", context)
