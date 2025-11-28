"""Game roles constant data.

This module contains static game role definitions that were previously stored in database.
"""

from typing import Dict, List, Optional, TypedDict


class RoleDict(TypedDict):
    """Type definition for role data."""

    id: str
    slug: str
    name: str
    description: str
    task: str
    is_playable: bool


ROLES_BY_GAME: Dict[str, List[RoleDict]] = {
    "werewolf": [
        {
            "id": "villager",
            "slug": "villager",
            "name": "村民",
            "description": "普通村民，无特殊能力，白天参与讨论与投票。",
            "task": "在白天参与讨论并投票找出狼人；没有夜间能力。",
            "is_playable": True,
        },
        {
            "id": "werewolf",
            "slug": "werewolf",
            "name": "狼人",
            "description": "夜间行动的隐秘阵营，目标是消灭村民并隐瞒身份。",
            "task": "每晚选择一个玩家作为击杀目标；在白天混淆视听避免被投票判定。",
            "is_playable": True,
        },
        {
            "id": "seer",
            "slug": "seer",
            "name": "预言家",
            "description": "每晚可以查看一名玩家的真实身份（好人阵营/狼人阵营）。",
            "task": "每晚选择一名玩家查验其身份，获得该玩家是狼人还是好人的信息，并在白天合理引导村民投票。",
            "is_playable": True,
        },
        {
            "id": "witch",
            "slug": "witch",
            "name": "女巫",
            "description": "拥有解药和毒药各一瓶，解药可以救活当晚被狼人杀死的玩家，毒药可以毒死任意一名玩家。",
            "task": "每晚得知被狼人击杀的目标后决定是否使用解药救人；可以在任意夜晚使用毒药毒死一名玩家。每种药只能使用一次。",
            "is_playable": True,
        },
        {
            "id": "hunter",
            "slug": "hunter",
            "name": "猎人",
            "description": "当猎人被淘汰（无论是被狼人杀死还是被投票出局）时，可以立即开枪带走一名玩家。",
            "task": "被淘汰时开枪选择一名玩家作为报复目标。注意：如果被女巫毒死则不能开枪。",
            "is_playable": True,
        },
    ],
}


def get_roles_by_game_slug(game_slug: str) -> Optional[List[RoleDict]]:
    """Get roles for a specific game by its slug.

    Args:
        game_slug: The game slug to search for.

    Returns:
        List of role dicts if found, None otherwise.
    """
    return ROLES_BY_GAME.get(game_slug)
