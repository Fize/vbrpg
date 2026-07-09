# -*- coding: utf-8 -*-
"""Hunter role AI agent."""

import logging
from typing import Any, Dict, List, Optional

from src.games.base.agent import BaseGameAgent
from src.games.werewolf.prompts.hunter import (
    HUNTER_SHOOT_PROMPT,
    HUNTER_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class HunterAgent(BaseGameAgent):
    """AI agent for hunter role."""

    def __init__(
        self,
        player_id: str,
        player_name: str,
        seat_number: int,
        personality: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize hunter agent.

        :param player_id: Unique player identifier.
        :param player_name: Display name.
        :param seat_number: Seat number (1-10).
        :param personality: Personality traits for the agent.
        """
        super().__init__(player_id, player_name, seat_number, personality)
        self.can_shoot = True
        self.known_info: List[Dict[str, Any]] = []

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
        """Get hunter system prompt."""
        alive_players = game_state.get("alive_players", [])
        dead_players = game_state.get("dead_players", [])
        day_number = game_state.get("day_number", 1)

        alive_text = ", ".join(
            [f"{p['seat_number']}号{p['name']}" for p in alive_players]
        ) or "无"
        dead_text = ", ".join(
            [f"{p['seat_number']}号{p['name']}" for p in dead_players]
        ) or "无"

        suspicious_text = "无特别可疑玩家"
        for info in self.known_info:
            if info.get("type") == "suspicious":
                suspicious_text = info.get("content", suspicious_text)
                break

        speech_history = game_state.get("speech_history", "")
        speech_history_section = f"## 白天发言记录\n{speech_history}" if day_number > 1 and speech_history else ""

        personality_section = self._build_personality_section()
        if personality_section:
            personality_section = f"\n\n## 你的性格特征\n{personality_section}\n请用符合你性格特征的方式思考和发言。\n"

        return HUNTER_SYSTEM_PROMPT.format(
            day_number=day_number,
            alive_players=alive_text,
            dead_players=dead_text,
            suspicious_players=suspicious_text,
            speech_history_section=speech_history_section,
        ) + personality_section

    async def decide_night_action(
        self,
        game_state: Dict[str, Any],
        available_targets: List[Dict[str, Any]],
        llm_client=None,
    ) -> Dict[str, Any]:
        """
        Hunter has no night action.

        :param game_state: Current game state.
        :param available_targets: List of available targets.
        :param llm_client: LLM client for generating responses.
        :return: Pass action.
        """
        return {
            "action": "pass",
            "target": None,
            "reasoning": "猎人夜间无行动",
        }

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

    async def decide_shoot(
        self,
        game_state: Dict[str, Any],
        death_reason: str,
        available_targets: List[Dict[str, Any]],
        llm_client=None,
    ) -> Dict[str, Any]:
        """
        Decide whether and who to shoot on death.

        :param game_state: Current game state.
        :param death_reason: How the hunter died.
        :param available_targets: List of alive players that can be shot.
        :param llm_client: LLM client for generating responses.
        :return: Shoot decision.
        """
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

        alive_players = game_state.get("alive_players", [])
        day_number = game_state.get("day_number", 1)

        alive_text = ", ".join(
            [f"{p['seat_number']}号{p['name']}" for p in alive_players]
        ) or "无"

        targets_text = "\n".join([
            f"- {t['seat_number']}号 {t['name']}"
            for t in available_targets
        ])

        speech_history = game_state.get("speech_history", "")
        if speech_history:
            speech_history_section = f"## 白天发言记录\n{speech_history}"
        else:
            speech_history_section = ""

        prompt = HUNTER_SHOOT_PROMPT.format(
            death_reason=death_reason,
            day_number=day_number,
            can_shoot="是" if can_shoot_now else "否",
            alive_players=alive_text,
            available_targets=targets_text,
            speech_history_section=speech_history_section,
            known_info=self.format_known_info(),
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

            action = decision.get("action", "shoot")
            target = decision.get("target")

            if action == "no_shoot":
                return {
                    "action": "no_shoot",
                    "target": None,
                    "reasoning": decision.get("reasoning", "选择不开枪"),
                }

            normalized_target = self._normalize_seat_number(target)
            valid_seats = {t["seat_number"] for t in available_targets}
            if normalized_target is None or normalized_target not in valid_seats:
                logger.warning(f"[{self.player_name}] Invalid shoot target '{target}', using fallback")
                normalized_target = available_targets[0]["seat_number"]

            return {
                "action": "shoot",
                "target": normalized_target,
                "reasoning": decision.get("reasoning", ""),
            }

        except Exception as e:
            logger.error(f"[{self.player_name}] Shoot decision failed: {e}")
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
