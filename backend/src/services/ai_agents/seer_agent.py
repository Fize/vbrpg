# -*- coding: utf-8 -*-
"""Seer role AI agent."""

import logging
from typing import Any, Dict, List, Optional

from src.integrations.llm_client import LLMClient
from src.services.ai_agents.base import BaseWerewolfAgent
from src.services.ai_agents.prompts.seer_prompts import (
    SEER_NIGHT_PROMPT,
    SEER_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class SeerAgent(BaseWerewolfAgent):
    """AI agent for seer role."""

    def __init__(
        self,
        player_id: str,
        player_name: str,
        seat_number: int,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize seer agent.

        :param player_id: Unique player identifier.
        :param player_name: Display name.
        :param seat_number: Seat number (1-10).
        :param llm_client: LLM client instance.
        """
        super().__init__(player_id, player_name, seat_number, llm_client)
        # Track check history: [{seat_number, player_name, is_werewolf, day}]
        self.check_history: List[Dict[str, Any]] = []

    @property
    def role_type(self) -> str:
        return "seer"

    @property
    def team(self) -> str:
        return "villager"

    def add_check_result(
        self,
        seat_number: int,
        player_name: str,
        is_werewolf: bool,
        day: int,
    ) -> None:
        """
        Record a check result.

        :param seat_number: Checked player's seat.
        :param player_name: Checked player's name.
        :param is_werewolf: True if the player is a werewolf.
        :param day: Day number when checked.
        """
        result = {
            "seat_number": seat_number,
            "player_name": player_name,
            "is_werewolf": is_werewolf,
            "day": day,
        }
        self.check_history.append(result)

        # Add to known info
        identity = "狼人" if is_werewolf else "好人"
        self.add_known_info({
            "type": "check_result",
            "content": f"第{day}夜查验{seat_number}号{player_name}，结果是{identity}",
        })

        logger.info(
            f"[{self.player_name}] Checked {seat_number}#{player_name}: {identity}"
        )

    def format_check_history(self) -> str:
        """Format check history for prompts."""
        if not self.check_history:
            return "暂无查验记录"

        lines = []
        for check in self.check_history:
            identity = "狼人" if check["is_werewolf"] else "好人"
            lines.append(
                f"第{check['day']}夜：{check['seat_number']}号{check['player_name']} -> {identity}"
            )

        return "\n".join(lines)

    def get_system_prompt(self, game_state: Dict[str, Any]) -> str:
        """Get seer system prompt."""
        formatted = self.format_game_state(game_state)

        return SEER_SYSTEM_PROMPT.format(
            check_history=self.format_check_history(),
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
        Decide who to check at night.

        :param game_state: Current game state.
        :param available_targets: List of checkable players.
        :return: Action decision.
        """
        formatted = self.format_game_state(game_state)

        # Filter out already checked players
        checked_seats = {c["seat_number"] for c in self.check_history}
        unchecked_targets = [
            t for t in available_targets
            if t["seat_number"] not in checked_seats
        ]

        # Format targets
        targets_text = "\n".join([
            f"- {t['seat_number']}号 {t['name']}"
            for t in available_targets
        ])

        # Format unchecked players
        unchecked_text = ", ".join([
            f"{t['seat_number']}号{t['name']}"
            for t in unchecked_targets
        ]) or "所有存活玩家都已查验"

        # Get day number
        day_number = game_state.get("day_number", 1)
        
        # Format speech history section (only for day 2+)
        speech_history = game_state.get("speech_history", "")
        if day_number > 1 and speech_history:
            speech_history_section = f"## 白天发言记录\n{speech_history}"
        else:
            speech_history_section = ""

        prompt = SEER_NIGHT_PROMPT.format(
            day_number=day_number,
            check_history=self.format_check_history(),
            unchecked_players=unchecked_text,
            available_targets=targets_text,
            speech_history_section=speech_history_section,
        )

        messages = [
            {"role": "system", "content": self.get_system_prompt(game_state)},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.llm_client.generate(messages)
            decision = self._parse_json_response(response)

            target = decision.get("target")

            # Normalize and validate target
            normalized_target = self._normalize_seat_number(target)
            valid_seats = {t["seat_number"] for t in available_targets}
            if normalized_target is None or normalized_target not in valid_seats:
                logger.warning(f"[{self.player_name}] Invalid check target '{target}' (normalized: {normalized_target}), using fallback")
                # Prefer unchecked target
                if unchecked_targets:
                    normalized_target = unchecked_targets[0]["seat_number"]
                elif available_targets:
                    normalized_target = available_targets[0]["seat_number"]

            return {
                "action": "check",
                "target": normalized_target,
                "reasoning": decision.get("reasoning", ""),
            }

        except Exception as e:
            logger.error(f"[{self.player_name}] Night action decision failed: {e}")
            # Fallback: check first unchecked player
            if unchecked_targets:
                return {
                    "action": "check",
                    "target": unchecked_targets[0]["seat_number"],
                    "reasoning": "决策失败，随机选择查验目标",
                }
            elif available_targets:
                return {
                    "action": "check",
                    "target": available_targets[0]["seat_number"],
                    "reasoning": "决策失败，随机选择查验目标",
                }
            return {
                "action": "pass",
                "target": None,
                "reasoning": "无可查验目标",
            }

    def get_confirmed_werewolves(self) -> List[int]:
        """Get list of confirmed werewolf seat numbers."""
        return [
            c["seat_number"]
            for c in self.check_history
            if c["is_werewolf"]
        ]

    def get_confirmed_good(self) -> List[int]:
        """Get list of confirmed good player seat numbers."""
        return [
            c["seat_number"]
            for c in self.check_history
            if not c["is_werewolf"]
        ]
