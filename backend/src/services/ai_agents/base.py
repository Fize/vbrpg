# -*- coding: utf-8 -*-
"""Base class for werewolf game AI agents."""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

from src.integrations.llm_client import LLMClient
from src.services.ai_agents.prompts.game_rules import ROLE_NAMES, TEAM_NAMES

logger = logging.getLogger(__name__)


class BaseWerewolfAgent(ABC):
    """
    Base class for werewolf game AI agents.

    Each role (werewolf, seer, witch, hunter, villager) extends this class
    and implements role-specific behavior.
    """

    def __init__(
        self,
        player_id: str,
        player_name: str,
        seat_number: int,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize the AI agent.

        :param player_id: Unique identifier for the player.
        :param player_name: Display name of the player.
        :param seat_number: Seat number (1-10).
        :param llm_client: LLM client for generating responses.
        """
        self.player_id = player_id
        self.player_name = player_name
        self.seat_number = seat_number
        self.llm_client = llm_client or LLMClient()

        # Game state tracking
        self.is_alive = True
        self.known_info: List[Dict[str, Any]] = []
        self.memory: List[Dict[str, Any]] = []
        
        # B17: 用于存储实时上下文更新
        self._current_context: Dict[str, Any] = {}

    @property
    @abstractmethod
    def role_type(self) -> str:
        """Return the role type (e.g., 'werewolf', 'seer')."""
        pass

    @property
    @abstractmethod
    def team(self) -> str:
        """Return the team (e.g., 'werewolf', 'villager')."""
        pass

    @property
    def role_name(self) -> str:
        """Return the Chinese name of the role."""
        return ROLE_NAMES.get(self.role_type, self.role_type)

    @property
    def team_name(self) -> str:
        """Return the Chinese name of the team."""
        return TEAM_NAMES.get(self.team, self.team)

    @abstractmethod
    def get_system_prompt(self, game_state: Dict[str, Any]) -> str:
        """
        Get the system prompt for this agent.

        :param game_state: Current game state.
        :return: System prompt string.
        """
        pass

    def add_known_info(self, info: Dict[str, Any]) -> None:
        """
        Add information to the agent's knowledge.

        :param info: Information dict with type, content, etc.
        """
        self.known_info.append(info)
        logger.debug(f"[{self.player_name}] Added known info: {info.get('type')}")

    def add_memory(self, event: Dict[str, Any]) -> None:
        """
        Add an event to the agent's memory.

        :param event: Event dict with type, day, content, etc.
        """
        self.memory.append(event)

    # =========================================================================
    # B17: 上下文更新方法
    # =========================================================================

    def update_context(
        self,
        speeches: List[Dict[str, Any]],
        host_context: Optional[str] = None,
        game_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        更新 AI Agent 的实时上下文。

        此方法用于在发言轮次中更新 AI 的上下文信息，
        包括本轮已有的玩家发言、主持人公告等。

        :param speeches: 本轮已有的发言列表，每项包含:
            - seat_number: 发言者座位号
            - player_name: 发言者名称
            - content: 发言内容
        :param host_context: 主持人上下文摘要（可选）
        :param game_state: 完整游戏状态（可选）
        """
        self._current_context = {
            "current_round_speeches": speeches or [],
            "host_context": host_context,
            "last_update_time": None,  # 可扩展添加时间戳
        }

        if game_state:
            self._current_context["game_state"] = game_state

        logger.debug(
            f"[{self.player_name}] Context updated with {len(speeches)} speeches"
        )

    def get_current_context(self) -> Dict[str, Any]:
        """
        获取当前上下文。

        :return: 当前上下文字典
        """
        return self._current_context.copy()

    def format_known_info(self) -> str:
        """Format known information for prompts."""
        if not self.known_info:
            return "暂无已知信息"

        lines = []
        for info in self.known_info:
            info_type = info.get("type", "unknown")
            content = info.get("content", "")
            lines.append(f"- [{info_type}] {content}")

        return "\n".join(lines)

    def format_game_state(self, game_state: Dict[str, Any]) -> Dict[str, str]:
        """
        Format game state for use in prompts.

        :param game_state: Raw game state dict.
        :return: Formatted strings dict.
        """
        alive_players = game_state.get("alive_players", [])
        dead_players = game_state.get("dead_players", [])
        day_number = game_state.get("day_number", 1)

        return {
            "day_number": str(day_number),
            "alive_players": ", ".join(
                [f"{p['seat_number']}号{p['name']}" for p in alive_players]
            ) or "无",
            "dead_players": ", ".join(
                [f"{p['seat_number']}号{p['name']}" for p in dead_players]
            ) or "无",
            "known_info": self.format_known_info(),
        }

    async def decide_night_action(
        self,
        game_state: Dict[str, Any],
        available_targets: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Decide the night action for this agent.

        :param game_state: Current game state.
        :param available_targets: List of available targets.
        :return: Action decision dict with action, target, reasoning.
        """
        # Default implementation - override in subclasses
        return {
            "action": "pass",
            "target": None,
            "reasoning": "No night action available for this role",
        }

    async def generate_speech(
        self,
        game_state: Dict[str, Any],
        previous_speeches: List[Dict[str, Any]],
    ) -> str:
        """
        Generate a speech for the discussion phase.

        :param game_state: Current game state.
        :param previous_speeches: List of previous speeches in this round.
        :return: Generated speech text.
        """
        from src.services.ai_agents.prompts.common_prompts import SPEECH_PROMPT

        formatted_state = self.format_game_state(game_state)

        # Format previous speeches
        prev_speeches_text = self._format_previous_speeches(previous_speeches)

        prompt = SPEECH_PROMPT.format(
            role_name=self.role_name,
            team_name=self.team_name,
            seat_number=self.seat_number,
            day_number=formatted_state["day_number"],
            alive_players=formatted_state["alive_players"],
            dead_players=formatted_state["dead_players"],
            previous_speeches=prev_speeches_text,
            known_info=formatted_state["known_info"],
        )

        messages = [
            {"role": "system", "content": self.get_system_prompt(game_state)},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.llm_client.generate(messages)
            # Add to memory
            self.add_memory({
                "type": "speech",
                "day": game_state.get("day_number", 1),
                "content": response,
            })
            return response
        except Exception as e:
            logger.error(f"[{self.player_name}] Speech generation failed: {e}")
            return f"我是{self.seat_number}号，我的发言就到这里。"

    async def generate_speech_stream(
        self,
        game_state: Dict[str, Any],
        previous_speeches: List[Dict[str, Any]],
        current_round_speeches: Optional[List[Dict[str, Any]]] = None,
        host_context: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Generate a speech with streaming output.

        B18 增强：增加了 current_round_speeches 和 host_context 参数，
        使 AI 发言能考虑本轮其他玩家的发言上下文。

        :param game_state: Current game state.
        :param previous_speeches: List of previous speeches (历史发言).
        :param current_round_speeches: 本轮已有发言列表（可选）.
        :param host_context: 主持人上下文摘要（可选）.
        :yields: Chunks of speech text.
        """
        from src.services.ai_agents.prompts.common_prompts import SPEECH_PROMPT

        formatted_state = self.format_game_state(game_state)
        prev_speeches_text = self._format_previous_speeches(previous_speeches)

        # B18: 格式化本轮发言上下文
        current_round_text = ""
        if current_round_speeches:
            current_round_text = self._format_current_round_speeches(current_round_speeches)

        # B18: 添加主持人上下文到提示
        host_info = ""
        if host_context:
            host_info = f"\n\n【主持人提示】\n{host_context}"

        prompt = SPEECH_PROMPT.format(
            role_name=self.role_name,
            team_name=self.team_name,
            seat_number=self.seat_number,
            day_number=formatted_state["day_number"],
            alive_players=formatted_state["alive_players"],
            dead_players=formatted_state["dead_players"],
            previous_speeches=prev_speeches_text,
            known_info=formatted_state["known_info"],
        )

        # B18: 如果有本轮发言，追加到提示中
        if current_round_text:
            prompt += f"\n\n【本轮已有发言】\n{current_round_text}"

        if host_info:
            prompt += host_info

        messages = [
            {"role": "system", "content": self.get_system_prompt(game_state)},
            {"role": "user", "content": prompt},
        ]

        full_content = ""
        try:
            async for chunk in self.llm_client.generate_stream(messages):
                full_content += chunk
                yield chunk

            # Add to memory after complete
            self.add_memory({
                "type": "speech",
                "day": game_state.get("day_number", 1),
                "content": full_content,
            })
        except Exception as e:
            logger.error(f"[{self.player_name}] Speech stream failed: {e}")
            fallback = f"我是{self.seat_number}号，我的发言就到这里。"
            yield fallback

    def _format_current_round_speeches(
        self,
        speeches: List[Dict[str, Any]],
    ) -> str:
        """
        格式化本轮发言列表。

        :param speeches: 本轮发言列表
        :return: 格式化的文本
        """
        if not speeches:
            return "暂无本轮发言"

        lines = []
        for speech in speeches:
            speaker = speech.get("player_name", "未知")
            seat = speech.get("seat_number", "?")
            content = speech.get("content", "")
            lines.append(f"【{seat}号 {speaker}】：{content}")

        return "\n\n".join(lines)

    async def decide_vote(
        self,
        game_state: Dict[str, Any],
        speech_summary: str,
        voteable_players: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Decide who to vote for.

        :param game_state: Current game state.
        :param speech_summary: Summary of discussion speeches.
        :param voteable_players: List of players that can be voted.
        :return: Vote decision dict with action, target, reasoning.
        """
        from src.services.ai_agents.prompts.common_prompts import (
            VOTE_PROMPT,
            VOTING_STRATEGIES,
        )

        formatted_state = self.format_game_state(game_state)
        voting_strategy = VOTING_STRATEGIES.get(self.role_type, "根据场上信息做出判断")

        # Format voteable players
        voteable_text = "\n".join([
            f"- {p['seat_number']}号 {p['name']}"
            for p in voteable_players
        ])

        prompt = VOTE_PROMPT.format(
            role_name=self.role_name,
            team_name=self.team_name,
            seat_number=self.seat_number,
            day_number=formatted_state["day_number"],
            alive_players=formatted_state["alive_players"],
            speech_summary=speech_summary,
            known_info=formatted_state["known_info"],
            voteable_players=voteable_text,
            voting_strategy=voting_strategy,
        )

        messages = [
            {"role": "system", "content": self.get_system_prompt(game_state)},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.llm_client.generate(messages)
            decision = self._parse_json_response(response)

            # Validate decision
            if decision.get("action") not in ["vote", "abstain"]:
                decision["action"] = "abstain"
                decision["target"] = None

            # Add to memory
            self.add_memory({
                "type": "vote",
                "day": game_state.get("day_number", 1),
                "target": decision.get("target"),
                "reasoning": decision.get("reasoning", ""),
            })

            return decision
        except Exception as e:
            logger.error(f"[{self.player_name}] Vote decision failed: {e}")
            return {
                "action": "abstain",
                "target": None,
                "reasoning": "决策失败，选择弃票",
            }

    def _format_previous_speeches(
        self,
        speeches: List[Dict[str, Any]],
    ) -> str:
        """Format previous speeches for prompts."""
        if not speeches:
            return "暂无发言"

        lines = []
        for speech in speeches:
            speaker = speech.get("player_name", "未知")
            seat = speech.get("seat_number", "?")
            content = speech.get("content", "")
            lines.append(f"【{seat}号 {speaker}】：{content}")

        return "\n\n".join(lines)

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response from LLM."""
        # Try to extract JSON from response
        try:
            # Remove markdown code blocks if present
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end]
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end]

            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return {}

    def set_dead(self) -> None:
        """Mark the agent as dead."""
        self.is_alive = False
        logger.info(f"[{self.player_name}] has died")
