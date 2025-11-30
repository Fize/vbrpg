# -*- coding: utf-8 -*-
"""Villager role AI agent."""

import logging
from typing import Any, Dict, List, Optional

from src.integrations.llm_client import LLMClient
from src.services.ai_agents.base import BaseWerewolfAgent
from src.services.ai_agents.prompts.villager_prompts import VILLAGER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class VillagerAgent(BaseWerewolfAgent):
    """AI agent for villager role."""

    def __init__(
        self,
        player_id: str,
        player_name: str,
        seat_number: int,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize villager agent.

        :param player_id: Unique player identifier.
        :param player_name: Display name.
        :param seat_number: Seat number (1-10).
        :param llm_client: LLM client instance.
        """
        super().__init__(player_id, player_name, seat_number, llm_client)

    @property
    def role_type(self) -> str:
        return "villager"

    @property
    def team(self) -> str:
        return "villager"

    def get_system_prompt(self, game_state: Dict[str, Any]) -> str:
        """Get villager system prompt."""
        formatted = self.format_game_state(game_state)

        return VILLAGER_SYSTEM_PROMPT.format(
            day_number=formatted["day_number"],
            alive_players=formatted["alive_players"],
            dead_players=formatted["dead_players"],
        )

    async def decide_night_action(
        self,
        game_state: Dict[str, Any],
        available_targets: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Villager has no night action.

        :param game_state: Current game state.
        :param available_targets: List of available targets.
        :return: Pass action.
        """
        return {
            "action": "pass",
            "target": None,
            "reasoning": "村民夜间无行动",
        }
