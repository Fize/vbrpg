"""Integration tests for DELETE /rooms/{code}/participants/{player_id} API endpoint."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from src.api.rooms import get_current_user_id
from src.database import get_db
from src.models.game import GameRoom, GameRoomParticipant
from src.models.user import Player


@pytest.fixture
async def client(test_db, sample_player):
    """Create a test HTTP client."""
    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user_id] = lambda: sample_player.id
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def not_in_room_player(test_db: AsyncSession):
    """Create a player not in any room."""
    player = Player(
        id="not-in-room-player",
        username="NotInRoomPlayer",
        is_guest=True
    )
    test_db.add(player)
    await test_db.commit()
    return player


@pytest.fixture
async def room_with_two_players(test_db: AsyncSession, sample_game_type, sample_player):
    """Create a room with owner and one other player."""
    # Create second player
    second_player = Player(
        id="leave-player-2",
        username="LeavePlayer2",
        is_guest=True
    )
    test_db.add(second_player)
    
    # Create room
    room = GameRoom(
        code="LEAVE1",
        status="Waiting",
        max_players=4,
        min_players=2,
        game_type_id=sample_game_type.id,
        owner_id=sample_player.id,
        current_participant_count=2,
        ai_agent_counter=0
    )
    test_db.add(room)
    await test_db.flush()
    
    # Add owner
    owner_participant = GameRoomParticipant(
        game_room_id=room.id,
        player_id=sample_player.id,
        is_owner=True,
        is_ai_agent=False
    )
    test_db.add(owner_participant)
    
    # Add second player
    second_participant = GameRoomParticipant(
        game_room_id=room.id,
        player_id=second_player.id,
        is_owner=False,
        is_ai_agent=False
    )
    test_db.add(second_participant)
    
    await test_db.commit()
    await test_db.refresh(room)
    return room, second_player


@pytest.fixture
async def in_progress_room_for_leave(test_db: AsyncSession, sample_game_type, sample_player):
    """Create a room with game in progress."""
    room = GameRoom(
        code="LEAVE2",
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


@pytest.mark.asyncio
class TestLeaveRoomAPI:
    """Test DELETE /rooms/{code}/participants/{player_id} endpoint."""
    
    async def test_leave_room_success_returns_204(
        self, client, room_with_two_players
    ):
        """Test successful leave returns 204 No Content."""
        room, second_player = room_with_two_players
        
        # Second player leaves
        app.dependency_overrides[get_current_user_id] = lambda: second_player.id
        
        response = await client.delete(
            f"/api/v1/rooms/{room.code}/participants/{second_player.id}"
        )
        
        assert response.status_code == 204
        assert response.content == b''  # No content body
    
    async def test_leave_nonexistent_room_returns_404(
        self, client, sample_player
    ):
        """Test leaving non-existent room returns 404."""
        response = await client.delete(
            f"/api/v1/rooms/NOEXIST/participants/{sample_player.id}"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    async def test_leave_when_not_in_room_returns_404(
        self, client, room_with_two_players, not_in_room_player
    ):
        """Test leaving when player is not in room returns 404."""
        room, _ = room_with_two_players
        
        # Use not_in_room_player for test
        app.dependency_overrides[get_current_user_id] = lambda: not_in_room_player.id
        
        response = await client.delete(
            f"/api/v1/rooms/{room.code}/participants/{not_in_room_player.id}"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    async def test_leave_in_progress_game_returns_409(
        self, client, in_progress_room_for_leave
    ):
        """Test leaving in-progress game returns 409."""
        room = in_progress_room_for_leave
        
        response = await client.delete(
            f"/api/v1/rooms/{room.code}/participants/{room.owner_id}"
        )
        
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data
        detail_lower = data["detail"].lower()
        assert ("inprogress" in detail_lower or "in progress" in detail_lower or 
                "started" in detail_lower)
