# -*- coding: utf-8 -*-
"""Hunter role AI agent."""

import logging
from typing import Any, Dict, List, Optional

from src.integrations.llm_client import LLMClient
from src.services.ai_agents.base import BaseWerewolfAgent
from src.services.ai_agents.prompts.hunter_prompts import (
    HUNTER_SHOOT_PROMPT,
    HUNTER_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class HunterAgent(BaseWerewolfAgent):
    """AI agent for hunter role."""

    def __init__(
        self,
        player_id: str,
        player_name: str,
        seat_number: int,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize hunter agent.

        :param player_id: Unique player identifier.
        :param player_name: Display name.
        :param seat_number: Seat number (1-10).
        :param llm_client: LLM client instance.
        """
        super().__init__(player_id, player_name, seat_number, llm_client)
        self.can_shoot = True  # Whether can shoot on death

    @property
    def role_type(self) -> str:
        return "hunter"

    @property
    def team(self) -> str:
        return "villager"

    def disable_shoot(self) -> None:
        """Disable shooting ability (e.g., when poisoned by witch)."""
        self.can_shoot = False
        logger.info(f"[{self.player_name}] Shooting disabled")

    def get_system_prompt(self, game_state: Dict[str, Any]) -> str:
        """Get hunter system prompt."""
        formatted = self.format_game_state(game_state)

        # Analyze suspicious players based on known info
        suspicious_text = "无特别可疑玩家"
        for info in self.known_info:
            if info.get("type") == "suspicious":
                suspicious_text = info.get("content", suspicious_text)
                break

        return HUNTER_SYSTEM_PROMPT.format(
            day_number=formatted["day_number"],
            alive_players=formatted["alive_players"],
            dead_players=formatted["dead_players"],
            suspicious_players=suspicious_text,
        )

    async def decide_night_action(
        self,
        game_state: Dict[str, Any],
        available_targets: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Hunter has no night action.

        :param game_state: Current game state.
        :param available_targets: List of available targets.
        :return: Pass action.
        """
        return {
            "action": "pass",
            "target": None,
            "reasoning": "猎人夜间无行动",
        }

    async def decide_shoot(
        self,
        game_state: Dict[str, Any],
        death_reason: str,
        available_targets: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Decide whether and who to shoot on death.

        :param game_state: Current game state.
        :param death_reason: How the hunter died.
        :param available_targets: List of alive players that can be shot.
        :return: Shoot decision.
        """
        # Check if can shoot
        can_shoot_now = self.can_shoot and death_reason != "poisoned"

        if not can_shoot_now:
            return {
                "action": "no_shoot",
                "target": None,
                "reasoning": "被女巫毒死，无法开枪",
            }

        if not available_targets:
            return {
                "action": "no_shoot",
                "target": None,
                "reasoning": "无可开枪目标",
            }

        formatted = self.format_game_state(game_state)

        # Format targets
        targets_text = "\n".join([
            f"- {t['seat_number']}号 {t['name']}"
            for t in available_targets
        ])

        # Get day number
        day_number = game_state.get("day_number", 1)
        
        # Format speech history section (only if available)
        speech_history = game_state.get("speech_history", "")
        if speech_history:
            speech_history_section = f"## 白天发言记录\n{speech_history}"
        else:
            speech_history_section = ""

        prompt = HUNTER_SHOOT_PROMPT.format(
            death_reason=death_reason,
            day_number=day_number,
            can_shoot="是" if can_shoot_now else "否",
            alive_players=formatted["alive_players"],
            available_targets=targets_text,
            speech_history_section=speech_history_section,
            known_info=formatted["known_info"],
        )

        messages = [
            {"role": "system", "content": self.get_system_prompt(game_state)},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.llm_client.generate(messages)
            decision = self._parse_json_response(response)

            action = decision.get("action", "shoot")
            target = decision.get("target")

            if action == "no_shoot":
                return {
                    "action": "no_shoot",
                    "target": None,
                    "reasoning": decision.get("reasoning", "选择不开枪"),
                }

            # Normalize and validate target
            normalized_target = self._normalize_seat_number(target)
            valid_seats = {t["seat_number"] for t in available_targets}
            if normalized_target is None or normalized_target not in valid_seats:
                logger.warning(f"[{self.player_name}] Invalid shoot target '{target}' (normalized: {normalized_target}), using fallback")
                # Pick first available target
                normalized_target = available_targets[0]["seat_number"]

            return {
                "action": "shoot",
                "target": normalized_target,
                "reasoning": decision.get("reasoning", ""),
            }

        except Exception as e:
            logger.error(f"[{self.player_name}] Shoot decision failed: {e}")
            # Fallback: shoot first available target
            if available_targets:
                return {
                    "action": "shoot",
                    "target": available_targets[0]["seat_number"],
                    "reasoning": "决策失败，随机选择开枪目标",
                }
            return {
                "action": "no_shoot",
                "target": None,
                "reasoning": "决策失败，无可开枪目标",
            }
