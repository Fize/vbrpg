"""Input validation utilities.

Centralized validation for usernames, room codes, and game actions.
"""
import re
from typing import Any

from src.utils.errors import BadRequestError


# Validation patterns
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\u4e00-\u9fa5]{3,20}$')
ROOM_CODE_PATTERN = re.compile(r'^[A-Z0-9]{6}$')
GUEST_USERNAME_PATTERN = re.compile(r'^Guest_[a-z]+_[a-z]+$')


def validate_username(username: str) -> str:
    """Validate and normalize username.
    
    Args:
        username: Username to validate
        
    Returns:
        Normalized username
        
    Raises:
        BadRequestError: If username invalid
    """
    if not username:
        raise BadRequestError("用户名不能为空")
    
    username = username.strip()
    
    if not username:
        raise BadRequestError("用户名不能为空")
    
    # Check guest username format
    if username.startswith("Guest_"):
        if not GUEST_USERNAME_PATTERN.match(username):
            raise BadRequestError("访客用户名格式无效")
        return username
    
    # Check regular username format
    if not USERNAME_PATTERN.match(username):
        raise BadRequestError(
            "用户名只能包含字母、数字、下划线和中文字符，长度为 3-20"
        )
    
    return username


def validate_room_code(room_code: str) -> str:
    """Validate and normalize room code.
    
    Args:
        room_code: Room code to validate
        
    Returns:
        Normalized room code (uppercase)
        
    Raises:
        BadRequestError: If room code invalid
    """
    if not room_code:
        raise BadRequestError("房间代码不能为空")
    
    room_code = room_code.strip().upper()
    
    if not ROOM_CODE_PATTERN.match(room_code):
        raise BadRequestError("房间代码必须是 6 位大写字母或数字")
    
    return room_code


def validate_action(action: dict[str, Any]) -> dict[str, Any]:
    """Validate game action structure.
    
    Args:
        action: Action dictionary to validate
        
    Returns:
        Validated action
        
    Raises:
        BadRequestError: If action structure invalid
    """
    if not isinstance(action, dict):
        raise BadRequestError("动作必须是字典格式")
    
    if "type" not in action:
        raise BadRequestError("动作必须包含 'type' 字段")
    
    action_type = action["type"]
    if not isinstance(action_type, str):
        raise BadRequestError("动作类型必须是字符串")
    
    # Validate action type
    valid_types = {
        "investigate",
        "question",
        "accuse",
        "move",
        "examine",
        "use_item",
        "speak"
    }
    
    if action_type not in valid_types:
        raise BadRequestError(f"无效的动作类型: {action_type}")
    
    # Validate required fields for each action type
    if action_type == "investigate":
        if "location" not in action:
            raise BadRequestError("调查动作必须包含 'location' 字段")
    
    elif action_type == "question":
        if "target" not in action or "question" not in action:
            raise BadRequestError("询问动作必须包含 'target' 和 'question' 字段")
    
    elif action_type == "accuse":
        if "target" not in action or "evidence" not in action:
            raise BadRequestError("指控动作必须包含 'target' 和 'evidence' 字段")
    
    elif action_type == "move":
        if "destination" not in action:
            raise BadRequestError("移动动作必须包含 'destination' 字段")
    
    elif action_type == "examine":
        if "object" not in action:
            raise BadRequestError("检查动作必须包含 'object' 字段")
    
    elif action_type == "use_item":
        if "item" not in action:
            raise BadRequestError("使用物品动作必须包含 'item' 字段")
    
    return action


def validate_player_count(count: int, min_players: int = 2, max_players: int = 6) -> int:
    """Validate player count for game room.
    
    Args:
        count: Player count to validate
        min_players: Minimum allowed players (default: 2)
        max_players: Maximum allowed players (default: 6)
        
    Returns:
        Validated player count
        
    Raises:
        BadRequestError: If count out of range
    """
    if not isinstance(count, int):
        raise BadRequestError("玩家数量必须是整数")
    
    if count < min_players or count > max_players:
        raise BadRequestError(f"玩家数量必须在 {min_players} 到 {max_players} 之间")
    
    return count


def validate_game_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate game configuration.
    
    Args:
        config: Game configuration to validate
        
    Returns:
        Validated configuration
        
    Raises:
        BadRequestError: If configuration invalid
    """
    if not isinstance(config, dict):
        raise BadRequestError("游戏配置必须是字典格式")
    
    # Validate difficulty
    if "difficulty" in config:
        valid_difficulties = {"easy", "medium", "hard"}
        if config["difficulty"] not in valid_difficulties:
            raise BadRequestError(f"难度必须是: {', '.join(valid_difficulties)}")
    
    # Validate turn_time_limit
    if "turn_time_limit" in config:
        time_limit = config["turn_time_limit"]
        if not isinstance(time_limit, int) or time_limit < 30 or time_limit > 300:
            raise BadRequestError("回合时间限制必须在 30-300 秒之间")
    
    # Validate use_ai_narrator
    if "use_ai_narrator" in config:
        if not isinstance(config["use_ai_narrator"], bool):
            raise BadRequestError("AI 叙述者设置必须是布尔值")
    
    return config
