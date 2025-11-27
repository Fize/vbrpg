"""Tests for validation utilities.

Tests input validation for usernames, room codes, actions, etc.
"""
import pytest

from src.utils.input_processing import (
    validate_username,
    validate_room_code,
    validate_action,
    validate_player_count,
    validate_game_config
)
from src.utils.errors import BadRequestError


class TestValidateUsername:
    """Test validate_username function."""
    
    def test_valid_alphanumeric_username(self):
        """Test valid alphanumeric username."""
        result = validate_username("player123")
        assert result == "player123"
    
    def test_valid_username_with_underscore(self):
        """Test valid username with underscore."""
        result = validate_username("player_123")
        assert result == "player_123"
    
    def test_valid_chinese_username(self):
        """Test valid Chinese username."""
        result = validate_username("玩家123")
        assert result == "玩家123"
    
    def test_valid_guest_username(self):
        """Test valid guest username."""
        result = validate_username("Guest_happy_cat")
        assert result == "Guest_happy_cat"
    
    def test_strips_whitespace(self):
        """Test username whitespace is stripped."""
        result = validate_username("  player123  ")
        assert result == "player123"
    
    def test_empty_username_raises_error(self):
        """Test empty username raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_username("")
        assert "不能为空" in str(exc_info.value)
    
    def test_whitespace_only_username_raises_error(self):
        """Test whitespace-only username raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_username("   ")
        assert "不能为空" in str(exc_info.value)
    
    def test_too_short_username_raises_error(self):
        """Test too short username raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_username("ab")
        assert "3-20" in str(exc_info.value)
    
    def test_too_long_username_raises_error(self):
        """Test too long username raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_username("a" * 21)
        assert "3-20" in str(exc_info.value)
    
    def test_invalid_characters_raises_error(self):
        """Test invalid characters raise error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_username("player@123")
        assert "字母、数字、下划线和中文" in str(exc_info.value)
    
    def test_invalid_guest_format_raises_error(self):
        """Test invalid guest username format raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_username("Guest_Invalid_Format_123")
        assert "访客用户名格式无效" in str(exc_info.value)


class TestValidateRoomCode:
    """Test validate_room_code function."""
    
    def test_valid_room_code(self):
        """Test valid room code."""
        result = validate_room_code("ABC123")
        assert result == "ABC123"
    
    def test_converts_to_uppercase(self):
        """Test room code is converted to uppercase."""
        result = validate_room_code("abc123")
        assert result == "ABC123"
    
    def test_strips_whitespace(self):
        """Test room code whitespace is stripped."""
        result = validate_room_code("  ABC123  ")
        assert result == "ABC123"
    
    def test_empty_room_code_raises_error(self):
        """Test empty room code raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_room_code("")
        assert "不能为空" in str(exc_info.value)
    
    def test_invalid_length_raises_error(self):
        """Test invalid length raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_room_code("ABC12")
        assert "6 位" in str(exc_info.value)
    
    def test_invalid_characters_raises_error(self):
        """Test invalid characters raise error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_room_code("ABC@12")
        assert "6 位大写字母或数字" in str(exc_info.value)


class TestValidateAction:
    """Test validate_action function."""
    
    def test_valid_investigate_action(self):
        """Test valid investigate action."""
        action = {
            "type": "investigate",
            "location": "library"
        }
        result = validate_action(action)
        assert result["type"] == "investigate"
        assert result["location"] == "library"
    
    def test_valid_question_action(self):
        """Test valid question action."""
        action = {
            "type": "question",
            "target": "butler",
            "question": "Where were you?"
        }
        result = validate_action(action)
        assert result["type"] == "question"
    
    def test_valid_accuse_action(self):
        """Test valid accuse action."""
        action = {
            "type": "accuse",
            "target": "colonel",
            "evidence": "fingerprints"
        }
        result = validate_action(action)
        assert result["type"] == "accuse"
    
    def test_valid_move_action(self):
        """Test valid move action."""
        action = {
            "type": "move",
            "destination": "kitchen"
        }
        result = validate_action(action)
        assert result["type"] == "move"
    
    def test_valid_examine_action(self):
        """Test valid examine action."""
        action = {
            "type": "examine",
            "object": "candlestick"
        }
        result = validate_action(action)
        assert result["type"] == "examine"
    
    def test_valid_use_item_action(self):
        """Test valid use_item action."""
        action = {
            "type": "use_item",
            "item": "magnifying_glass"
        }
        result = validate_action(action)
        assert result["type"] == "use_item"
    
    def test_non_dict_raises_error(self):
        """Test non-dict action raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_action("not a dict")
        assert "字典格式" in str(exc_info.value)
    
    def test_missing_type_raises_error(self):
        """Test missing type raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_action({"location": "library"})
        assert "type" in str(exc_info.value)
    
    def test_invalid_type_raises_error(self):
        """Test invalid action type raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_action({"type": "invalid_action"})
        assert "无效的动作类型" in str(exc_info.value)
    
    def test_investigate_missing_location_raises_error(self):
        """Test investigate without location raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_action({"type": "investigate"})
        assert "location" in str(exc_info.value)
    
    def test_question_missing_fields_raises_error(self):
        """Test question without required fields raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_action({"type": "question", "target": "butler"})
        assert "question" in str(exc_info.value)
    
    def test_accuse_missing_fields_raises_error(self):
        """Test accuse without required fields raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_action({"type": "accuse", "target": "colonel"})
        assert "evidence" in str(exc_info.value)


class TestValidatePlayerCount:
    """Test validate_player_count function."""
    
    def test_valid_player_count(self):
        """Test valid player count."""
        result = validate_player_count(4)
        assert result == 4
    
    def test_minimum_player_count(self):
        """Test minimum player count."""
        result = validate_player_count(2)
        assert result == 2
    
    def test_maximum_player_count(self):
        """Test maximum player count."""
        result = validate_player_count(6)
        assert result == 6
    
    def test_custom_min_max(self):
        """Test custom min and max."""
        result = validate_player_count(5, min_players=3, max_players=8)
        assert result == 5
    
    def test_non_integer_raises_error(self):
        """Test non-integer raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_player_count("4")
        assert "整数" in str(exc_info.value)
    
    def test_below_minimum_raises_error(self):
        """Test below minimum raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_player_count(1)
        assert "2 到 6" in str(exc_info.value)
    
    def test_above_maximum_raises_error(self):
        """Test above maximum raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_player_count(7)
        assert "2 到 6" in str(exc_info.value)


class TestValidateGameConfig:
    """Test validate_game_config function."""
    
    def test_valid_config(self):
        """Test valid game config."""
        config = {
            "difficulty": "medium",
            "turn_time_limit": 60,
            "use_ai_narrator": True
        }
        result = validate_game_config(config)
        assert result == config
    
    def test_valid_difficulty_easy(self):
        """Test valid easy difficulty."""
        config = {"difficulty": "easy"}
        result = validate_game_config(config)
        assert result["difficulty"] == "easy"
    
    def test_valid_difficulty_hard(self):
        """Test valid hard difficulty."""
        config = {"difficulty": "hard"}
        result = validate_game_config(config)
        assert result["difficulty"] == "hard"
    
    def test_valid_turn_time_limit(self):
        """Test valid turn time limit."""
        config = {"turn_time_limit": 120}
        result = validate_game_config(config)
        assert result["turn_time_limit"] == 120
    
    def test_empty_config(self):
        """Test empty config is allowed."""
        config = {}
        result = validate_game_config(config)
        assert result == {}
    
    def test_non_dict_raises_error(self):
        """Test non-dict config raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_game_config("not a dict")
        assert "字典格式" in str(exc_info.value)
    
    def test_invalid_difficulty_raises_error(self):
        """Test invalid difficulty raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_game_config({"difficulty": "impossible"})
        assert "难度" in str(exc_info.value)
    
    def test_turn_time_too_short_raises_error(self):
        """Test turn time too short raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_game_config({"turn_time_limit": 20})
        assert "30-300" in str(exc_info.value)
    
    def test_turn_time_too_long_raises_error(self):
        """Test turn time too long raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_game_config({"turn_time_limit": 400})
        assert "30-300" in str(exc_info.value)
    
    def test_invalid_ai_narrator_type_raises_error(self):
        """Test invalid ai_narrator type raises error."""
        with pytest.raises(BadRequestError) as exc_info:
            validate_game_config({"use_ai_narrator": "yes"})
        assert "布尔值" in str(exc_info.value)
