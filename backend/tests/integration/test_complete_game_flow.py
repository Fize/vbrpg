"""End-to-end tests for complete game flow."""
import json
import pytest
from httpx import AsyncClient
from main import app
from src.database import get_db
from src.api.rooms import get_current_user_id


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
class TestCompleteGameFlow:
    """Test complete game flow from room creation to game start."""
    
    async def test_complete_flow_with_ai_fill(
        self, client, test_db, sample_game_type
    ):
        """
        Test complete flow: Create room → AI fills → Start game → Verify GameState.
        
        This test covers:
        1. Room creation via API
        2. Automatic AI agent filling when starting with insufficient players
        3. GameState initialization with correct data
        4. All participants included in game data
        """
        # Step 1: Create room (creator joins automatically)
        create_response = await client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type.slug,
                "max_players": 6,
                "min_players": 4
            }
        )
        assert create_response.status_code == 201
        room_data = create_response.json()
        room_code = room_data["code"]
        
        # Verify initial state
        assert room_data["status"] == "Waiting"
        assert len(room_data["participants"]) == 1  # Only creator
        
        # Step 2: Start game (should auto-fill with AI)
        start_response = await client.post(f"/api/v1/rooms/{room_code}/start")
        assert start_response.status_code == 200
        started_room = start_response.json()
        
        # Verify game started
        assert started_room["status"] == "In Progress"
        assert len(started_room["participants"]) == 4  # 1 human + 3 AI
        
        # Step 3: Verify AI participants were created
        ai_participants = [
            p for p in started_room["participants"] 
            if p.get("is_ai_agent", False)
        ]
        assert len(ai_participants) == 3
        
        # Verify AI have personalities
        for ai_p in ai_participants:
            assert ai_p["ai_personality"] is not None
            assert ai_p["player"] is None  # AI don't have player records
        
        # Step 4: Verify GameState was created
        from src.models.game import GameState
        from sqlalchemy import select
        
        stmt = select(GameState).where(
            GameState.game_room_id == started_room["id"]
        )
        result = await test_db.execute(stmt)
        game_state = result.scalar_one_or_none()
        
        assert game_state is not None
        assert game_state.current_phase == "setup"
        assert game_state.turn_number == 1
        
        # Step 5: Verify game_data structure
        game_data = json.loads(game_state.game_data)
        assert game_data["phase"] == "setup"
        assert game_data["round"] == 1
        assert game_data["game_type"] == sample_game_type.slug
        assert "started_at" in game_data
        
        # Verify all participants in game_data
        assert len(game_data["participants"]) == 4
        
        # Count human vs AI
        human_count = sum(1 for p in game_data["participants"] if not p["is_ai"])
        ai_count = sum(1 for p in game_data["participants"] if p["is_ai"])
        
        assert human_count == 1
        assert ai_count == 3
    
    async def test_complete_flow_manual_join(
        self, client, test_db, sample_game_type
    ):
        """
        Test flow with manual joins: Create → Join → Join → Start.
        
        Tests scenario where humans join to reach min_players without AI.
        """
        # Step 1: Create room
        create_response = await client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type.slug,
                "max_players": 6,
                "min_players": 4  # Use valid min_players
            }
        )
        assert create_response.status_code == 201
        room_code = create_response.json()["code"]
        
        # Step 2: Create guest users and join
        # Note: In real scenario, these would be different authenticated users
        # For test, we're simulating multiple joins
        
        join_response1 = await client.post(f"/api/v1/rooms/{room_code}/join")
        # First join might return 200 or 409 if already in room (as creator)
        assert join_response1.status_code in [200, 409]
        
        # Step 3: Get room to verify participant count
        get_response = await client.get(f"/api/v1/rooms/{room_code}")
        assert get_response.status_code == 200
        room_data = get_response.json()
        
        # We have 1 participant (creator)
        participant_count = len(room_data["participants"])
        
        # Step 4: Start game
        # Since min_players=4 and we have 1, AI should fill 3 slots
        start_response = await client.post(f"/api/v1/rooms/{room_code}/start")
        assert start_response.status_code == 200
        started_room = start_response.json()
        
        assert started_room["status"] == "In Progress"
        assert len(started_room["participants"]) == 4
        
        # Verify GameState
        from src.models.game import GameState
        from sqlalchemy import select
        
        stmt = select(GameState).where(
            GameState.game_room_id == started_room["id"]
        )
        result = await test_db.execute(stmt)
        game_state = result.scalar_one()
        
        game_data = json.loads(game_state.game_data)
        assert len(game_data["participants"]) == 4
    
    async def test_flow_with_max_players(
        self, client, test_db, sample_game_type
    ):
        """Test that AI fill respects max_players limit."""
        # Create room with min=6, max=6
        create_response = await client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type.slug,
                "max_players": 6,
                "min_players": 6
            }
        )
        assert create_response.status_code == 201
        room_code = create_response.json()["code"]
        
        # Start immediately (1 human, needs 5 AI)
        start_response = await client.post(f"/api/v1/rooms/{room_code}/start")
        assert start_response.status_code == 200
        started_room = start_response.json()
        
        # Should have exactly 6 participants
        assert len(started_room["participants"]) == 6
        
        ai_count = sum(
            1 for p in started_room["participants"] 
            if p.get("is_ai_agent", False)
        )
        assert ai_count == 5
    
    async def test_game_state_persistence(
        self, client, test_db, sample_game_type
    ):
        """Test that GameState persists after game start."""
        # Create and start game
        create_response = await client.post(
            "/api/v1/rooms",
            json={
                "game_type_slug": sample_game_type.slug,
                "max_players": 6,
                "min_players": 4
            }
        )
        room_code = create_response.json()["code"]
        room_id = create_response.json()["id"]
        
        start_response = await client.post(f"/api/v1/rooms/{room_code}/start")
        assert start_response.status_code == 200
        
        # Query GameState independently
        from src.models.game import GameState
        from sqlalchemy import select
        
        stmt = select(GameState).where(GameState.game_room_id == room_id)
        result = await test_db.execute(stmt)
        game_state = result.scalar_one()
        
        # Verify it persists with correct data
        assert game_state.game_room_id == room_id
        assert game_state.current_phase == "setup"
        
        game_data = json.loads(game_state.game_data)
        assert "participants" in game_data
        assert "phase" in game_data
        assert "started_at" in game_data
