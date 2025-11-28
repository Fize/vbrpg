"""Game types constant data.

This module contains static game type definitions that were previously stored in database.
"""

from typing import List, Optional, TypedDict


class GameTypeDict(TypedDict):
    """Type definition for game type data."""

    id: str
    name: str
    slug: str
    description: str
    rules_summary: str
    min_players: int
    max_players: int
    avg_duration_minutes: int
    is_available: bool
    min_ai_opponents: int
    max_ai_opponents: int
    supports_spectating: bool


GAME_TYPES: List[GameTypeDict] = [
    {
        "id": "crime-scene",
        "name": "犯罪现场",
        "slug": "crime-scene",
        "description": "一款推理解谜游戏，玩家通过收集线索、推理分析来找出真凶。每个玩家扮演不同的角色，通过互动和讨论来揭开谜团。",
        "rules_summary": """游戏分为几个阶段：
1. 角色分配：每个玩家获得一个角色卡，包含背景故事和秘密信息
2. 线索收集：玩家轮流探索场景，收集证据和线索
3. 讨论推理：玩家可以自由讨论，分享信息或保留秘密
4. 指认凶手：根据收集的信息，投票指认凶手
5. 真相揭晓：揭示最终答案

游戏目标：找出真凶，或者隐藏真相（如果你是凶手）""",
        "min_players": 4,
        "max_players": 8,
        "avg_duration_minutes": 60,
        "is_available": True,
        "min_ai_opponents": 1,
        "max_ai_opponents": 3,
        "supports_spectating": True,
    },
    {
        "id": "werewolf",
        "name": "狼人杀",
        "slug": "werewolf",
        "description": "经典的社交推理游戏，村民和狼人展开智慧与心理的较量。白天投票，夜晚行动，谁能笑到最后？",
        "rules_summary": "狼人杀规则：村民需要找出所有狼人，狼人需要消灭所有村民。",
        "min_players": 6,
        "max_players": 12,
        "avg_duration_minutes": 45,
        "is_available": True,
        "min_ai_opponents": 1,
        "max_ai_opponents": 3,
        "supports_spectating": True,
    },
]


def get_game_type_by_slug(slug: str) -> Optional[GameTypeDict]:
    """Get a game type by its slug.

    Args:
        slug: The game type slug to search for.

    Returns:
        The game type dict if found, None otherwise.
    """
    for game_type in GAME_TYPES:
        if game_type["slug"] == slug:
            return game_type
    return None
