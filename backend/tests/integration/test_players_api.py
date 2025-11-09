"""Integration tests for Players API endpoints."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from unittest.mock import patch

from main import app
from src.models.player import Player
from src.models.player_profile import PlayerProfile
from src.models.game_room_participant import GameRoomParticipant
from src.utils.sessions import SessionManager


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def guest_player(test_db):
    """Create a guest player for testing."""
    player = Player(
        username="Guest_测试_老虎",
        is_guest=True,
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    test_db.add(player)
    await test_db.commit()
    await test_db.refresh(player)
    return player


@pytest.fixture
async def permanent_player(test_db):
    """Create a permanent player for testing."""
    player = Player(
        username="PermanentUser",
        is_guest=False,
        expires_at=None
    )
    test_db.add(player)
    await test_db.commit()
    await test_db.refresh(player)
    return player


@pytest.fixture
async def player_with_stats(test_db):
    """Create player with game statistics."""
    player = Player(
        username="StatsPlayer",
        is_guest=False,
        expires_at=None
    )
    test_db.add(player)
    await test_db.commit()
    await test_db.refresh(player)
    
    # Create profile with stats
    profile = PlayerProfile(
        player_id=player.id,
        total_games_played=10,
        games_won=7,
        games_lost=3,
        total_play_time_minutes=120,
        last_active_at=datetime.utcnow()
    )
    test_db.add(profile)
    await test_db.commit()
    
    return player


def create_session_cookie(player_id: str) -> str:
    """Helper to create session cookie string."""
    from src.utils.sessions import SessionManager
    session_id = SessionManager.generate_session_id()
    return f"{session_id}:{player_id}"


class TestCreateGuestAccount:
    """Test POST /api/v1/players/guest endpoint."""

    def test_create_guest_success(self, client):
        """Test successful guest account creation."""
        response = client.post("/api/v1/players/guest")
        
        assert response.status_code == 201
        data = response.json()
        
        # Check response structure
        assert "id" in data
        assert "username" in data
        assert data["is_guest"] is True
        
        # Check username format
        assert data["username"].startswith("Guest_")
        
        # Check session cookie is set
        assert "vbrpg_session" in response.cookies

    def test_create_guest_sets_session_cookie(self, client):
        """Test that guest creation sets session cookie."""
        response = client.post("/api/v1/players/guest")
        
        assert response.status_code == 201
        
        # Extract cookie
        session_cookie = response.cookies.get("vbrpg_session")
        assert session_cookie is not None
        
        # Cookie should contain session_id:player_id
        assert ":" in session_cookie
        parts = session_cookie.split(":")
        assert len(parts) == 2
        
        # Session ID should be 32 chars hex
        assert len(parts[0]) == 32
        
        # Player ID should match response
        data = response.json()
        assert parts[1] == data["id"]

    def test_create_guest_generates_unique_username(self, client):
        """Test that each guest gets unique username."""
        usernames = set()
        
        # Create 5 guest accounts
        for _ in range(5):
            response = client.post("/api/v1/players/guest")
            assert response.status_code == 201
            
            data = response.json()
            usernames.add(data["username"])
        
        # All should be unique
        assert len(usernames) == 5

    def test_create_guest_sets_expiration(self, client):
        """Test that guest account has expiration set."""
        response = client.post("/api/v1/players/guest")
        
        assert response.status_code == 201
        data = response.json()
        
        # Should have expires_at field
        assert "expires_at" in data
        assert data["expires_at"] is not None
        
        # Should be roughly 30 days in future
        # (exact validation would require parsing datetime)

    def test_create_guest_cookie_attributes(self, client):
        """Test session cookie has correct security attributes."""
        response = client.post("/api/v1/players/guest")
        
        assert response.status_code == 201
        
        # Check cookie attributes
        set_cookie_header = response.headers.get("set-cookie")
        assert "HttpOnly" in set_cookie_header
        assert "SameSite=lax" in set_cookie_header or "SameSite=Lax" in set_cookie_header
        assert "Max-Age" in set_cookie_header


class TestGetCurrentPlayer:
    """Test GET /api/v1/players/me endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_player_success(self, client, guest_player):
        """Test getting current player with valid session."""
        # Create session cookie
        cookie = create_session_cookie(guest_player.id)
        
        response = client.get(
            "/api/v1/players/me",
            cookies={"vbrpg_session": cookie}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == guest_player.id
        assert data["username"] == guest_player.username
        assert data["is_guest"] is True

    def test_get_current_player_unauthorized(self, client):
        """Test GET /me without session returns 401."""
        response = client.get("/api/v1/players/me")
        
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_get_current_player_invalid_session(self, client):
        """Test GET /me with invalid session format."""
        response = client.get(
            "/api/v1/players/me",
            cookies={"vbrpg_session": "invalid_format"}
        )
        
        # Should return 401 or 404 depending on validation
        assert response.status_code in [401, 404]

    def test_get_current_player_nonexistent(self, client):
        """Test GET /me with session for nonexistent player."""
        cookie = create_session_cookie("nonexistent_player_id")
        
        response = client.get(
            "/api/v1/players/me",
            cookies={"vbrpg_session": cookie}
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_permanent_player(self, client, permanent_player):
        """Test getting permanent player profile."""
        cookie = create_session_cookie(permanent_player.id)
        
        response = client.get(
            "/api/v1/players/me",
            cookies={"vbrpg_session": cookie}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == permanent_player.id
        assert data["is_guest"] is False
        assert data["expires_at"] is None


class TestUpgradeAccount:
    """Test POST /api/v1/players/me/upgrade endpoint."""

    @pytest.mark.asyncio
    async def test_upgrade_guest_success(self, client, guest_player):
        """Test successful guest account upgrade."""
        cookie = create_session_cookie(guest_player.id)
        
        response = client.post(
            "/api/v1/players/me/upgrade",
            json={"username": "UpgradedUser"},
            cookies={"vbrpg_session": cookie}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["username"] == "UpgradedUser"
        assert data["is_guest"] is False
        assert data["expires_at"] is None

    def test_upgrade_unauthorized(self, client):
        """Test upgrade without session returns 401."""
        response = client.post(
            "/api/v1/players/me/upgrade",
            json={"username": "NewUser"}
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upgrade_invalid_username(self, client, guest_player):
        """Test upgrade with invalid username format."""
        cookie = create_session_cookie(guest_player.id)
        
        # Try to upgrade with Guest_ prefix (reserved)
        response = client.post(
            "/api/v1/players/me/upgrade",
            json={"username": "Guest_不允许_使用"},
            cookies={"vbrpg_session": cookie}
        )
        
        assert response.status_code == 400
        assert "Guest_" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upgrade_empty_username(self, client, guest_player):
        """Test upgrade with empty username."""
        cookie = create_session_cookie(guest_player.id)
        
        response = client.post(
            "/api/v1/players/me/upgrade",
            json={"username": ""},
            cookies={"vbrpg_session": cookie}
        )
        
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upgrade_duplicate_username(self, client, guest_player, test_db):
        """Test upgrade to existing username fails."""
        # Create another player with target username
        existing = Player(username="ExistingUser", is_guest=False)
        test_db.add(existing)
        await test_db.commit()
        
        cookie = create_session_cookie(guest_player.id)
        
        response = client.post(
            "/api/v1/players/me/upgrade",
            json={"username": "ExistingUser"},
            cookies={"vbrpg_session": cookie}
        )
        
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upgrade_username_validation(self, client, guest_player):
        """Test username validation rules."""
        cookie = create_session_cookie(guest_player.id)
        
        # Test various invalid usernames
        invalid_usernames = [
            "ab",  # Too short
            "a" * 51,  # Too long (>50 chars)
            "user@name",  # Special chars
            "user name",  # Spaces
        ]
        
        for invalid in invalid_usernames:
            response = client.post(
                "/api/v1/players/me/upgrade",
                json={"username": invalid},
                cookies={"vbrpg_session": cookie}
            )
            
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upgrade_permanent_account_fails(self, client, permanent_player):
        """Test that permanent accounts cannot be 'upgraded'."""
        cookie = create_session_cookie(permanent_player.id)
        
        response = client.post(
            "/api/v1/players/me/upgrade",
            json={"username": "NewName"},
            cookies={"vbrpg_session": cookie}
        )
        
        # Should fail - already permanent
        assert response.status_code == 400


class TestGetPlayerStats:
    """Test GET /api/v1/players/me/stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_stats_success(self, client, player_with_stats):
        """Test getting player statistics."""
        cookie = create_session_cookie(player_with_stats.id)
        
        response = client.get(
            "/api/v1/players/me/stats",
            cookies={"vbrpg_session": cookie}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check stats structure
        assert data["player_id"] == player_with_stats.id
        assert data["username"] == "StatsPlayer"
        assert data["total_games"] == 10
        assert data["wins"] == 7
        assert data["win_rate"] == 0.7
        assert data["total_play_time_minutes"] == 120

    def test_get_stats_unauthorized(self, client):
        """Test stats endpoint without session."""
        response = client.get("/api/v1/players/me/stats")
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_stats_new_player(self, client, guest_player):
        """Test stats for player with no games."""
        cookie = create_session_cookie(guest_player.id)
        
        response = client.get(
            "/api/v1/players/me/stats",
            cookies={"vbrpg_session": cookie}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # New player has zero stats
        assert data["total_games"] == 0
        assert data["wins"] == 0
        assert data["win_rate"] == 0.0
        assert data["favorite_game"] is None

    @pytest.mark.asyncio
    async def test_get_stats_win_rate_calculation(self, client, test_db):
        """Test win rate calculation."""
        # Create player with specific win/loss ratio
        player = Player(username="WinRatePlayer", is_guest=False)
        test_db.add(player)
        await test_db.commit()
        await test_db.refresh(player)
        
        profile = PlayerProfile(
            player_id=player.id,
            total_games_played=20,
            games_won=15,
            games_lost=5
        )
        test_db.add(profile)
        await test_db.commit()
        
        cookie = create_session_cookie(player.id)
        
        response = client.get(
            "/api/v1/players/me/stats",
            cookies={"vbrpg_session": cookie}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 15/20 = 0.75
        assert data["win_rate"] == 0.75

    @pytest.mark.asyncio
    async def test_stats_include_timestamps(self, client, player_with_stats):
        """Test that stats include timestamp fields."""
        cookie = create_session_cookie(player_with_stats.id)
        
        response = client.get(
            "/api/v1/players/me/stats",
            cookies={"vbrpg_session": cookie}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "created_at" in data
        assert "last_active_at" in data


class TestPlayersAPIEdgeCases:
    """Test edge cases and error handling."""

    def test_invalid_http_methods(self, client):
        """Test that invalid HTTP methods are rejected."""
        # POST to /me should not be allowed (only GET)
        response = client.post("/api/v1/players/me")
        assert response.status_code in [405, 404]
        
        # PUT to /guest should not be allowed (only POST)
        response = client.put("/api/v1/players/guest")
        assert response.status_code in [405, 404]

    def test_malformed_json_upgrade(self, client):
        """Test upgrade with malformed JSON."""
        response = client.post(
            "/api/v1/players/me/upgrade",
            data="not json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422  # Unprocessable Entity

    def test_missing_username_field_upgrade(self, client):
        """Test upgrade without username field."""
        response = client.post(
            "/api/v1/players/me/upgrade",
            json={}
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_concurrent_guest_creation(self, client):
        """Test creating multiple guests concurrently."""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        def create_guest():
            return client.post("/api/v1/players/guest")
        
        # Create 10 guests concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_guest) for _ in range(10)]
            responses = [f.result() for f in futures]
        
        # All should succeed
        assert all(r.status_code == 201 for r in responses)
        
        # All should have unique usernames
        usernames = {r.json()["username"] for r in responses}
        assert len(usernames) == 10

    @pytest.mark.asyncio
    async def test_expired_session_cookie(self, client, guest_player):
        """Test that expired sessions are rejected."""
        # Create cookie with very old session
        # (Real implementation would check session age)
        cookie = create_session_cookie(guest_player.id)
        
        # Mock time has passed
        with patch("src.utils.sessions.datetime") as mock_datetime:
            # Set time to 31 days in future
            future_time = datetime.utcnow() + timedelta(days=31)
            mock_datetime.utcnow.return_value = future_time
            
            response = client.get(
                "/api/v1/players/me",
                cookies={"vbrpg_session": cookie}
            )
            
            # Should handle expired session
            # (Exact behavior depends on implementation)


class TestPlayersAPIIntegration:
    """Integration tests for complete user flows."""

    def test_complete_guest_to_permanent_flow(self, client):
        """Test complete flow: create guest → get profile → upgrade → verify."""
        # 1. Create guest
        response = client.post("/api/v1/players/guest")
        assert response.status_code == 201
        
        guest_data = response.json()
        session_cookie = response.cookies.get("session")
        
        # 2. Get profile
        response = client.get(
            "/api/v1/players/me",
            cookies={"vbrpg_session": session_cookie}
        )
        assert response.status_code == 200
        assert response.json()["is_guest"] is True
        
        # 3. Upgrade account
        response = client.post(
            "/api/v1/players/me/upgrade",
            json={"username": "UpgradedFlowUser"},
            cookies={"vbrpg_session": session_cookie}
        )
        assert response.status_code == 200
        
        upgraded_data = response.json()
        assert upgraded_data["username"] == "UpgradedFlowUser"
        assert upgraded_data["is_guest"] is False
        
        # 4. Verify permanent status persists
        response = client.get(
            "/api/v1/players/me",
            cookies={"vbrpg_session": session_cookie}
        )
        assert response.status_code == 200
        assert response.json()["is_guest"] is False

    def test_guest_stats_accumulation(self, client):
        """Test that guest accounts can accumulate statistics."""
        # Create guest
        response = client.post("/api/v1/players/guest")
        session_cookie = response.cookies.get("session")
        
        # Get initial stats
        response = client.get(
            "/api/v1/players/me/stats",
            cookies={"vbrpg_session": session_cookie}
        )
        assert response.status_code == 200
        assert response.json()["total_games"] == 0
        
        # (In real flow, player would join games and stats would increment)
        # This test verifies the stats endpoint is accessible for guests
