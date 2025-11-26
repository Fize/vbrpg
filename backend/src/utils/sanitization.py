"""Content sanitization utilities.

Prevent injection attacks and sanitize user-provided content.
"""
import html
import re
from typing import Any

# Patterns for dangerous content
SQL_INJECTION_PATTERN = re.compile(
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|TABLE)\b)|"
    r"(--|;|\/\*|\*\/|xp_|sp_)",
    re.IGNORECASE
)

SCRIPT_TAG_PATTERN = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
EVENT_HANDLER_PATTERN = re.compile(r"\bon\w+\s*=", re.IGNORECASE)
JAVASCRIPT_PROTOCOL = re.compile(r"javascript:", re.IGNORECASE)


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
