# -*- coding: utf-8 -*-
"""Witch role AI agent."""

import logging
from typing import Any, Dict, List, Optional

from src.integrations.llm_client import LLMClient
from src.services.ai_agents.base import BaseWerewolfAgent
from src.services.ai_agents.prompts.witch_prompts import (
    WITCH_NIGHT_PROMPT,
    WITCH_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class WitchAgent(BaseWerewolfAgent):
    """AI agent for witch role."""

    def __init__(
        self,
        player_id: str,
        player_name: str,
        seat_number: int,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize witch agent.

        :param player_id: Unique player identifier.
        :param player_name: Display name.
        :param seat_number: Seat number (1-10).
        :param llm_client: LLM client instance.
        """
        super().__init__(player_id, player_name, seat_number, llm_client)
        # Potion status
        self.has_antidote = True  # 解药
        self.has_poison = True    # 毒药

    @property
    def role_type(self) -> str:
        return "witch"

    @property
    def team(self) -> str:
        return "villager"

    def use_antidote(self) -> bool:
        """
        Use the antidote.

        :return: True if successful, False if already used.
        """
        if self.has_antidote:
            self.has_antidote = False
            logger.info(f"[{self.player_name}] Used antidote")
            return True
        return False

    def use_poison(self) -> bool:
        """
        Use the poison.

        :return: True if successful, False if already used.
        """
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

    def get_system_prompt(self, game_state: Dict[str, Any]) -> str:
        """Get witch system prompt."""
        formatted = self.format_game_state(game_state)
        status = self.get_potion_status()

        return WITCH_SYSTEM_PROMPT.format(
            antidote_status=status["antidote"],
            poison_status=status["poison"],
            day_number=formatted["day_number"],
            alive_players=formatted["alive_players"],
            dead_players=formatted["dead_players"],
        )

    async def decide_night_action(
        self,
        game_state: Dict[str, Any],
        available_targets: List[Dict[str, Any]],
        killed_player: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Decide night action (save or poison).

        :param game_state: Current game state.
        :param available_targets: List of players that can be poisoned.
        :param killed_player: Player killed by werewolves tonight (if any).
        :return: Action decision.
        """
        formatted = self.format_game_state(game_state)
        status = self.get_potion_status()
        is_first_night = game_state.get("day_number", 1) == 1

        # Format killed player
        killed_text = "无人被杀" if not killed_player else (
            f"{killed_player['seat_number']}号{killed_player['name']}"
        )

        # Determine available actions
        actions = []
        if self.has_antidote and killed_player:
            # Check if can self-save
            can_self_save = killed_player.get("seat_number") == self.seat_number
            if can_self_save and is_first_night:
                actions.append("- save: 使用解药救自己（首夜可自救）")
            elif not can_self_save:
                actions.append(f"- save: 使用解药救{killed_text}")
        if self.has_poison:
            actions.append("- poison: 使用毒药毒杀一名玩家")
        actions.append("- pass: 不使用药物")

        actions_text = "\n".join(actions)

        # Format targets for poison
        targets_text = "\n".join([
            f"- {t['seat_number']}号 {t['name']}"
            for t in available_targets
        ])

        prompt = WITCH_NIGHT_PROMPT.format(
            antidote_status=status["antidote"],
            poison_status=status["poison"],
            killed_player=killed_text,
            is_first_night="是" if is_first_night else "否",
            available_actions=actions_text + "\n\n可毒杀的目标：\n" + targets_text,
        )

        messages = [
            {"role": "system", "content": self.get_system_prompt(game_state)},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.llm_client.generate(messages)
            decision = self._parse_json_response(response)

            action = decision.get("action", "pass")
            target = decision.get("target")

            # Validate action
            if action == "save":
                if not self.has_antidote or not killed_player:
                    action = "pass"
                    target = None
                else:
                    # Self-save check
                    if (
                        killed_player.get("seat_number") == self.seat_number
                        and not is_first_night
                    ):
                        # Cannot self-save after first night
                        action = "pass"
                        target = None
                    else:
                        target = killed_player.get("seat_number")

            elif action == "poison":
                if not self.has_poison:
                    action = "pass"
                    target = None
                else:
                    # Validate target
                    valid_seats = {str(t["seat_number"]) for t in available_targets}
                    if str(target) not in valid_seats:
                        action = "pass"
                        target = None

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

        # For now, always self-save on first night if possible
        # Could be enhanced with LLM decision
        return True
