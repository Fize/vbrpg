# -*- coding: utf-8 -*-
"""Werewolf role AI agent."""

import logging
from typing import Any, Dict, List, Optional

from src.games.base.agent import BaseGameAgent
from src.games.werewolf.prompts.werewolf import (
    WEREWOLF_NIGHT_PROMPT,
    WEREWOLF_NIGHT_DISCUSS_PROMPT,
    WEREWOLF_NIGHT_FINAL_DECISION_PROMPT,
    WEREWOLF_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class WerewolfAgent(BaseGameAgent):
    """AI agent for werewolf role."""

    def __init__(
        self,
        player_id: str,
        player_name: str,
        seat_number: int,
        personality: Optional[Dict[str, str]] = None,
        teammates: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Initialize werewolf agent.

        :param player_id: Unique player identifier.
        :param player_name: Display name.
        :param seat_number: Seat number (1-10).
        :param personality: Personality traits for the agent.
        :param teammates: List of werewolf teammate info.
        """
        super().__init__(player_id, player_name, seat_number, personality)
        self.teammates = teammates or []
        self.known_info: List[Dict[str, Any]] = []

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
        for mate in teammates:
            self.known_info.append({
                "type": "teammate",
                "content": f"{mate['seat_number']}号{mate['name']}是狼人队友",
            })

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
        """Get werewolf system prompt."""
        alive_players = game_state.get("alive_players", [])
        dead_players = game_state.get("dead_players", [])
        day_number = game_state.get("day_number", 1)

        alive_text = ", ".join(
            [f"{p['seat_number']}号{p['name']}" for p in alive_players]
        ) or "无"
        dead_text = ", ".join(
            [f"{p['seat_number']}号{p['name']}" for p in dead_players]
        ) or "无"

        teammates_text = ", ".join([
            f"{t['seat_number']}号{t['name']}"
            for t in self.teammates
            if t.get("is_alive", True)
        ]) or "无存活队友"

        personality_section = self._build_personality_section()
        if personality_section:
            personality_section = f"\n\n## 你的性格特征\n{personality_section}\n请用符合你性格特征的方式思考和发言。\n"

        return WEREWOLF_SYSTEM_PROMPT.format(
            teammates=teammates_text,
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
        Decide who to kill at night.

        :param game_state: Current game state.
        :param available_targets: List of killable players.
        :param llm_client: LLM client for generating responses.
        :return: Action decision.
        """
        day_number = game_state.get("day_number", 1)
        alive_players = game_state.get("alive_players", [])
        dead_players = game_state.get("dead_players", [])

        alive_text = ", ".join(
            [f"{p['seat_number']}号{p['name']}" for p in alive_players]
        ) or "无"
        dead_text = ", ".join(
            [f"{p['seat_number']}号{p['name']}" for p in dead_players]
        ) or "无"

        non_teammate_ids = {t.get("player_id") for t in self.teammates}
        good_targets = [
            t for t in available_targets
            if t.get("player_id") not in non_teammate_ids
        ]

        targets_text = "\n".join([
            f"- {t['seat_number']}号 {t['name']}"
            for t in available_targets
        ])

        alive_good_text = ", ".join([
            f"{t['seat_number']}号{t['name']}"
            for t in good_targets
        ])

        teammates_text = ", ".join([
            f"{t['seat_number']}号{t['name']}"
            for t in self.teammates
            if t.get("is_alive", True)
        ])

        prompt = WEREWOLF_NIGHT_PROMPT.format(
            alive_good_players=alive_good_text,
            teammates=teammates_text,
            known_info=self.format_known_info(),
            available_targets=targets_text,
        )

        messages = [
            {"role": "system", "content": self.get_system_prompt(game_state)},
            {"role": "user", "content": prompt},
        ]

        if llm_client is None:
            from src.integrations.llm_client import LLMClient
            llm_client = LLMClient()

        try:
            response = await llm_client.generate(messages)
            decision = self._parse_json_response(response)

            action = decision.get("action", "kill")
            target = decision.get("target")

            if action == "empty_kill":
                return {
                    "action": "empty_kill",
                    "target": None,
                    "reasoning": decision.get("reasoning", "选择空刀"),
                }

            normalized_target = self._normalize_seat_number(target)
            valid_seats = {t["seat_number"] for t in available_targets}
            if normalized_target is None or normalized_target not in valid_seats:
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
        llm_client=None,
    ) -> Dict[str, Any]:
        """
        在狼人讨论阶段发表击杀意见。

        :param game_state: 当前游戏状态
        :param available_targets: 可击杀目标列表
        :param previous_opinions: 之前队友的意见列表
        :param llm_client: LLM client for generating responses.
        :return: 包含建议目标和意见的字典
        """
        day_number = game_state.get("day_number", 1)
        alive_players = game_state.get("alive_players", [])
        dead_players = game_state.get("dead_players", [])

        alive_text = ", ".join(
            [f"{p['seat_number']}号{p['name']}" for p in alive_players]
        ) or "无"
        dead_text = ", ".join(
            [f"{p['seat_number']}号{p['name']}" for p in dead_players]
        ) or "无"

        non_teammate_ids = {t.get("player_id") for t in self.teammates}
        good_targets = [
            t for t in available_targets
            if t.get("player_id") not in non_teammate_ids
        ]

        targets_text = "\n".join([
            f"- {t['seat_number']}号 {t['name']}"
            for t in available_targets
        ])

        alive_good_text = ", ".join([
            f"{t['seat_number']}号{t['name']}"
            for t in good_targets
        ])

        teammates_text = ", ".join([
            f"{t['seat_number']}号{t['name']}"
            for t in self.teammates
            if t.get("is_alive", True)
        ])

        prev_opinions_text = ""
        if previous_opinions:
            prev_opinions_text = "## 队友已发表的意见\n"
            for op in previous_opinions:
                prev_opinions_text += f"- {op['seat_number']}号{op['name']}：建议刀{op['suggested_target']}号，理由：{op['opinion']}\n"

        speech_history = game_state.get("speech_history", "")
        if day_number > 1 and speech_history:
            speech_history_section = f"## 白天发言记录\n{speech_history}"
        else:
            speech_history_section = ""

        prompt = WEREWOLF_NIGHT_DISCUSS_PROMPT.format(
            day_number=day_number,
            alive_good_players=alive_good_text,
            teammates=teammates_text,
            known_info=self.format_known_info(),
            available_targets=targets_text,
            speech_history_section=speech_history_section,
            previous_opinions=prev_opinions_text,
        )

        messages = [
            {"role": "system", "content": self.get_system_prompt(game_state)},
            {"role": "user", "content": prompt},
        ]

        if llm_client is None:
            from src.integrations.llm_client import LLMClient
            llm_client = LLMClient()

        try:
            response = await llm_client.generate(messages)
            decision = self._parse_json_response(response)

            suggested_target = decision.get("suggested_target")
            normalized_target = self._normalize_seat_number(suggested_target)

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
        llm_client=None,
    ) -> Dict[str, Any]:
        """
        综合队友意见，做出最终击杀决定。

        :param game_state: 当前游戏状态
        :param available_targets: 可击杀目标列表
        :param teammate_opinions: 所有狼人的意见列表
        :param llm_client: LLM client for generating responses.
        :return: 最终决策
        """
        alive_players = game_state.get("alive_players", [])
        dead_players = game_state.get("dead_players", [])

        alive_text = ", ".join(
            [f"{p['seat_number']}号{p['name']}" for p in alive_players]
        ) or "无"
        dead_text = ", ".join(
            [f"{p['seat_number']}号{p['name']}" for p in dead_players]
        ) or "无"

        non_teammate_ids = {t.get("player_id") for t in self.teammates}
        good_targets = [
            t for t in available_targets
            if t.get("player_id") not in non_teammate_ids
        ]

        targets_text = "\n".join([
            f"- {t['seat_number']}号 {t['name']}"
            for t in available_targets
        ])

        alive_good_text = ", ".join([
            f"{t['seat_number']}号{t['name']}"
            for t in good_targets
        ])

        teammates_text = ", ".join([
            f"{t['seat_number']}号{t['name']}"
            for t in self.teammates
            if t.get("is_alive", True)
        ])

        opinions_text = ""
        for op in teammate_opinions:
            opinions_text += f"- {op['seat_number']}号{op['name']}：建议刀{op['suggested_target']}号，理由：{op['opinion']}\n"

        prompt = WEREWOLF_NIGHT_FINAL_DECISION_PROMPT.format(
            alive_good_players=alive_good_text,
            teammates=teammates_text,
            known_info=self.format_known_info(),
            available_targets=targets_text,
            teammate_opinions=opinions_text,
        )

        messages = [
            {"role": "system", "content": self.get_system_prompt(game_state)},
            {"role": "user", "content": prompt},
        ]

        if llm_client is None:
            from src.integrations.llm_client import LLMClient
            llm_client = LLMClient()

        try:
            response = await llm_client.generate(messages)
            decision = self._parse_json_response(response)

            action = decision.get("action", "kill")
            target = decision.get("target")

            if action == "empty_kill":
                return {
                    "action": "empty_kill",
                    "target": None,
                    "reasoning": decision.get("reasoning", "选择空刀"),
                }

            normalized_target = self._normalize_seat_number(target)
            valid_seats = {t["seat_number"] for t in available_targets}
            if normalized_target is None or normalized_target not in valid_seats:
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
