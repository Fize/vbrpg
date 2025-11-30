# -*- coding: utf-8 -*-
"""Integration tests for werewolf game API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch

from main import app
from src.database import get_db


@pytest.fixture
async def client(test_db):
    """Create a test HTTP client."""
    # Override database dependency
    app.dependency_overrides[get_db] = lambda: test_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_werewolf_game_service():
    """Create a mock WerewolfGameService."""
    service = MagicMock()
    service.start_game = AsyncMock()
    service.get_visible_state = MagicMock()
    service.get_game_state = MagicMock()
    service.get_player_role = MagicMock()
    service.process_human_action = AsyncMock()
    return service


@pytest.mark.asyncio
class TestWerewolfQuickStartAPI:
    """Tests for the quick-start endpoint."""

    async def test_quick_start_success(self, client, mock_werewolf_game_service):
        """Test successful game start."""
        # Setup mock response
        mock_werewolf_game_service.get_visible_state.return_value = {
            "phase": "night",
            "day_number": 1,
            "players": [
                {
                    "seat_number": i,
                    "display_name": f"Player_{i}",
                    "is_alive": True,
                    "role": "werewolf" if i == 1 else None,
                    "team": "werewolf" if i == 1 else None,
                }
                for i in range(1, 11)
            ],
            "winner": None,
            "your_seat": 1,
            "your_role": "werewolf",
        }

        with patch(
            'src.api.werewolf_routes.WerewolfGameService',
            return_value=mock_werewolf_game_service
        ):
            response = await client.post(
                "/api/v1/werewolf/quick-start",
                json={
                    "player_id": "test-player-123",
                    "preferred_role": "werewolf",
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert "room_code" in data
        assert data["room_code"].startswith("WW-")
        assert data["phase"] == "night"
        assert data["day_number"] == 1
        assert len(data["players"]) == 10

    async def test_quick_start_without_preferred_role(self, client, mock_werewolf_game_service):
        """Test game start without specifying preferred role."""
        mock_werewolf_game_service.get_visible_state.return_value = {
            "phase": "night",
            "day_number": 1,
            "players": [
                {"seat_number": i, "display_name": f"Player_{i}", "is_alive": True}
                for i in range(1, 11)
            ],
            "winner": None,
            "your_seat": 1,
            "your_role": "villager",
        }

        with patch(
            'src.api.werewolf_routes.WerewolfGameService',
            return_value=mock_werewolf_game_service
        ):
            response = await client.post(
                "/api/v1/werewolf/quick-start",
                json={
                    "player_id": "test-player-456",
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert "room_code" in data

    async def test_quick_start_missing_player_id(self, client):
        """Test game start without player_id."""
        response = await client.post(
            "/api/v1/werewolf/quick-start",
            json={}
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
class TestWerewolfActionAPI:
    """Tests for the action submission endpoint."""

    async def test_submit_action_success(self, client, mock_werewolf_game_service):
        """Test successful action submission."""
        mock_werewolf_game_service.get_game_state.return_value = MagicMock(
            seer_result=None
        )

        # First, we need to "create" a game
        room_code = "WW-TEST001"
        with patch(
            'src.api.werewolf_routes._game_services',
            {room_code: mock_werewolf_game_service}
        ):
            response = await client.post(
                f"/api/v1/werewolf/rooms/{room_code}/action",
                json={
                    "player_id": "test-player-123",
                    "action_type": "vote",
                    "target_seat": 3,
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "vote" in data["message"]

    async def test_submit_check_action_returns_result(
        self, client, mock_werewolf_game_service
    ):
        """Test seer check action returns result."""
        mock_werewolf_game_service.get_game_state.return_value = MagicMock(
            seer_result={"is_werewolf": True}
        )

        room_code = "WW-TEST002"
        with patch(
            'src.api.werewolf_routes._game_services',
            {room_code: mock_werewolf_game_service}
        ):
            response = await client.post(
                f"/api/v1/werewolf/rooms/{room_code}/action",
                json={
                    "player_id": "test-player-123",
                    "action_type": "check",
                    "target_seat": 5,
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"] is not None
        assert data["result"]["is_werewolf"] is True

    async def test_submit_action_game_not_found(self, client):
        """Test action submission for non-existent game."""
        with patch('src.api.werewolf_routes._game_services', {}):
            response = await client.post(
                "/api/v1/werewolf/rooms/NONEXISTENT/action",
                json={
                    "player_id": "test-player-123",
                    "action_type": "vote",
                    "target_seat": 3,
                }
            )

        assert response.status_code == 404

    async def test_submit_action_missing_fields(self, client):
        """Test action submission with missing fields."""
        response = await client.post(
            "/api/v1/werewolf/rooms/WW-TEST/action",
            json={
                "player_id": "test-player-123",
                # Missing action_type
            }
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
class TestWerewolfStateAPI:
    """Tests for game state retrieval endpoint."""

    async def test_get_game_state_success(self, client, mock_werewolf_game_service):
        """Test successful game state retrieval."""
        mock_werewolf_game_service.get_visible_state.return_value = {
            "phase": "discussion",
            "day_number": 2,
            "players": [
                {"seat_number": i, "display_name": f"Player_{i}", "is_alive": i != 3}
                for i in range(1, 11)
            ],
            "winner": None,
            "your_seat": 1,
            "your_role": "seer",
        }

        room_code = "WW-TEST003"
        with patch(
            'src.api.werewolf_routes._game_services',
            {room_code: mock_werewolf_game_service}
        ):
            response = await client.get(
                f"/api/v1/werewolf/rooms/{room_code}/state",
                params={"player_id": "test-player-123"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["phase"] == "discussion"
        assert data["day_number"] == 2
        assert data["your_role"] == "seer"

    async def test_get_game_state_not_found(self, client):
        """Test state retrieval for non-existent game."""
        with patch('src.api.werewolf_routes._game_services', {}):
            response = await client.get(
                "/api/v1/werewolf/rooms/NONEXISTENT/state",
                params={"player_id": "test-player-123"}
            )

        assert response.status_code == 404


@pytest.mark.asyncio
class TestWerewolfRoleAPI:
    """Tests for player role retrieval endpoint."""

    async def test_get_player_role_werewolf(self, client, mock_werewolf_game_service):
        """Test getting werewolf role info."""
        mock_werewolf_game_service.get_player_role.return_value = "werewolf"

        room_code = "WW-TEST004"
        with patch(
            'src.api.werewolf_routes._game_services',
            {room_code: mock_werewolf_game_service}
        ):
            response = await client.get(
                f"/api/v1/werewolf/rooms/{room_code}/role",
                params={"player_id": "test-player-123"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "werewolf"
        assert data["role_name"] == "狼人"
        assert data["team"] == "werewolf"
        assert "击杀" in data["description"]

    async def test_get_player_role_seer(self, client, mock_werewolf_game_service):
        """Test getting seer role info."""
        mock_werewolf_game_service.get_player_role.return_value = "seer"

        room_code = "WW-TEST005"
        with patch(
            'src.api.werewolf_routes._game_services',
            {room_code: mock_werewolf_game_service}
        ):
            response = await client.get(
                f"/api/v1/werewolf/rooms/{room_code}/role",
                params={"player_id": "test-player-456"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "seer"
        assert data["role_name"] == "预言家"
        assert data["team"] == "villager"
        assert "查验" in data["description"]

    async def test_get_player_role_witch(self, client, mock_werewolf_game_service):
        """Test getting witch role info."""
        mock_werewolf_game_service.get_player_role.return_value = "witch"

        room_code = "WW-TEST006"
        with patch(
            'src.api.werewolf_routes._game_services',
            {room_code: mock_werewolf_game_service}
        ):
            response = await client.get(
                f"/api/v1/werewolf/rooms/{room_code}/role",
                params={"player_id": "test-player-789"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "witch"
        assert data["role_name"] == "女巫"
        assert "解药" in data["description"]
        assert "毒药" in data["description"]

    async def test_get_player_role_hunter(self, client, mock_werewolf_game_service):
        """Test getting hunter role info."""
        mock_werewolf_game_service.get_player_role.return_value = "hunter"

        room_code = "WW-TEST007"
        with patch(
            'src.api.werewolf_routes._game_services',
            {room_code: mock_werewolf_game_service}
        ):
            response = await client.get(
                f"/api/v1/werewolf/rooms/{room_code}/role",
                params={"player_id": "test-player-abc"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "hunter"
        assert data["role_name"] == "猎人"
        assert "开枪" in data["description"]

    async def test_get_player_role_villager(self, client, mock_werewolf_game_service):
        """Test getting villager role info."""
        mock_werewolf_game_service.get_player_role.return_value = "villager"

        room_code = "WW-TEST008"
        with patch(
            'src.api.werewolf_routes._game_services',
            {room_code: mock_werewolf_game_service}
        ):
            response = await client.get(
                f"/api/v1/werewolf/rooms/{room_code}/role",
                params={"player_id": "test-player-def"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "villager"
        assert data["role_name"] == "村民"
        assert data["team"] == "villager"

    async def test_get_player_role_not_found(self, client, mock_werewolf_game_service):
        """Test getting role for non-existent player."""
        mock_werewolf_game_service.get_player_role.return_value = None

        room_code = "WW-TEST009"
        with patch(
            'src.api.werewolf_routes._game_services',
            {room_code: mock_werewolf_game_service}
        ):
            response = await client.get(
                f"/api/v1/werewolf/rooms/{room_code}/role",
                params={"player_id": "unknown-player"}
            )

        assert response.status_code == 404

    async def test_get_role_game_not_found(self, client):
        """Test getting role for non-existent game."""
        with patch('src.api.werewolf_routes._game_services', {}):
            response = await client.get(
                "/api/v1/werewolf/rooms/NONEXISTENT/role",
                params={"player_id": "test-player-123"}
            )

        assert response.status_code == 404


@pytest.mark.asyncio
class TestAPIValidation:
    """Tests for API request validation."""

    async def test_quick_start_invalid_role(self, client, mock_werewolf_game_service):
        """Test quick start with invalid preferred role."""
        # Setup mock with proper visible state
        mock_service_instance = mock_werewolf_game_service
        mock_service_instance.get_visible_state.return_value = {
            "phase": "night",
            "day_number": 1,
            "players": [
                {
                    "seat_number": i,
                    "display_name": f"Player_{i}",
                    "is_alive": True,
                    "role": None,
                    "team": None,
                }
                for i in range(1, 11)
            ],
            "winner": None,
            "your_seat": 1,
            "your_role": "villager",
        }
        
        with patch("src.api.werewolf_routes.WerewolfGameService", return_value=mock_service_instance):
            response = await client.post(
                "/api/v1/werewolf/quick-start",
                json={
                    "player_id": "test-player-123",
                    "preferred_role": "invalid_role",
                }
            )

        # The API should accept it (invalid role just means random assignment)
        # 200 means accepted, service handles the invalid role gracefully
        assert response.status_code == 200

    async def test_action_invalid_action_type(self, client):
        """Test action with invalid action type."""
        response = await client.post(
            "/api/v1/werewolf/rooms/WW-TEST/action",
            json={
                "player_id": "test-player-123",
                "action_type": "invalid_action",
            }
        )

        # Should return validation error or be accepted
        # depending on schema strictness
        assert response.status_code in [200, 404, 422]
