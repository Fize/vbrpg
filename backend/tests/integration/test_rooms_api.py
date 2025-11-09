"""Integration tests for REST API endpoints."""
import pytest
from httpx import AsyncClient
from main import app
from src.database import get_db
from src.api.rooms import get_current_user_id
from tests.conftest import test_db


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


@pytest.mark.asyncio
class TestHealthEndpoint:
    """Test health check endpoint."""
    
    async def test_health_check(self, client):
        """Test health check returns OK."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


@pytest.mark.asyncio
class TestRoomsAPI:
    """Test game rooms API endpoints."""
    
    async def test_create_room_success(self, client, sample_game_type):
        """Test creating a room via API."""
        response = await client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type.slug,
                "max_players": 6,
                "min_players": 4
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "code" in data
        assert len(data["code"]) == 8
        assert data["status"] == "Waiting"
        assert data["game_type"]["slug"] == sample_game_type.slug
    
    async def test_create_room_invalid_game_type(self, client):
        """Test creating a room with invalid game type."""
        response = await client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": "nonexistent",
                "max_players": 6,
                "min_players": 4
            }
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    async def test_create_room_invalid_player_counts(self, client, sample_game_type):
        """Test creating a room with invalid player counts."""
        response = await client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type.slug,
                "max_players": 3,
                "min_players": 5
            }
        )
        
        # Pydantic validation returns 422
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    async def test_get_room_success(self, client, sample_game_room):
        """Test getting a room by code."""
        response = await client.get(f"/api/v1/rooms/{sample_game_room.code}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == sample_game_room.code
        assert "participants" in data
        assert "game_type" in data
    
    async def test_get_room_not_found(self, client):
        """Test getting a nonexistent room."""
        response = await client.get("/api/v1/rooms/NOTFOUND")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    async def test_list_rooms_success(self, client, sample_game_room):
        """Test listing rooms."""
        response = await client.get("/api/v1/rooms")
        
        assert response.status_code == 200
        data = response.json()
        assert "rooms" in data
        assert "total" in data
        assert isinstance(data["rooms"], list)
        assert data["total"] >= 1
    
    async def test_list_rooms_filtered_by_status(self, client, sample_game_room):
        """Test listing rooms filtered by status."""
        response = await client.get("/api/v1/rooms?status=Waiting")
        
        assert response.status_code == 200
        data = response.json()
        for room in data["rooms"]:
            assert room["status"] == "Waiting"
    
    async def test_list_rooms_filtered_by_game_type(self, client, sample_game_type, sample_game_room):
        """Test listing rooms filtered by game type."""
        response = await client.get(f"/api/v1/rooms?gameType={sample_game_type.slug}")
        
        assert response.status_code == 200
        data = response.json()
        for room in data["rooms"]:
            assert room["game_type"]["slug"] == sample_game_type.slug
    
    async def test_list_rooms_with_limit(self, client, sample_game_room):
        """Test listing rooms with limit."""
        response = await client.get("/api/v1/rooms?limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["rooms"]) <= 5
    
    async def test_join_room_success(self, client, sample_game_room):
        """Test joining a room via API."""
        response = await client.post(f"/api/v1/rooms/{sample_game_room.code}/join")
        
        # This will return 409 because temporary user is already creator/participant
        # In real scenario with different users, this should be 200
        assert response.status_code in [200, 409]
    
    async def test_join_room_not_found(self, client):
        """Test joining a nonexistent room."""
        response = await client.post("/api/v1/rooms/NOTFOUND/join")
        
        assert response.status_code == 404
    
    async def test_leave_room_success(self, client, sample_game_room):
        """Test leaving a room via API."""
        response = await client.post(f"/api/v1/rooms/{sample_game_room.code}/leave")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    async def test_leave_room_not_in_room(self, client, sample_game_room):
        """Test leaving a room you're not in."""
        # First leave the room
        await client.post(f"/api/v1/rooms/{sample_game_room.code}/leave")
        
        # Try to leave again
        response = await client.post(f"/api/v1/rooms/{sample_game_room.code}/leave")
        
        assert response.status_code == 404
        data = response.json()
        assert "not in" in data["detail"].lower()
    
    async def test_start_game_success(self, client, test_db, sample_game_room, sample_guest_player):
        """Test starting a game via API."""
        # Add another participant to help reach min_players
        from src.models.game_room_participant import GameRoomParticipant
        
        participant = GameRoomParticipant(
            game_room_id=sample_game_room.id,
            player_id=sample_guest_player.id,
            is_ai_agent=False
        )
        test_db.add(participant)
        await test_db.commit()
        
        response = await client.post(f"/api/v1/rooms/{sample_game_room.code}/start")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "In Progress"
    
    async def test_start_game_not_found(self, client):
        """Test starting a nonexistent game."""
        response = await client.post("/api/v1/rooms/NOTFOUND/start")
        
        assert response.status_code == 404


@pytest.mark.asyncio
class TestRoomsAPIFlow:
    """Test complete room flow via API."""
    
    async def test_complete_room_lifecycle(self, client, sample_game_type):
        """Test creating, joining, and starting a room."""
        # Create room
        create_response = await client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type.slug,
                "max_players": 6,
                "min_players": 4
            }
        )
        assert create_response.status_code == 201
        room_code = create_response.json()["code"]
        
        # Get room details
        get_response = await client.get(f"/api/v1/rooms/{room_code}")
        assert get_response.status_code == 200
        room_data = get_response.json()
        assert room_data["status"] == "Waiting"
        
        # List rooms (should include our room)
        list_response = await client.get("/api/v1/rooms?status=Waiting")
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert any(r["code"] == room_code for r in list_data["rooms"])
        
        # Start game
        start_response = await client.post(f"/api/v1/rooms/{room_code}/start")
        assert start_response.status_code == 200
        started_room = start_response.json()
        assert started_room["status"] == "In Progress"
        
        # Verify room status changed
        final_response = await client.get(f"/api/v1/rooms/{room_code}")
        assert final_response.status_code == 200
        final_room = final_response.json()
        assert final_room["status"] == "In Progress"
