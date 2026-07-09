# -*- coding: utf-8 -*-
"""Villager role AI agent."""

import logging
from typing import Any, Dict, List, Optional

from src.games.base.agent import BaseGameAgent
from src.games.werewolf.prompts.villager import VILLAGER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class VillagerAgent(BaseGameAgent):
    """AI agent for villager role."""

    def __init__(
        self,
        player_id: str,
        player_name: str,
        seat_number: int,
        personality: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize villager agent.

        :param player_id: Unique player identifier.
        :param player_name: Display name.
        :param seat_number: Seat number (1-10).
        :param personality: Personality traits for the agent.
        """
        super().__init__(player_id, player_name, seat_number, personality)
        self.known_info: List[Dict[str, Any]] = []

    @property
    def role_type(self) -> str:
        return "villager"

    @property
    def team(self) -> str:
        return "villager"

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

    def _build_personality_section(self) -> str:
        """Build personality description section for system prompt."""
        if not self.personality:
            return ""
        traits = []
        for key, value in self.personality.items():
            traits.append(f"- {key}: {value}")
        return "\n".join(traits)

    def get_system_prompt(self, game_state: Dict[str, Any]) -> str:
        """Get villager system prompt."""
        alive_players = game_state.get("alive_players", [])
        dead_players = game_state.get("dead_players", [])
        day_number = game_state.get("day_number", 1)

        alive_text = ", ".join(
            [f"{p['seat_number']}号{p['name']}" for p in alive_players]
        ) or "无"
        dead_text = ", ".join(
            [f"{p['seat_number']}号{p['name']}" for p in dead_players]
        ) or "无"

        speech_history = game_state.get("speech_history", "")
        speech_history_section = f"## 白天发言记录\n{speech_history}" if day_number > 1 and speech_history else ""

        personality_section = self._build_personality_section()
        if personality_section:
            personality_section = f"\n\n## 你的性格特征\n{personality_section}\n请用符合你性格特征的方式思考和发言。\n"

        return VILLAGER_SYSTEM_PROMPT.format(
            day_number=day_number,
            alive_players=alive_text,
            dead_players=dead_text,
            speech_history_section=speech_history_section,
        ) + personality_section

    async def decide_night_action(
        self,
        game_state: Dict[str, Any],
        available_targets: List[Dict[str, Any]],
        llm_client=None,
    ) -> Dict[str, Any]:
        """
        Villager has no night action.

        :param game_state: Current game state.
        :param available_targets: List of available targets.
        :param llm_client: LLM client for generating responses.
        :return: Pass action.
        """
        return {
            "action": "pass",
            "target": None,
            "reasoning": "村民夜间无行动",
        }
