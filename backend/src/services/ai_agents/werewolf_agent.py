# -*- coding: utf-8 -*-
"""Werewolf role AI agent."""

import logging
from typing import Any, Dict, List, Optional

from src.integrations.llm_client import LLMClient
from src.services.ai_agents.base import BaseWerewolfAgent
from src.services.ai_agents.prompts.werewolf_prompts import (
    WEREWOLF_NIGHT_PROMPT,
    WEREWOLF_NIGHT_DISCUSS_PROMPT,
    WEREWOLF_NIGHT_FINAL_DECISION_PROMPT,
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

            # Normalize and validate target
            normalized_target = self._normalize_seat_number(target)
            valid_seats = {t["seat_number"] for t in available_targets}
            if normalized_target is None or normalized_target not in valid_seats:
                # Pick first non-teammate target
                logger.warning(f"[{self.player_name}] Invalid kill target '{target}' (normalized: {normalized_target}), using fallback")
                if good_targets:
                    normalized_target = good_targets[0]["seat_number"]
                elif available_targets:
                    normalized_target = available_targets[0]["seat_number"]

            return {
                "action": "kill",
                "target": normalized_target,
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

    async def discuss_night_target(
        self,
        game_state: Dict[str, Any],
        available_targets: List[Dict[str, Any]],
        previous_opinions: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        在狼人讨论阶段发表击杀意见。

        :param game_state: 当前游戏状态
        :param available_targets: 可击杀目标列表
        :param previous_opinions: 之前队友的意见列表
        :return: 包含建议目标和意见的字典
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

        # Format alive good players
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

        # Format previous opinions
        prev_opinions_text = ""
        if previous_opinions:
            prev_opinions_text = "## 队友已发表的意见\n"
            for op in previous_opinions:
                prev_opinions_text += f"- {op['seat_number']}号{op['name']}：建议刀{op['suggested_target']}号，理由：{op['opinion']}\n"

        # Get day number
        day_number = game_state.get("day_number", 1)
        
        # Format speech history section (only for day 2+)
        speech_history = game_state.get("speech_history", "")
        if day_number > 1 and speech_history:
            speech_history_section = f"## 白天发言记录\n{speech_history}"
        else:
            speech_history_section = ""

        prompt = WEREWOLF_NIGHT_DISCUSS_PROMPT.format(
            day_number=day_number,
            alive_good_players=alive_good_text,
            teammates=teammates_text,
            known_info=formatted["known_info"],
            available_targets=targets_text,
            speech_history_section=speech_history_section,
            previous_opinions=prev_opinions_text,
        )

        messages = [
            {"role": "system", "content": self.get_system_prompt(game_state)},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.llm_client.generate(messages)
            decision = self._parse_json_response(response)

            suggested_target = decision.get("suggested_target")
            normalized_target = self._normalize_seat_number(suggested_target)
            
            # Validate target
            valid_seats = {t["seat_number"] for t in available_targets}
            if normalized_target is None or normalized_target not in valid_seats:
                if good_targets:
                    normalized_target = good_targets[0]["seat_number"]
                elif available_targets:
                    normalized_target = available_targets[0]["seat_number"]

            return {
                "seat_number": self.seat_number,
                "name": self.player_name,
                "suggested_target": normalized_target,
                "opinion": decision.get("opinion", "同意击杀这个目标"),
            }

        except Exception as e:
            logger.error(f"[{self.player_name}] Night discuss failed: {e}")
            # Fallback
            fallback_target = good_targets[0]["seat_number"] if good_targets else (
                available_targets[0]["seat_number"] if available_targets else None
            )
            return {
                "seat_number": self.seat_number,
                "name": self.player_name,
                "suggested_target": fallback_target,
                "opinion": "我觉得刀这个可以",
            }

    async def make_final_kill_decision(
        self,
        game_state: Dict[str, Any],
        available_targets: List[Dict[str, Any]],
        teammate_opinions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        综合队友意见，做出最终击杀决定。

        :param game_state: 当前游戏状态
        :param available_targets: 可击杀目标列表
        :param teammate_opinions: 所有狼人的意见列表
        :return: 最终决策
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

        # Format alive good players
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

        # Format teammate opinions
        opinions_text = ""
        for op in teammate_opinions:
            opinions_text += f"- {op['seat_number']}号{op['name']}：建议刀{op['suggested_target']}号，理由：{op['opinion']}\n"

        prompt = WEREWOLF_NIGHT_FINAL_DECISION_PROMPT.format(
            alive_good_players=alive_good_text,
            teammates=teammates_text,
            known_info=formatted["known_info"],
            available_targets=targets_text,
            teammate_opinions=opinions_text,
        )

        messages = [
            {"role": "system", "content": self.get_system_prompt(game_state)},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.llm_client.generate(messages)
            decision = self._parse_json_response(response)

            action = decision.get("action", "kill")
            target = decision.get("target")

            if action == "empty_kill":
                return {
                    "action": "empty_kill",
                    "target": None,
                    "reasoning": decision.get("reasoning", "选择空刀"),
                }

            # Normalize and validate target
            normalized_target = self._normalize_seat_number(target)
            valid_seats = {t["seat_number"] for t in available_targets}
            if normalized_target is None or normalized_target not in valid_seats:
                # Pick the most suggested target
                target_votes = {}
                for op in teammate_opinions:
                    t = op.get("suggested_target")
                    if t:
                        target_votes[t] = target_votes.get(t, 0) + 1
                if target_votes:
                    normalized_target = max(target_votes, key=target_votes.get)
                elif good_targets:
                    normalized_target = good_targets[0]["seat_number"]
                elif available_targets:
                    normalized_target = available_targets[0]["seat_number"]

            return {
                "action": "kill",
                "target": normalized_target,
                "reasoning": decision.get("reasoning", ""),
            }

        except Exception as e:
            logger.error(f"[{self.player_name}] Final decision failed: {e}")
            # Fallback: use most voted target
            target_votes = {}
            for op in teammate_opinions:
                t = op.get("suggested_target")
                if t:
                    target_votes[t] = target_votes.get(t, 0) + 1
            if target_votes:
                best_target = max(target_votes, key=target_votes.get)
            elif good_targets:
                best_target = good_targets[0]["seat_number"]
            else:
                best_target = None

            if best_target:
                return {
                    "action": "kill",
                    "target": best_target,
                    "reasoning": "综合队友意见选择目标",
                }
            return {
                "action": "empty_kill",
                "target": None,
                "reasoning": "决策失败，选择空刀",
            }
