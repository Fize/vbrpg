# -*- coding: utf-8 -*-
"""Seer role AI agent."""

import logging
from typing import Any, Dict, List, Optional

from src.games.base.agent import BaseGameAgent
from src.games.werewolf.prompts.seer import (
    SEER_NIGHT_PROMPT,
    SEER_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class SeerAgent(BaseGameAgent):
    """AI agent for seer role."""

    def __init__(
        self,
        player_id: str,
        player_name: str,
        seat_number: int,
        personality: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize seer agent.

        :param player_id: Unique player identifier.
        :param player_name: Display name.
        :param seat_number: Seat number (1-10).
        :param personality: Personality traits for the agent.
        """
        super().__init__(player_id, player_name, seat_number, personality)
        self.check_history: List[Dict[str, Any]] = []
        self.known_info: List[Dict[str, Any]] = []

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
        identity = "狼人" if is_werewolf else "好人"
        self.known_info.append({
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

    def _build_personality_section(self) -> str:
        """Build personality description section for system prompt."""
        if not self.personality:
            return ""
        traits = []
        for key, value in self.personality.items():
            traits.append(f"- {key}: {value}")
        return "\n".join(traits)

    def get_system_prompt(self, game_state: Dict[str, Any]) -> str:
        """Get seer system prompt."""
        alive_players = game_state.get("alive_players", [])
        dead_players = game_state.get("dead_players", [])
        day_number = game_state.get("day_number", 1)

        alive_text = ", ".join(
            [f"{p['seat_number']}号{p['name']}" for p in alive_players]
        ) or "无"
        dead_text = ", ".join(
            [f"{p['seat_number']}号{p['name']}" for p in dead_players]
        ) or "无"

        personality_section = self._build_personality_section()
        if personality_section:
            personality_section = f"\n\n## 你的性格特征\n{personality_section}\n请用符合你性格特征的方式思考和发言。\n"

        return SEER_SYSTEM_PROMPT.format(
            check_history=self.format_check_history(),
            day_number=day_number,
            alive_players=alive_text,
            dead_players=dead_text,
        ) + personality_section

    def _normalize_seat_number(self, value: Any) -> Optional[int]:
        """Normalize different seat representations returned by LLMs into integers."""
        import re
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, dict):
            for key in ("seat_number", "seat", "target"):
                if key in value:
                    return self._normalize_seat_number(value[key])
        if isinstance(value, str):
            digits = re.search(r"\d+", value)
            if digits:
                return int(digits.group())
        return None

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response from LLM."""
        import json
        try:
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

    async def decide_night_action(
        self,
        game_state: Dict[str, Any],
        available_targets: List[Dict[str, Any]],
        llm_client=None,
    ) -> Dict[str, Any]:
        """
        Decide who to check at night.

        :param game_state: Current game state.
        :param available_targets: List of checkable players.
        :param llm_client: LLM client for generating responses.
        :return: Action decision.
        """
        day_number = game_state.get("day_number", 1)

        checked_seats = {c["seat_number"] for c in self.check_history}
        unchecked_targets = [
            t for t in available_targets
            if t["seat_number"] not in checked_seats
        ]

        targets_text = "\n".join([
            f"- {t['seat_number']}号 {t['name']}"
            for t in available_targets
        ])

        unchecked_text = ", ".join([
            f"{t['seat_number']}号{t['name']}"
            for t in unchecked_targets
        ]) or "所有存活玩家都已查验"

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

        if llm_client is None:
            from src.llm import LLMClient
            llm_client = LLMClient()

        try:
            response = await llm_client.generate(messages)
            decision = self._parse_json_response(response)

            target = decision.get("target")
            normalized_target = self._normalize_seat_number(target)
            valid_seats = {t["seat_number"] for t in available_targets}
            if normalized_target is None or normalized_target not in valid_seats:
                logger.warning(f"[{self.player_name}] Invalid check target '{target}' (normalized: {normalized_target}), using fallback")
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
