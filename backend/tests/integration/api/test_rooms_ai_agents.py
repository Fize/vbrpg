"""Integration tests for POST/DELETE /rooms/{code}/ai-agents API endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from src.api.rooms import get_current_user_id
from src.database import get_db
from src.models.game import GameRoom, GameRoomParticipant
from src.models.user import Player


@pytest.fixture
async def owner_room(test_db: AsyncSession, sample_game_type, sample_player):
    """Create a room where sample_player is the owner."""
    room = GameRoom(
        code="AITEST",
        status="Waiting",
        max_players=4,
        min_players=2,
        game_type_id=sample_game_type.id,
        owner_id=sample_player.id,
        current_participant_count=1,
        ai_agent_counter=0
    )
    test_db.add(room)
    await test_db.flush()
    
    owner_participant = GameRoomParticipant(
        game_room_id=room.id,
        player_id=sample_player.id,
        is_owner=True,
        is_ai_agent=False
    )
    test_db.add(owner_participant)
    
    await test_db.commit()
    await test_db.refresh(room)
    return room


@pytest.fixture
async def non_owner_player(test_db: AsyncSession):
    """Create a non-owner player."""
    player = Player(
        id="non-owner-ai",
        username="NonOwner",
        is_guest=True
    )
    test_db.add(player)
    await test_db.commit()
    return player


@pytest.fixture
async def full_room(test_db: AsyncSession, sample_game_type, sample_player):
    """Create a room at max capacity."""
    room = GameRoom(
        code="FULL01",
        status="Waiting",
        max_players=2,
        min_players=2,
        game_type_id=sample_game_type.id,
        owner_id=sample_player.id,
        current_participant_count=2,
        ai_agent_counter=0
    )
    test_db.add(room)
    await test_db.flush()
    
    # Add owner
    owner_p = GameRoomParticipant(
        game_room_id=room.id,
        player_id=sample_player.id,
        is_owner=True,
        is_ai_agent=False
    )
    test_db.add(owner_p)
    
    # Add second player
    p2 = Player(id="full-p2", username="FullP2", is_guest=True)
    test_db.add(p2)
    await test_db.flush()
    
    p2_participant = GameRoomParticipant(
        game_room_id=room.id,
        player_id=p2.id,
        is_owner=False,
        is_ai_agent=False
    )
    test_db.add(p2_participant)
    
    await test_db.commit()
    await test_db.refresh(room)
    return room


@pytest.fixture
async def in_progress_room(test_db: AsyncSession, sample_game_type, sample_player):
    """Create a room with game in progress."""
    room = GameRoom(
        code="INPROG",
        status="InProgress",
        max_players=4,
        min_players=2,
        game_type_id=sample_game_type.id,
        owner_id=sample_player.id,
        current_participant_count=1,
        ai_agent_counter=0
    )
    test_db.add(room)
    await test_db.flush()
    
    participant = GameRoomParticipant(
        game_room_id=room.id,
        player_id=sample_player.id,
        is_owner=True,
        is_ai_agent=False
    )
    test_db.add(participant)
    
    await test_db.commit()
    await test_db.refresh(room)
    return room


@pytest.fixture
async def client(test_db, sample_player):
    """Create a test HTTP client."""
    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user_id] = lambda: sample_player.id
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestAddAIAgentAPI:
    """Test POST /rooms/{code}/ai-agents endpoint."""
    
    async def test_add_ai_agent_success_returns_201(
        self, client, owner_room
    ):
        """Test owner can add AI agent successfully (AS1)."""
        response = await client.post(
            f"/api/v1/rooms/{owner_room.code}/ai-agents"
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify AI agent data in response
        assert "ai_agent" in data
        assert "room_code" in data
        assert data["room_code"] == owner_room.code
        assert data["ai_agent"]["player_type"] == "ai"
        assert "AI玩家" in data["ai_agent"]["username"]  # Sequential name
    
    async def test_add_ai_agent_non_owner_returns_403(
        self, client, owner_room, non_owner_player, test_db
    ):
        """Test non-owner cannot add AI agent (AS1 permission check)."""
        # Override current user to non-owner
        app.dependency_overrides[get_current_user_id] = lambda: non_owner_player.id
        
        response = await client.post(
            f"/api/v1/rooms/{owner_room.code}/ai-agents"
        )
        
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "owner" in data["detail"].lower() or "permission" in data["detail"].lower()
    
    async def test_add_ai_agent_full_room_returns_409(
        self, client, full_room
    ):
        """Test cannot add AI agent to full room."""
        response = await client.post(
            f"/api/v1/rooms/{full_room.code}/ai-agents"
        )
        
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data
        assert "full" in data["detail"].lower() or "capacity" in data["detail"].lower()
    
    async def test_add_ai_agent_in_progress_returns_409(
        self, client, in_progress_room
    ):
        """Test cannot add AI agent after game starts."""
        response = await client.post(
            f"/api/v1/rooms/{in_progress_room.code}/ai-agents"
        )
        
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data
        detail_lower = data["detail"].lower()
        assert ("progress" in detail_lower or 
                "started" in detail_lower or
                "starts" in detail_lower or
                "inprogress" in detail_lower)
    
    async def test_add_multiple_ai_agents_sequential_names(
        self, client, owner_room
    ):
        """Test adding multiple AI agents creates sequential names (FR-007)."""
        # Add first AI agent
        response1 = await client.post(
            f"/api/v1/rooms/{owner_room.code}/ai-agents"
        )
        assert response1.status_code == 201
        agent1_name = response1.json()["ai_agent"]["username"]
        assert "AI玩家1" == agent1_name
        
        # Add second AI agent
        response2 = await client.post(
            f"/api/v1/rooms/{owner_room.code}/ai-agents"
        )
        assert response2.status_code == 201
        agent2_name = response2.json()["ai_agent"]["username"]
        assert "AI玩家2" == agent2_name


@pytest.mark.asyncio
class TestRemoveAIAgentAPI:
    """Test DELETE /rooms/{code}/ai-agents/{agent_id} endpoint."""
    
    async def test_remove_ai_agent_success_returns_204(
        self, client, owner_room, test_db
    ):
        """Test owner can remove AI agent successfully (AS2)."""
        # First add an AI agent
        add_response = await client.post(
            f"/api/v1/rooms/{owner_room.code}/ai-agents"
        )
        assert add_response.status_code == 201
        ai_agent_id = add_response.json()["ai_agent"]["id"]
        
        # Remove the AI agent
        response = await client.delete(
            f"/api/v1/rooms/{owner_room.code}/ai-agents/{ai_agent_id}"
        )
        
        assert response.status_code == 204
    
    async def test_remove_ai_agent_non_owner_returns_403(
        self, client, owner_room, non_owner_player, test_db
    ):
        """Test non-owner cannot remove AI agent."""
        # Owner adds AI agent
        add_response = await client.post(
            f"/api/v1/rooms/{owner_room.code}/ai-agents"
        )
        assert add_response.status_code == 201
        ai_agent_id = add_response.json()["ai_agent"]["id"]
        
        # Non-owner tries to remove
        app.dependency_overrides[get_current_user_id] = lambda: non_owner_player.id
        
        response = await client.delete(
            f"/api/v1/rooms/{owner_room.code}/ai-agents/{ai_agent_id}"
        )
        
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
    
    async def test_remove_nonexistent_ai_agent_returns_404(
        self, client, owner_room
    ):
        """Test removing non-existent AI agent returns 404."""
        response = await client.delete(
            f"/api/v1/rooms/{owner_room.code}/ai-agents/nonexistent-id"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    async def test_remove_ai_agent_in_progress_returns_409(
        self, client, in_progress_room, test_db
    ):
        """Test cannot remove AI agent after game starts."""
        # Add AI agent to in-progress room (via direct DB manipulation)
        from src.models.user import Player
        from src.models.game import GameRoomParticipant
        
        ai_player = Player(id="prog-ai", username="AI玩家1", is_guest=True)
        test_db.add(ai_player)
        await test_db.flush()
        
        ai_participant = GameRoomParticipant(
            game_room_id=in_progress_room.id,
            player_id=ai_player.id,
            is_owner=False,
            is_ai_agent=True
        )
        test_db.add(ai_participant)
        await test_db.commit()
        
        response = await client.delete(
            f"/api/v1/rooms/{in_progress_room.code}/ai-agents/{ai_player.id}"
        )
        
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data
