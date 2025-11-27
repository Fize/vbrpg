"""Input processing utilities.

This module combines content sanitization and input validation utilities.
Provides protection against injection attacks and validates user input.
"""
import html
import re
from typing import Any

from src.utils.errors import BadRequestError


# =============================================================================
# Sanitization Patterns
# =============================================================================

SQL_INJECTION_PATTERN = re.compile(
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|TABLE)\b)|"
    r"(--|;|\/\*|\*\/|xp_|sp_)",
    re.IGNORECASE
)

SCRIPT_TAG_PATTERN = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
EVENT_HANDLER_PATTERN = re.compile(r"\bon\w+\s*=", re.IGNORECASE)
JAVASCRIPT_PROTOCOL = re.compile(r"javascript:", re.IGNORECASE)


# =============================================================================
# Validation Patterns
# =============================================================================

USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\u4e00-\u9fa5]{3,20}$')
ROOM_CODE_PATTERN = re.compile(r'^[A-Z0-9]{6}$')
GUEST_USERNAME_PATTERN = re.compile(r'^Guest_[a-z]+_[a-z]+$')


# =============================================================================
# Sanitization Functions
# =============================================================================

def sanitize_text(text: str, max_length: int = 1000) -> str:
    """Sanitize user-provided text content.

    Args:
        text: Text to sanitize
        max_length: Maximum allowed length (default: 1000)

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Trim whitespace
    text = text.strip()

    # Enforce max length
    if len(text) > max_length:
        text = text[:max_length]

    # Remove script tags first
    text = SCRIPT_TAG_PATTERN.sub("", text)

    # Remove event handlers
    text = EVENT_HANDLER_PATTERN.sub("", text)

    # Remove javascript: protocol
    text = JAVASCRIPT_PROTOCOL.sub("", text)

    # HTML escape to prevent XSS
    text = html.escape(text)

    return text


def sanitize_username(username: str) -> str:
    """Sanitize username input.

    Args:
        username: Username to sanitize

    Returns:
        Sanitized username
    """
    if not username:
        return ""

    # Trim and limit length
    username = username.strip()[:20]

    # Remove any SQL injection attempts
    if SQL_INJECTION_PATTERN.search(username):
        # Strip out dangerous patterns
        username = SQL_INJECTION_PATTERN.sub("", username)

    # HTML escape
    username = html.escape(username)

    return username


def sanitize_room_code(room_code: str) -> str:
    """Sanitize room code input.

    Args:
        room_code: Room code to sanitize

    Returns:
        Sanitized room code (uppercase alphanumeric only)
    """
    if not room_code:
        return ""

    # Keep only alphanumeric, convert to uppercase
    room_code = re.sub(r'[^A-Z0-9]', '', room_code.upper())

    # Limit to 6 characters
    return room_code[:6]


def sanitize_action_content(action: dict[str, Any]) -> dict[str, Any]:
    """Sanitize content within game actions.

    Args:
        action: Action dictionary with user content

    Returns:
        Action with sanitized content
    """
    if not isinstance(action, dict):
        return action

    sanitized = {}

    for key, value in action.items():
        if isinstance(value, str):
            # Sanitize string values
            sanitized[key] = sanitize_text(value, max_length=500)
        elif isinstance(value, dict):
            # Recursively sanitize nested dicts
            sanitized[key] = sanitize_action_content(value)
        elif isinstance(value, list):
            # Sanitize list items
            sanitized[key] = [
                sanitize_text(item, max_length=500) if isinstance(item, str) else item
                for item in value
            ]
        else:
            # Keep other types as-is
            sanitized[key] = value

    return sanitized


def sanitize_chat_message(message: str) -> str:
    """Sanitize chat message content.

    Args:
        message: Chat message to sanitize

    Returns:
        Sanitized message
    """
    if not message:
        return ""

    # Trim and limit length (chat messages can be longer)
    message = message.strip()
    if len(message) > 500:
        message = message[:500]

    # Remove script tags and event handlers first
    message = SCRIPT_TAG_PATTERN.sub("", message)
    message = EVENT_HANDLER_PATTERN.sub("", message)
    message = JAVASCRIPT_PROTOCOL.sub("", message)

    # HTML escape
    message = html.escape(message)

    # Check for SQL injection patterns (log warning but allow)
    if SQL_INJECTION_PATTERN.search(message):
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Potential SQL injection in chat message: {message[:100]}")

    return message


def check_for_injection(text: str) -> bool:
    """Check if text contains potential injection attempts.

    Args:
        text: Text to check

    Returns:
        True if injection patterns detected, False otherwise
    """
    if not text:
        return False

    # Check for SQL injection
    if SQL_INJECTION_PATTERN.search(text):
        return True

    # Check for script tags
    if SCRIPT_TAG_PATTERN.search(text):
        return True

    # Check for event handlers
    if EVENT_HANDLER_PATTERN.search(text):
        return True

    # Check for javascript protocol
    if JAVASCRIPT_PROTOCOL.search(text):
        return True

    return False


# =============================================================================
# Validation Functions
# =============================================================================

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
