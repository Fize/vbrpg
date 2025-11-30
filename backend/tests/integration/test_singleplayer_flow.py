"""Integration tests for single-player game flow.

单人模式端到端测试：
- 完整游戏流程
- 角色选择功能
- 游戏控制功能
"""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from src.database import get_db
from src.models.game import GameRoom, GameState, GameRoomParticipant


@pytest.fixture
async def client(test_db):
    """Create a test HTTP client."""
    # Override database dependency
    app.dependency_overrides[get_db] = lambda: test_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestSinglePlayerGameFlow:
    """Test complete single-player game flow."""

    async def test_create_room_and_start_game(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        sample_game_type
    ):
        """Test creating a room and starting a game."""
        # Create room
        create_response = await client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type["slug"],
                "max_players": 10,
                "min_players": 10,
                "user_role": "spectator",
                "is_spectator_mode": True
            }
        )
        assert create_response.status_code == 201
        room_data = create_response.json()
        room_code = room_data["code"]

        # Start game (should auto-fill AI players)
        start_response = await client.post(f"/api/v1/rooms/{room_code}/start")
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
        client: AsyncClient,
        test_db: AsyncSession,
        sample_game_type
    ):
        """Test room list and get functionality."""
        # Create room
        create_response = await client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type["slug"],
                "max_players": 10,
                "min_players": 10
            }
        )
        assert create_response.status_code == 201
        room_data = create_response.json()
        room_code = room_data["code"]

        # List rooms
        list_response = await client.get("/api/v1/rooms")
        assert list_response.status_code == 200
        rooms_data = list_response.json()
        rooms = rooms_data["rooms"]
        assert len(rooms) >= 1
        assert any(r["code"] == room_code for r in rooms)

        # Get room details
        get_response = await client.get(f"/api/v1/rooms/{room_code}")
        assert get_response.status_code == 200
        room_details = get_response.json()
        assert room_details["code"] == room_code


@pytest.mark.asyncio
class TestRoleSelection:
    """Test role selection functionality."""

    async def test_get_available_roles(
        self,
        client: AsyncClient,
        sample_game_type
    ):
        """Test getting available roles for a game type."""
        game_slug = sample_game_type["slug"]
        response = await client.get(
            f"/api/v1/games/{game_slug}/roles"
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "roles" in data
        roles = data["roles"]
        assert len(roles) > 0
        
        # Check role structure
        for role in roles:
            assert "id" in role
            assert "name" in role
            assert "description" in role

    async def test_select_spectator_role(
        self,
        client: AsyncClient,
        sample_game_type
    ):
        """Test selecting spectator role."""
        # Create room
        create_response = await client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type["slug"],
                "max_players": 10,
                "min_players": 10
            }
        )
        room_code = create_response.json()["code"]
        
        # Select spectator role
        select_response = await client.post(
            f"/api/v1/rooms/{room_code}/select-role",
            json={"is_spectator": True}
        )
        assert select_response.status_code == 200
        
        # Verify room is in spectator mode
        get_response = await client.get(f"/api/v1/rooms/{room_code}")
        room_data = get_response.json()
        assert room_data["user_role"] == "spectator"
        assert room_data["is_spectator_mode"] is True

    async def test_select_participant_role(
        self,
        client: AsyncClient,
        sample_game_type
    ):
        """Test selecting participant role."""
        # Create room
        create_response = await client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type["slug"],
                "max_players": 10,
                "min_players": 10
            }
        )
        room_code = create_response.json()["code"]
        
        # Select participant role
        select_response = await client.post(
            f"/api/v1/rooms/{room_code}/select-role",
            json={"is_spectator": False, "role_id": "detective"}
        )
        assert select_response.status_code == 200
        
        # Verify room is not in spectator mode
        get_response = await client.get(f"/api/v1/rooms/{room_code}")
        room_data = get_response.json()
        assert room_data["user_role"] == "detective"
        assert room_data["is_spectator_mode"] is False


@pytest.mark.asyncio
class TestGameControl:
    """Test game control functionality."""

    async def test_pause_and_resume_game(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        sample_game_type
    ):
        """Test pausing and resuming a game."""
        # Create and start game
        create_response = await client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type["slug"],
                "max_players": 10,
                "min_players": 10
            }
        )
        room_code = create_response.json()["code"]
        
        await client.post(f"/api/v1/rooms/{room_code}/start")
        
        # Pause game
        pause_response = await client.post(f"/api/v1/rooms/{room_code}/pause")
        assert pause_response.status_code == 200
        
        # Verify game is paused
        get_response = await client.get(f"/api/v1/rooms/{room_code}")
        room_data = get_response.json()
        assert room_data["status"] == "Paused"
        
        # Resume game
        resume_response = await client.post(f"/api/v1/rooms/{room_code}/resume")
        assert resume_response.status_code == 200
        
        # Verify game is resumed
        get_response = await client.get(f"/api/v1/rooms/{room_code}")
        room_data = get_response.json()
        assert room_data["status"] == "In Progress"

    async def test_stop_game(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        sample_game_type
    ):
        """Test stopping a game."""
        # Create and start game
        create_response = await client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type["slug"],
                "max_players": 10,
                "min_players": 10
            }
        )
        room_code = create_response.json()["code"]
        
        await client.post(f"/api/v1/rooms/{room_code}/start")
        
        # Stop game
        stop_response = await client.post(f"/api/v1/rooms/{room_code}/stop")
        assert stop_response.status_code == 200
        
        # Verify game is stopped
        get_response = await client.get(f"/api/v1/rooms/{room_code}")
        room_data = get_response.json()
        assert room_data["status"] == "Completed"

    async def test_cannot_pause_waiting_game(
        self,
        client: AsyncClient,
        sample_game_type
    ):
        """Test that cannot pause a waiting game."""
        # Create room
        create_response = await client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type["slug"],
                "max_players": 10,
                "min_players": 10
            }
        )
        room_code = create_response.json()["code"]
        
        # Try to pause waiting game
        pause_response = await client.post(f"/api/v1/rooms/{room_code}/pause")
        assert pause_response.status_code == 400

    async def test_cannot_resume_non_paused_game(
        self,
        client: AsyncClient,
        sample_game_type
    ):
        """Test that cannot resume a non-paused game."""
        # Create and start game
        create_response = await client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type["slug"],
                "max_players": 10,
                "min_players": 10
            }
        )
        room_code = create_response.json()["code"]
        
        await client.post(f"/api/v1/rooms/{room_code}/start")
        
        # Try to resume non-paused game
        resume_response = await client.post(f"/api/v1/rooms/{room_code}/resume")
        assert resume_response.status_code == 400


@pytest.mark.asyncio
class TestAIAgentManagement:
    """Test AI agent management functionality."""

    async def test_add_ai_agent(
        self,
        client: AsyncClient,
        sample_game_type
    ):
        """Test adding an AI agent."""
        # Create room
        create_response = await client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type["slug"],
                "max_players": 10,
                "min_players": 10
            }
        )
        room_code = create_response.json()["code"]
        
        # Add AI agent
        add_response = await client.post(f"/api/v1/rooms/{room_code}/ai-agents")
        assert add_response.status_code == 201
        
        # Verify AI agent was added
        get_response = await client.get(f"/api/v1/rooms/{room_code}")
        room_data = get_response.json()
        assert len(room_data["participants"]) > 0

    async def test_remove_ai_agent(
        self,
        client: AsyncClient,
        sample_game_type
    ):
        """Test removing an AI agent."""
        # Create room
        create_response = await client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type["slug"],
                "max_players": 10,
                "min_players": 10
            }
        )
        room_code = create_response.json()["code"]
        
        # Add AI agent first and get its ID
        add_response = await client.post(f"/api/v1/rooms/{room_code}/ai-agents")
        assert add_response.status_code == 201
        agent_id = add_response.json()["ai_agent"]["id"]
        
        # Remove AI agent
        remove_response = await client.delete(f"/api/v1/rooms/{room_code}/ai-agents/{agent_id}")
        assert remove_response.status_code == 204