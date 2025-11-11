"""Integration tests for POST /rooms/{code}/join API endpoint."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from src.api.rooms import get_current_user_id
from src.database import get_db
from src.models.game_room import GameRoom
from src.models.game_room_participant import GameRoomParticipant
from src.models.player import Player


@pytest.fixture
async def client(test_db, sample_player):
    """Create a test HTTP client."""
    # Override database dependency
    app.dependency_overrides[get_db] = lambda: test_db
    
    # Override auth to use test player
    app.dependency_overrides[get_current_user_id] = lambda: sample_player.id
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def second_player(test_db: AsyncSession):
    """Create a second test player for join tests."""
    player = Player(
        id="test-player-2",
        username="Player2",
        is_guest=True
    )
    test_db.add(player)
    await test_db.commit()
    await test_db.refresh(player)
    return player


@pytest.fixture
async def waiting_room(test_db: AsyncSession, sample_game_type, sample_player):
    """Create a waiting room with owner."""
    room = GameRoom(
        code="ABC123",
        status="Waiting",
        max_players=4,
        min_players=2,
        game_type_id=sample_game_type.id,
        owner_id=sample_player.id,
        current_participant_count=1,
        ai_agent_counter=0
    )
    test_db.add(room)
    await test_db.flush()  # Flush to get room.id
    
    # Add owner as participant
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
async def full_room(test_db: AsyncSession, sample_game_type, sample_player):
    """Create a room at max capacity."""
    room = GameRoom(
        code="FULL99",
        status="Waiting",
        max_players=2,
        min_players=2,
        game_type_id=sample_game_type.id,
        owner_id=sample_player.id,
        current_participant_count=2,
        ai_agent_counter=0
    )
    test_db.add(room)
    await test_db.flush()  # Flush to get room.id
    
    # Add 2 participants (at max capacity)
    for i in range(2):
        player = Player(
            id=f"full-player-{i}",
            username=f"FullPlayer{i}",
            is_guest=True
        )
        test_db.add(player)
        
    await test_db.flush()  # Flush to get player IDs
    
    for i in range(2):
        participant = GameRoomParticipant(
            game_room_id=room.id,
            player_id=f"full-player-{i}",
            is_owner=(i == 0),
            is_ai_agent=False
        )
        test_db.add(participant)
    
    await test_db.commit()
    await test_db.refresh(room)
    return room


@pytest.fixture
async def in_progress_room(test_db: AsyncSession, sample_game_type, sample_player):
    """Create a room with game in progress."""
    room = GameRoom(
        code="PROG99",
        status="InProgress",
        max_players=4,
        min_players=2,
        game_type_id=sample_game_type.id,
        owner_id=sample_player.id,
        current_participant_count=2,
        ai_agent_counter=0
    )
    test_db.add(room)
    await test_db.flush()  # Flush to get room.id
    
    # Add owner as participant
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
class TestJoinRoomAPI:
    """Test POST /rooms/{code}/join endpoint."""
    
    async def test_join_room_success(self, client, waiting_room, second_player):
        """Test successful join returns 200 with room and participants (AS1)."""
        # Override auth to use second player
        app.dependency_overrides[get_current_user_id] = lambda: second_player.id
        
        response = await client.post(f"/api/v1/rooms/{waiting_room.code}/join")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "room" in data
        assert "participants" in data
        assert "is_owner" in data
        
        # Verify room data
        assert data["room"]["code"] == waiting_room.code
        assert data["room"]["status"] == "Waiting"
        
        # Verify participant count increased
        assert len(data["participants"]) == 2
        
        # Verify second player is not owner
        assert data["is_owner"] is False
        
        # Verify second player is in participants list
        player_ids = [p["player"]["id"] for p in data["participants"]]
        assert second_player.id in player_ids
    
    async def test_join_nonexistent_room_returns_404(self, client, second_player):
        """Test joining non-existent room returns 404 (AS4)."""
        # Override auth to use second player
        app.dependency_overrides[get_current_user_id] = lambda: second_player.id
        
        response = await client.post("/api/v1/rooms/NOEXIST/join")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    async def test_join_full_room_returns_409(self, client, full_room, second_player):
        """Test joining full room returns 409 (AS3, SC-006)."""
        # Create a new player not in room
        new_player = Player(
            id="new-player-join",
            username="NewPlayer",
            is_guest=True
        )
        async for db in get_db():
            db.add(new_player)
            await db.commit()
            break
        
        # Override auth to use new player
        app.dependency_overrides[get_current_user_id] = lambda: new_player.id
        
        response = await client.post(f"/api/v1/rooms/{full_room.code}/join")
        
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data
        assert "full" in data["detail"].lower()
    
    async def test_join_in_progress_game_returns_409(self, client, in_progress_room, second_player):
        """Test joining in-progress game returns 409 (FR-004)."""
        # Override auth to use second player
        app.dependency_overrides[get_current_user_id] = lambda: second_player.id
        
        response = await client.post(f"/api/v1/rooms/{in_progress_room.code}/join")
        
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data
        assert ("started" in data["detail"].lower() or "progress" in data["detail"].lower())
    
    async def test_duplicate_join_returns_409(self, client, waiting_room, sample_player):
        """Test duplicate join (player already in room) returns 409 (FR-012)."""
        # sample_player is already the owner/in the room
        # Override auth to use sample player (already in room)
        app.dependency_overrides[get_current_user_id] = lambda: sample_player.id
        
        response = await client.post(f"/api/v1/rooms/{waiting_room.code}/join")
        
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data
        assert ("already" in data["detail"].lower() or "duplicate" in data["detail"].lower())
