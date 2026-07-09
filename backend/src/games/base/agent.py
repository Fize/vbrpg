"""Base AI agent for any game."""
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

logger = logging.getLogger(__name__)

class BaseGameAgent(ABC):
    """Abstract base for all game AI agents."""
    
    def __init__(self, player_id: str, player_name: str, seat_number: int,
                 personality: Optional[Dict[str, str]] = None):
        self.player_id = player_id
        self.player_name = player_name
        self.seat_number = seat_number
        self.personality = personality or {}
        self.is_alive = True
        self.memory: List[Dict[str, Any]] = []
    
    @property
    @abstractmethod
    def role_type(self) -> str:
        pass
    
    @abstractmethod
    def get_system_prompt(self, game_state: Dict[str, Any]) -> str:
        pass
    
    def add_memory(self, event: Dict[str, Any]) -> None:
        self.memory.append(event)

    async def generate_speech(self, game_state: Dict[str, Any],
                              llm_client: Optional[Any] = None) -> str:
        """默认发言生成。子类可重写以实现特殊发言逻辑。"""
        system_prompt = self.get_system_prompt(game_state)
        day_number = game_state.get("day_number", 1)
        user_prompt = (
            f"## 白天讨论\n"
            f"你是{self.player_name}，现在是第{day_number}天白天讨论阶段。"
            f"请根据你的角色和游戏局势，发表一段讨论发言。"
            f"请用中文发言，语言符合你角色的性格特征。"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await llm_client.generate(messages=messages)
        logger.info("%s 发言: %s...", self.player_name, str(response)[:50])
        return response

    async def decide_vote(self, game_state: Dict[str, Any],
                          available_targets: List[Dict[str, Any]],
                          llm_client: Optional[Any] = None) -> Dict[str, Any]:
        """默认投票决策。子类可重写以实现特殊投票逻辑。"""
        system_prompt = self.get_system_prompt(game_state)
        user_prompt = (
            f"## 投票\n"
            f"可投票目标：{available_targets}\n"
            f"请投票淘汰你认为最可能是狼人的玩家。"
            f"返回JSON格式：{{\"target\": 座号, \"reasoning\": \"理由\"}}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = await llm_client.generate(messages=messages)
            result = json.loads(response)
            return {"target": result.get("target"), "reasoning": result.get("reasoning", "")}
        except Exception as e:
            logger.warning("%s 投票解析失败: %s", self.player_name, e)
            fallback_target = available_targets[0]["seat_number"] if available_targets else None
            return {"target": fallback_target, "reasoning": "解析失败，随机选择"}
