# -*- coding: utf-8 -*-
"""Werewolf role AI agent."""

import logging
from typing import Any, Dict, List, Optional

from src.integrations.llm_client import LLMClient
from src.services.ai_agents.base import BaseWerewolfAgent
from src.services.ai_agents.prompts.werewolf_prompts import (
    WEREWOLF_NIGHT_PROMPT,
    WEREWOLF_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class WerewolfAgent(BaseWerewolfAgent):
    """AI agent for werewolf role."""

    def __init__(
        self,
        player_id: str,
        player_name: str,
        seat_number: int,
        teammates: Optional[List[Dict[str, Any]]] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize werewolf agent.

        :param player_id: Unique player identifier.
        :param player_name: Display name.
        :param seat_number: Seat number (1-10).
        :param teammates: List of werewolf teammate info.
        :param llm_client: LLM client instance.
        """
        super().__init__(player_id, player_name, seat_number, llm_client)
        self.teammates = teammates or []

    @property
    def role_type(self) -> str:
        return "werewolf"

    @property
    def team(self) -> str:
        return "werewolf"

    def set_teammates(self, teammates: List[Dict[str, Any]]) -> None:
        """
        Set werewolf teammates.

        :param teammates: List of teammate info dicts.
        """
        self.teammates = teammates
        # Add to known info
        for mate in teammates:
            self.add_known_info({
                "type": "teammate",
                "content": f"{mate['seat_number']}号{mate['name']}是狼人队友",
            })

    def get_system_prompt(self, game_state: Dict[str, Any]) -> str:
        """Get werewolf system prompt."""
        formatted = self.format_game_state(game_state)

        # Format teammates
        teammates_text = ", ".join([
            f"{t['seat_number']}号{t['name']}"
            for t in self.teammates
            if t.get("is_alive", True)
        ]) or "无存活队友"

        return WEREWOLF_SYSTEM_PROMPT.format(
            teammates=teammates_text,
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
        Decide who to kill at night.

        :param game_state: Current game state.
        :param available_targets: List of killable players.
        :return: Action decision.
        """
        formatted = self.format_game_state(game_state)

        # Filter out teammates from targets
        non_teammate_ids = {t.get("player_id") for t in self.teammates}
        good_targets = [
            t for t in available_targets
            if t.get("player_id") not in non_teammate_ids
        ]

        # Format targets
        targets_text = "\n".join([
            f"- {t['seat_number']}号 {t['name']}"
            for t in available_targets
        ])

        # Format alive good players (estimated)
        alive_good_text = ", ".join([
            f"{t['seat_number']}号{t['name']}"
            for t in good_targets
        ])

        # Format teammates
        teammates_text = ", ".join([
            f"{t['seat_number']}号{t['name']}"
            for t in self.teammates
            if t.get("is_alive", True)
        ])

        prompt = WEREWOLF_NIGHT_PROMPT.format(
            alive_good_players=alive_good_text,
            teammates=teammates_text,
            known_info=formatted["known_info"],
            available_targets=targets_text,
        )

        messages = [
            {"role": "system", "content": self.get_system_prompt(game_state)},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.llm_client.generate(messages)
            decision = self._parse_json_response(response)

            # Validate decision
            action = decision.get("action", "kill")
            target = decision.get("target")

            if action == "empty_kill":
                return {
                    "action": "empty_kill",
                    "target": None,
                    "reasoning": decision.get("reasoning", "选择空刀"),
                }

            # Validate target
            valid_seats = {str(t["seat_number"]) for t in available_targets}
            if str(target) not in valid_seats:
                # Pick first non-teammate target
                if good_targets:
                    target = good_targets[0]["seat_number"]
                elif available_targets:
                    target = available_targets[0]["seat_number"]

            return {
                "action": "kill",
                "target": target,
                "reasoning": decision.get("reasoning", ""),
            }

        except Exception as e:
            logger.error(f"[{self.player_name}] Night action decision failed: {e}")
            # Fallback: kill first non-teammate
            if good_targets:
                return {
                    "action": "kill",
                    "target": good_targets[0]["seat_number"],
                    "reasoning": "决策失败，随机选择目标",
                }
            return {
                "action": "empty_kill",
                "target": None,
                "reasoning": "决策失败，选择空刀",
            }
