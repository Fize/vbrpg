"""Integration tests for single-player game flow.

单人模式端到端测试：
- 完整游戏流程
- 角色选择功能
- 游戏控制功能
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.game import GameRoom, GameState, GameRoomParticipant


@pytest.mark.asyncio
class TestSinglePlayerGameFlow:
    """Test complete single-player game flow."""

    async def test_create_room_and_start_game(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        sample_game_type
    ):
        """Test creating a room and starting a game."""
        # Create room
        create_response = await async_client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type.slug,
                "max_players": 4,
                "min_players": 4,
                "user_role": "spectator",
                "is_spectator_mode": True
            }
        )
        assert create_response.status_code == 201
        room_data = create_response.json()
        room_code = room_data["code"]

        # Start game (should auto-fill AI players)
        start_response = await async_client.post(f"/api/v1/rooms/{room_code}/start")
        assert start_response.status_code == 200
        started_room = start_response.json()
        assert started_room["status"] == "In Progress"

        # Verify AI participants were created
        stmt = select(GameRoomParticipant).where(
            GameRoomParticipant.game_room_id == room_data["id"],
            GameRoomParticipant.is_ai_agent == True
        )
        result = await test_db.execute(stmt)
        ai_participants = result.scalars().all()
        assert len(ai_participants) >= 4

    async def test_room_list_and_get(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        sample_game_type
    ):
        """Test listing and getting rooms."""
        # Create a room first
        create_response = await async_client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type.slug,
                "max_players": 4,
                "min_players": 4
            }
        )
        assert create_response.status_code == 201
        room_code = create_response.json()["code"]

        # List rooms
        list_response = await async_client.get("/api/v1/rooms")
        assert list_response.status_code == 200
        rooms = list_response.json()
        assert rooms["total"] >= 1

        # Get specific room
        get_response = await async_client.get(f"/api/v1/rooms/{room_code}")
        assert get_response.status_code == 200
        room = get_response.json()
        assert room["code"] == room_code


@pytest.mark.asyncio
class TestRoleSelection:
    """Test role selection for single-player mode."""

    async def test_get_available_roles(
        self,
        async_client: AsyncClient,
        sample_game_type
    ):
        """Test getting available roles for a game type."""
        response = await async_client.get(
            f"/api/v1/games/{sample_game_type.slug}/roles"
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "roles" in data
        assert len(data["roles"]) > 0
        assert "supports_spectating" in data

    async def test_select_spectator_role(
        self,
        async_client: AsyncClient,
        sample_game_type
    ):
        """Test selecting spectator role."""
        # Create room
        create_response = await async_client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type.slug,
                "max_players": 4,
                "min_players": 4
            }
        )
        room_code = create_response.json()["code"]

        # Select spectator role
        select_response = await async_client.post(
            f"/api/v1/rooms/{room_code}/select-role",
            json={"is_spectator": True}
        )
        assert select_response.status_code == 200
        room = select_response.json()
        assert room["user_role"] == "spectator" or room.get("is_spectator_mode") is True

    async def test_select_participant_role(
        self,
        async_client: AsyncClient,
        sample_game_type
    ):
        """Test selecting a participant role."""
        # Create room
        create_response = await async_client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type.slug,
                "max_players": 4,
                "min_players": 4
            }
        )
        room_code = create_response.json()["code"]

        # Select detective role
        select_response = await async_client.post(
            f"/api/v1/rooms/{room_code}/select-role",
            json={"role_id": "detective", "is_spectator": False}
        )
        assert select_response.status_code == 200


@pytest.mark.asyncio
class TestGameControl:
    """Test game control features (pause/resume/stop)."""

    async def test_pause_and_resume_game(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        sample_game_type
    ):
        """Test pausing and resuming a game."""
        # Create and start game
        create_response = await async_client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type.slug,
                "max_players": 4,
                "min_players": 4
            }
        )
        room_code = create_response.json()["code"]
        
        await async_client.post(f"/api/v1/rooms/{room_code}/start")

        # Pause game
        pause_response = await async_client.post(f"/api/v1/rooms/{room_code}/pause")
        assert pause_response.status_code == 200
        assert pause_response.json()["status"] == "Paused"

        # Resume game
        resume_response = await async_client.post(f"/api/v1/rooms/{room_code}/resume")
        assert resume_response.status_code == 200
        assert resume_response.json()["status"] == "In Progress"

    async def test_stop_game(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        sample_game_type
    ):
        """Test stopping a game."""
        # Create and start game
        create_response = await async_client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type.slug,
                "max_players": 4,
                "min_players": 4
            }
        )
        room_code = create_response.json()["code"]
        
        await async_client.post(f"/api/v1/rooms/{room_code}/start")

        # Stop game
        stop_response = await async_client.post(f"/api/v1/rooms/{room_code}/stop")
        assert stop_response.status_code == 200
        assert stop_response.json()["status"] == "Completed"

    async def test_cannot_pause_waiting_game(
        self,
        async_client: AsyncClient,
        sample_game_type
    ):
        """Test that pausing a waiting game fails."""
        # Create room without starting
        create_response = await async_client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type.slug,
                "max_players": 4,
                "min_players": 4
            }
        )
        room_code = create_response.json()["code"]

        # Try to pause
        pause_response = await async_client.post(f"/api/v1/rooms/{room_code}/pause")
        assert pause_response.status_code == 400

    async def test_cannot_resume_non_paused_game(
        self,
        async_client: AsyncClient,
        sample_game_type
    ):
        """Test that resuming a non-paused game fails."""
        # Create and start game
        create_response = await async_client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type.slug,
                "max_players": 4,
                "min_players": 4
            }
        )
        room_code = create_response.json()["code"]
        
        await async_client.post(f"/api/v1/rooms/{room_code}/start")

        # Try to resume without pausing
        resume_response = await async_client.post(f"/api/v1/rooms/{room_code}/resume")
        assert resume_response.status_code == 400


@pytest.mark.asyncio
class TestAIAgentManagement:
    """Test AI agent management in single-player mode."""

    async def test_add_ai_agent(
        self,
        async_client: AsyncClient,
        sample_game_type
    ):
        """Test adding an AI agent to a room."""
        # Create room
        create_response = await async_client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type.slug,
                "max_players": 6,
                "min_players": 4
            }
        )
        room_code = create_response.json()["code"]

        # Add AI agent
        add_response = await async_client.post(f"/api/v1/rooms/{room_code}/ai-agents")
        assert add_response.status_code == 201
        ai_data = add_response.json()
        assert "ai_agent" in ai_data
        assert ai_data["room_code"] == room_code

    async def test_remove_ai_agent(
        self,
        async_client: AsyncClient,
        sample_game_type
    ):
        """Test removing an AI agent from a room."""
        # Create room
        create_response = await async_client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type.slug,
                "max_players": 6,
                "min_players": 4
            }
        )
        room_code = create_response.json()["code"]

        # Add AI agent
        add_response = await async_client.post(f"/api/v1/rooms/{room_code}/ai-agents")
        ai_data = add_response.json()

        # Get room to find participant ID
        room_response = await async_client.get(f"/api/v1/rooms/{room_code}")
        room = room_response.json()
        
        # Find AI participant
        ai_participant = next(
            (p for p in room["participants"] if p["is_ai_agent"]),
            None
        )
        assert ai_participant is not None

        # Remove AI agent
        remove_response = await async_client.delete(
            f"/api/v1/rooms/{room_code}/ai-agents/{ai_participant['id']}"
        )
        assert remove_response.status_code == 204
