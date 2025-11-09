"""Tests for sanitization utilities.

Tests content sanitization and injection prevention.
"""
import pytest

from src.utils.sanitization import (
    sanitize_text,
    sanitize_username,
    sanitize_room_code,
    sanitize_action_content,
    sanitize_chat_message,
    check_for_injection
)


class TestSanitizeText:
    """Test sanitize_text function."""
    
    def test_normal_text_unchanged(self):
        """Test normal text passes through unchanged."""
        text = "Hello, this is a normal message."
        result = sanitize_text(text)
        assert result == text
    
    def test_strips_whitespace(self):
        """Test whitespace is stripped."""
        text = "  Hello  "
        result = sanitize_text(text)
        assert result == "Hello"
    
    def test_html_escaping(self):
        """Test HTML special characters are escaped."""
        text = "<div>Hello & goodbye</div>"
        result = sanitize_text(text)
        assert "&lt;div&gt;" in result
        assert "&amp;" in result
    
    def test_removes_script_tags(self):
        """Test script tags are removed."""
        text = "Hello<script>alert('xss')</script>World"
        result = sanitize_text(text)
        assert "script" not in result.lower()
    
    def test_removes_event_handlers(self):
        """Test event handlers are removed."""
        text = '<div onclick="alert(\'xss\')">Click me</div>'
        result = sanitize_text(text)
        assert "onclick" not in result
    
    def test_removes_javascript_protocol(self):
        """Test javascript: protocol is removed."""
        text = '<a href="javascript:alert(\'xss\')">Link</a>'
        result = sanitize_text(text)
        assert "javascript:" not in result
    
    def test_enforces_max_length(self):
        """Test max length is enforced."""
        text = "a" * 2000
        result = sanitize_text(text, max_length=100)
        assert len(result) <= 100
    
    def test_default_max_length(self):
        """Test default max length."""
        text = "a" * 2000
        result = sanitize_text(text)
        assert len(result) <= 1000
    
    def test_empty_string(self):
        """Test empty string returns empty string."""
        result = sanitize_text("")
        assert result == ""
    
    def test_none_returns_empty_string(self):
        """Test None returns empty string."""
        result = sanitize_text(None)
        assert result == ""


class TestSanitizeUsername:
    """Test sanitize_username function."""
    
    def test_normal_username(self):
        """Test normal username."""
        username = "player123"
        result = sanitize_username(username)
        assert result == username
    
    def test_strips_whitespace(self):
        """Test whitespace is stripped."""
        username = "  player123  "
        result = sanitize_username(username)
        assert result == "player123"
    
    def test_html_escapes(self):
        """Test HTML is escaped."""
        username = "player<script>"
        result = sanitize_username(username)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
    
    def test_removes_sql_injection(self):
        """Test SQL injection patterns are removed."""
        username = "admin'; DROP TABLE users;--"
        result = sanitize_username(username)
        assert "DROP" not in result
        assert "TABLE" not in result
    
    def test_enforces_max_length(self):
        """Test max length of 20 characters."""
        username = "a" * 50
        result = sanitize_username(username)
        assert len(result) <= 20
    
    def test_empty_string(self):
        """Test empty string."""
        result = sanitize_username("")
        assert result == ""


class TestSanitizeRoomCode:
    """Test sanitize_room_code function."""
    
    def test_valid_room_code(self):
        """Test valid room code."""
        room_code = "ABC123"
        result = sanitize_room_code(room_code)
        assert result == "ABC123"
    
    def test_removes_special_characters(self):
        """Test special characters are removed."""
        room_code = "AB@C#12$3"
        result = sanitize_room_code(room_code)
        assert result == "ABC123"
    
    def test_converts_to_uppercase(self):
        """Test converts to uppercase."""
        room_code = "abc123"
        result = sanitize_room_code(room_code)
        assert result == "ABC123"
    
    def test_limits_to_6_characters(self):
        """Test limits to 6 characters."""
        room_code = "ABCDEFGHIJ"
        result = sanitize_room_code(room_code)
        assert len(result) == 6
        assert result == "ABCDEF"
    
    def test_empty_string(self):
        """Test empty string."""
        result = sanitize_room_code("")
        assert result == ""


class TestSanitizeActionContent:
    """Test sanitize_action_content function."""
    
    def test_sanitizes_string_values(self):
        """Test string values are sanitized."""
        action = {
            "type": "question",
            "question": "<script>alert('xss')</script>"
        }
        result = sanitize_action_content(action)
        assert "<script>" not in result["question"]
    
    def test_preserves_safe_content(self):
        """Test safe content is preserved."""
        action = {
            "type": "investigate",
            "location": "library"
        }
        result = sanitize_action_content(action)
        assert result["location"] == "library"
    
    def test_handles_nested_dicts(self):
        """Test nested dictionaries are sanitized."""
        action = {
            "type": "complex",
            "data": {
                "message": "<script>xss</script>"
            }
        }
        result = sanitize_action_content(action)
        assert "<script>" not in result["data"]["message"]
    
    def test_handles_lists(self):
        """Test lists are sanitized."""
        action = {
            "type": "multiple",
            "items": ["<script>xss1</script>", "safe", "<script>xss2</script>"]
        }
        result = sanitize_action_content(action)
        assert all("<script>" not in item for item in result["items"])
    
    def test_preserves_non_string_values(self):
        """Test non-string values are preserved."""
        action = {
            "type": "action",
            "count": 42,
            "enabled": True
        }
        result = sanitize_action_content(action)
        assert result["count"] == 42
        assert result["enabled"] is True
    
    def test_non_dict_returns_unchanged(self):
        """Test non-dict returns unchanged."""
        action = "not a dict"
        result = sanitize_action_content(action)
        assert result == action


class TestSanitizeChatMessage:
    """Test sanitize_chat_message function."""
    
    def test_normal_message(self):
        """Test normal message."""
        message = "Hello, how are you?"
        result = sanitize_chat_message(message)
        assert result == message
    
    def test_strips_whitespace(self):
        """Test whitespace is stripped."""
        message = "  Hello  "
        result = sanitize_chat_message(message)
        assert result == "Hello"
    
    def test_html_escapes(self):
        """Test HTML is escaped."""
        message = "<b>Bold text</b>"
        result = sanitize_chat_message(message)
        assert "<b>" not in result
        assert "&lt;b&gt;" in result
    
    def test_removes_script_tags(self):
        """Test script tags are removed."""
        message = "Hello<script>alert('xss')</script>World"
        result = sanitize_chat_message(message)
        assert "script" not in result.lower()
    
    def test_removes_event_handlers(self):
        """Test event handlers are removed."""
        message = '<img src=x onerror="alert(\'xss\')">'
        result = sanitize_chat_message(message)
        assert "onerror" not in result
    
    def test_enforces_max_length(self):
        """Test max length of 500 characters."""
        message = "a" * 1000
        result = sanitize_chat_message(message)
        assert len(result) <= 500
    
    def test_sql_injection_allowed_but_logged(self):
        """Test SQL injection patterns are allowed (for chat) but logged."""
        message = "I think the answer is SELECT * FROM clues"
        result = sanitize_chat_message(message)
        # Message should still be returned (it's just a chat message)
        assert "SELECT" in result
    
    def test_empty_string(self):
        """Test empty string."""
        result = sanitize_chat_message("")
        assert result == ""


class TestCheckForInjection:
    """Test check_for_injection function."""
    
    def test_safe_text_returns_false(self):
        """Test safe text returns False."""
        text = "This is a normal message"
        result = check_for_injection(text)
        assert result is False
    
    def test_sql_injection_returns_true(self):
        """Test SQL injection patterns return True."""
        texts = [
            "SELECT * FROM users",
            "DROP TABLE players",
            "INSERT INTO games",
            "'; DROP TABLE--",
            "UNION SELECT password"
        ]
        for text in texts:
            result = check_for_injection(text)
            assert result is True, f"Failed to detect SQL injection in: {text}"
    
    def test_script_tags_return_true(self):
        """Test script tags return True."""
        text = "<script>alert('xss')</script>"
        result = check_for_injection(text)
        assert result is True
    
    def test_event_handlers_return_true(self):
        """Test event handlers return True."""
        texts = [
            '<img onerror="alert(1)">',
            '<div onclick="malicious()">',
            '<body onload="hack()">',
        ]
        for text in texts:
            result = check_for_injection(text)
            assert result is True, f"Failed to detect event handler in: {text}"
    
    def test_javascript_protocol_returns_true(self):
        """Test javascript: protocol returns True."""
        text = '<a href="javascript:alert(1)">Click</a>'
        result = check_for_injection(text)
        assert result is True
    
    def test_empty_string_returns_false(self):
        """Test empty string returns False."""
        result = check_for_injection("")
        assert result is False
    
    def test_none_returns_false(self):
        """Test None returns False."""
        result = check_for_injection(None)
        assert result is False
    
    def test_case_insensitive(self):
        """Test detection is case-insensitive."""
        texts = [
            "select * from users",
            "SeLeCt * FrOm users",
            "<ScRiPt>alert(1)</ScRiPt>",
            "JavaScript:alert(1)"
        ]
        for text in texts:
            result = check_for_injection(text)
            assert result is True, f"Failed case-insensitive detection: {text}"
