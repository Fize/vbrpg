"""Unit tests for MySQL database connection and JSON fields.

单人模式数据库层测试：
- MySQL 连接配置
- 连接池功能
- JSON 字段读写
"""
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db, engine
from src.models.game import GameRoom, GameState, GameType
from src.models.user import PlayerProfile


@pytest.mark.asyncio
class TestDatabaseConnection:
    """Test MySQL database connection configuration."""

    async def test_database_engine_created(self):
        """Test that database engine is properly created."""
        assert engine is not None
        # Check that we're using MySQL driver
        assert "mysql" in str(engine.url) or "aiomysql" in str(engine.url.drivername)

    async def test_get_db_yields_session(self, test_db: AsyncSession):
        """Test that get_db yields a valid session."""
        assert test_db is not None
        assert isinstance(test_db, AsyncSession)

    async def test_basic_query_works(self, test_db: AsyncSession):
        """Test that basic SQL query works."""
        result = await test_db.execute(text("SELECT 1 as test"))
        row = result.fetchone()
        assert row is not None
        assert row[0] == 1


@pytest.mark.asyncio
class TestConnectionPool:
    """Test MySQL connection pool functionality."""

    async def test_multiple_sessions_from_pool(self):
        """Test that multiple sessions can be obtained from pool."""
        sessions = []
        async for session in get_db():
            sessions.append(session)
            if len(sessions) >= 3:
                break

        # All sessions should be valid
        for session in sessions:
            assert session is not None


@pytest.mark.asyncio
class TestJSONFields:
    """Test MySQL JSON field read/write operations."""

    async def test_game_state_json_field_write(
        self,
        test_db: AsyncSession,
        sample_game_room: GameRoom
    ):
        """Test writing dict to GameState.game_data JSON field."""
        game_data = {
            "phase": "investigation",
            "current_turn": 1,
            "players": [
                {"id": "player1", "role": "detective", "alive": True},
                {"id": "player2", "role": "suspect", "alive": True}
            ],
            "clues_found": ["fingerprint", "weapon"]
        }

        game_state = GameState(
            game_room_id=sample_game_room.id,
            current_turn="player1",
            game_data=game_data
        )
        test_db.add(game_state)
        await test_db.commit()
        await test_db.refresh(game_state)

        assert game_state.id is not None
        assert game_state.game_data == game_data

    async def test_game_state_json_field_read(
        self,
        test_db: AsyncSession,
        sample_game_room: GameRoom
    ):
        """Test reading GameState.game_data JSON field."""
        game_data = {"test_key": "test_value", "nested": {"a": 1, "b": 2}}

        game_state = GameState(
            game_room_id=sample_game_room.id,
            current_turn="test",
            game_data=game_data
        )
        test_db.add(game_state)
        await test_db.commit()

        # Read back from database
        result = await test_db.execute(
            select(GameState).where(GameState.id == game_state.id)
        )
        loaded_state = result.scalar_one()

        assert loaded_state.game_data == game_data
        assert loaded_state.game_data["nested"]["a"] == 1

    async def test_game_state_json_field_update(
        self,
        test_db: AsyncSession,
        sample_game_room: GameRoom
    ):
        """Test updating GameState.game_data JSON field."""
        initial_data = {"phase": "start", "turn": 0}
        
        game_state = GameState(
            game_room_id=sample_game_room.id,
            current_turn="test",
            game_data=initial_data
        )
        test_db.add(game_state)
        await test_db.commit()

        # Update the JSON field
        updated_data = {"phase": "investigation", "turn": 1, "new_field": "value"}
        game_state.game_data = updated_data
        await test_db.commit()
        await test_db.refresh(game_state)

        assert game_state.game_data == updated_data
        assert game_state.game_data["new_field"] == "value"

    async def test_player_profile_json_preferences(
        self,
        test_db: AsyncSession,
        sample_player
    ):
        """Test PlayerProfile.ui_preferences JSON field."""
        preferences = {
            "theme": "dark",
            "language": "zh-CN",
            "notifications": {
                "sound": True,
                "vibration": False
            }
        }

        profile = PlayerProfile(
            player_id=sample_player.id,
            ui_preferences=preferences
        )
        test_db.add(profile)
        await test_db.commit()
        await test_db.refresh(profile)

        assert profile.ui_preferences == preferences
        assert profile.ui_preferences["notifications"]["sound"] is True

    async def test_json_field_null_handling(
        self,
        test_db: AsyncSession,
        sample_game_room: GameRoom
    ):
        """Test JSON field with null/empty values."""
        # Test with empty dict
        game_state = GameState(
            game_room_id=sample_game_room.id,
            current_turn="test",
            game_data={}
        )
        test_db.add(game_state)
        await test_db.commit()
        await test_db.refresh(game_state)

        assert game_state.game_data == {}

    async def test_json_field_complex_nested_data(
        self,
        test_db: AsyncSession,
        sample_game_room: GameRoom
    ):
        """Test JSON field with deeply nested complex data."""
        complex_data = {
            "game_info": {
                "type": "crime-scene",
                "difficulty": "hard"
            },
            "players": [
                {
                    "id": "ai-1",
                    "personality": "analytical",
                    "stats": {
                        "correct_deductions": 3,
                        "wrong_guesses": 1
                    }
                },
                {
                    "id": "ai-2",
                    "personality": "intuitive",
                    "stats": {
                        "correct_deductions": 2,
                        "wrong_guesses": 0
                    }
                }
            ],
            "evidence": {
                "physical": ["knife", "fingerprint"],
                "testimonial": ["witness_1_statement"]
            },
            "timeline": [
                {"time": "10:00", "event": "body_discovered"},
                {"time": "10:30", "event": "police_arrived"}
            ]
        }

        game_state = GameState(
            game_room_id=sample_game_room.id,
            current_turn="ai-1",
            game_data=complex_data
        )
        test_db.add(game_state)
        await test_db.commit()
        await test_db.refresh(game_state)

        # Verify complex nested data is preserved
        assert game_state.game_data["players"][0]["stats"]["correct_deductions"] == 3
        assert game_state.game_data["evidence"]["physical"][0] == "knife"
        assert len(game_state.game_data["timeline"]) == 2
