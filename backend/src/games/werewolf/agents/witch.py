# -*- coding: utf-8 -*-
"""Witch role AI agent."""

import logging
from typing import Any, Dict, List, Optional

from src.games.base.agent import BaseGameAgent
from src.games.werewolf.prompts.witch import (
    WITCH_LAST_WORDS_SYSTEM_PROMPT,
    WITCH_NIGHT_PROMPT,
    WITCH_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class WitchAgent(BaseGameAgent):
    """AI agent for witch role."""

    def __init__(
        self,
        player_id: str,
        player_name: str,
        seat_number: int,
        personality: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize witch agent.

        :param player_id: Unique player identifier.
        :param player_name: Display name.
        :param seat_number: Seat number (1-10).
        :param personality: Personality traits for the agent.
        """
        super().__init__(player_id, player_name, seat_number, personality)
        self.has_antidote = True
        self.has_poison = True
        self.known_info: List[Dict[str, Any]] = []

    @property
    def role_type(self) -> str:
        return "witch"

    @property
    def team(self) -> str:
        return "villager"

    def use_antidote(self) -> bool:
        """Use the antidote."""
        if self.has_antidote:
            self.has_antidote = False
            logger.info(f"[{self.player_name}] Used antidote")
            return True
        return False

    def use_poison(self) -> bool:
        """Use the poison."""
        if self.has_poison:
            self.has_poison = False
            logger.info(f"[{self.player_name}] Used poison")
            return True
        return False

    def get_potion_status(self) -> Dict[str, str]:
        """Get current potion status."""
        return {
            "antidote": "有" if self.has_antidote else "已使用",
            "poison": "有" if self.has_poison else "已使用",
        }

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
        """Get witch system prompt."""
        alive_players = game_state.get("alive_players", [])
        dead_players = game_state.get("dead_players", [])
        day_number = game_state.get("day_number", 1)

        alive_text = ", ".join(
            [f"{p['seat_number']}号{p['name']}" for p in alive_players]
        ) or "无"
        dead_text = ", ".join(
            [f"{p['seat_number']}号{p['name']}" for p in dead_players]
        ) or "无"

        status = self.get_potion_status()

        speech_history = game_state.get("speech_history", "")
        speech_history_section = f"## 白天发言记录\n{speech_history}" if day_number > 1 and speech_history else ""

        personality_section = self._build_personality_section()
        if personality_section:
            personality_section = f"\n\n## 你的性格特征\n{personality_section}\n请用符合你性格特征的方式思考和发言。\n"

        return WITCH_SYSTEM_PROMPT.format(
            antidote_status=status["antidote"],
            poison_status=status["poison"],
            day_number=day_number,
            alive_players=alive_text,
            dead_players=dead_text,
            speech_history_section=speech_history_section,
        ) + personality_section

    def get_last_words_system_prompt(self, game_state: Dict[str, Any]) -> str:
        """Get witch system prompt for last words (without potion status)."""
        alive_players = game_state.get("alive_players", [])
        dead_players = game_state.get("dead_players", [])
        day_number = game_state.get("day_number", 1)

        alive_text = ", ".join(
            [f"{p['seat_number']}号{p['name']}" for p in alive_players]
        ) or "无"
        dead_text = ", ".join(
            [f"{p['seat_number']}号{p['name']}" for p in dead_players]
        ) or "无"

        return WITCH_LAST_WORDS_SYSTEM_PROMPT.format(
            day_number=day_number,
            alive_players=alive_text,
            dead_players=dead_text,
        )

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
        killed_player: Optional[Dict[str, Any]] = None,
        llm_client=None,
    ) -> Dict[str, Any]:
        """
        Decide night action (save or poison).

        :param game_state: Current game state.
        :param available_targets: List of players that can be poisoned.
        :param killed_player: Player killed by werewolves tonight (if any).
        :param llm_client: LLM client for generating responses.
        :return: Action decision.
        """
        status = self.get_potion_status()
        is_first_night = game_state.get("day_number", 1) == 1

        if not killed_player:
            killed_text = "无人被杀"
        elif killed_player.get("seat_number") == self.seat_number:
            killed_text = f"{killed_player['seat_number']}号{killed_player['name']}（就是你自己）"
        else:
            killed_text = f"{killed_player['seat_number']}号{killed_player['name']}"

        actions = []
        if self.has_antidote and killed_player:
            can_self_save = killed_player.get("seat_number") == self.seat_number
            if can_self_save and is_first_night:
                actions.append("- save: 使用解药救自己（首夜可自救）")
            elif not can_self_save:
                actions.append(f"- save: 使用解药救{killed_text}")
        if self.has_poison:
            actions.append("- poison: 使用毒药毒杀一名玩家")
        actions.append("- pass: 不使用药物")

        actions_text = "\n".join(actions)

        targets_text = "\n".join([
            f"- {t['seat_number']}号 {t['name']}"
            for t in available_targets
        ])

        speech_history = game_state.get("speech_history", "")
        speech_history_section = f"## 白天发言记录\n{speech_history}" if not is_first_night and speech_history else ""

        prompt = WITCH_NIGHT_PROMPT.format(
            antidote_status=status["antidote"],
            poison_status=status["poison"],
            killed_player=killed_text,
            is_first_night="是" if is_first_night else "否",
            available_actions=actions_text + "\n\n可毒杀的目标：\n" + targets_text,
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

            action = decision.get("action", "pass")
            target = decision.get("target")

            if action == "save":
                if not self.has_antidote or not killed_player:
                    action = "pass"
                    target = None
                elif (
                    killed_player.get("seat_number") == self.seat_number
                    and not is_first_night
                ):
                    action = "pass"
                    target = None
                else:
                    target = killed_player.get("seat_number")

            elif action == "poison":
                if not self.has_poison:
                    action = "pass"
                    target = None
                else:
                    normalized_target = self._normalize_seat_number(target)
                    valid_seats = {t["seat_number"] for t in available_targets}
                    if normalized_target is None or normalized_target not in valid_seats:
                        logger.warning(f"[{self.player_name}] Invalid poison target '{target}', not poisoning")
                        action = "pass"
                        target = None
                    else:
                        target = normalized_target
            else:
                action = "pass"
                target = None

            return {
                "action": action,
                "target": target,
                "reasoning": decision.get("reasoning", ""),
            }

        except Exception as e:
            logger.error(f"[{self.player_name}] Night action decision failed: {e}")
            return {
                "action": "pass",
                "target": None,
                "reasoning": "决策失败，选择不使用药物",
            }

    async def decide_self_save(
        self,
        game_state: Dict[str, Any],
    ) -> bool:
        """
        Quick decision for self-save on first night.

        :param game_state: Current game state.
        :return: True to use antidote on self.
        """
        is_first_night = game_state.get("day_number", 1) == 1
        if not self.has_antidote or not is_first_night:
            return False
        return True
