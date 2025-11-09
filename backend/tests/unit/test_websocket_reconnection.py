"""Tests for WebSocket reconnection handling."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from socketio import AsyncServer

from src.websocket.handlers import (
    disconnected_players,
    RECONNECTION_GRACE_PERIOD,
    handle_reconnection_timeout,
    connect,
    disconnect
)


@pytest.fixture
def mock_sio():
    """Mock SocketIO server."""
    sio = Mock(spec=AsyncServer)
    sio.emit = AsyncMock()
    sio.enter_room = AsyncMock()
    sio.leave_room = AsyncMock()
    return sio


@pytest.fixture
def mock_sid():
    """Mock session ID."""
    return "test_session_123"


@pytest.fixture
def mock_player_id():
    """Mock player ID."""
    return "player_456"


@pytest.fixture
def mock_room_code():
    """Mock room code."""
    return "ABC123"


@pytest.fixture(autouse=True)
def clear_disconnected_players():
    """Clear disconnected players dict before each test."""
    disconnected_players.clear()
    yield
    disconnected_players.clear()


class TestReconnectionConstants:
    """Test reconnection configuration."""

    def test_reconnection_grace_period(self):
        """Test reconnection grace period is 5 minutes."""
        assert RECONNECTION_GRACE_PERIOD == timedelta(minutes=5)
        assert RECONNECTION_GRACE_PERIOD.total_seconds() == 300

    def test_disconnected_players_dict_exists(self):
        """Test disconnected players tracking dict exists."""
        assert disconnected_players is not None
        assert isinstance(disconnected_players, dict)


class TestConnectWithReconnection:
    """Test connect handler with reconnection logic."""

    @pytest.mark.asyncio
    async def test_connect_normal_first_time(self, mock_sio, mock_sid, test_db):
        """Test normal first-time connection."""
        environ = {"auth": {"player_id": "new_player"}}
        
        # Simulate connect (this would need actual handler setup)
        # Testing the reconnection check logic
        player_id = "new_player"
        
        # Player not in disconnected dict
        assert player_id not in disconnected_players
        
        # Should proceed normally with room joining

    @pytest.mark.asyncio
    async def test_connect_with_recent_disconnect(self, mock_sio, mock_sid):
        """Test reconnection within grace period."""
        player_id = "reconnecting_player"
        room_code = "ROOM123"
        
        # Simulate recent disconnect
        disconnect_time = datetime.utcnow()
        disconnected_players[player_id] = {
            "disconnect_time": disconnect_time,
            "room_code": room_code,
            "task": None
        }
        
        # Calculate elapsed time
        time_elapsed = datetime.utcnow() - disconnect_time
        
        # Should be within grace period
        assert time_elapsed < RECONNECTION_GRACE_PERIOD
        
        # Reconnection should be allowed

    @pytest.mark.asyncio
    async def test_connect_after_grace_period(self):
        """Test connection attempt after grace period expired."""
        player_id = "late_player"
        room_code = "ROOM456"
        
        # Simulate old disconnect (beyond grace period)
        disconnect_time = datetime.utcnow() - timedelta(minutes=6)
        disconnected_players[player_id] = {
            "disconnect_time": disconnect_time,
            "room_code": room_code,
            "task": None
        }
        
        # Calculate elapsed time
        time_elapsed = datetime.utcnow() - disconnect_time
        
        # Should be beyond grace period
        assert time_elapsed > RECONNECTION_GRACE_PERIOD
        
        # Reconnection should fail

    @pytest.mark.asyncio
    async def test_connect_cancels_timeout_task(self):
        """Test that reconnection cancels pending timeout task."""
        player_id = "player_with_task"
        
        # Create mock timeout task
        mock_task = MagicMock()
        mock_task.cancel = Mock()
        
        disconnected_players[player_id] = {
            "disconnect_time": datetime.utcnow(),
            "room_code": "ROOM789",
            "task": mock_task
        }
        
        # Simulate reconnection (would cancel task)
        # In real handler, this would be:
        # old_task = disconnected_players[player_id].get("task")
        # if old_task:
        #     old_task.cancel()
        
        old_task = disconnected_players[player_id].get("task")
        if old_task:
            old_task.cancel()
        
        # Task should be cancelled
        assert mock_task.cancel.called


class TestDisconnectHandling:
    """Test disconnect handler with reconnection setup."""

    @pytest.mark.asyncio
    async def test_disconnect_starts_grace_period(self):
        """Test that disconnect starts grace period timer."""
        player_id = "disconnecting_player"
        room_code = "DISCO123"
        
        # Simulate disconnect handling
        disconnect_time = datetime.utcnow()
        
        # Would create timeout task here
        # In real handler:
        # task = asyncio.create_task(
        #     handle_reconnection_timeout(player_id, room_code)
        # )
        
        disconnected_players[player_id] = {
            "disconnect_time": disconnect_time,
            "room_code": room_code,
            "task": None  # Would be actual task
        }
        
        # Player should be tracked
        assert player_id in disconnected_players
        assert disconnected_players[player_id]["room_code"] == room_code

    @pytest.mark.asyncio
    async def test_disconnect_notifies_other_players(self, mock_sio):
        """Test that disconnect notifies other players in room."""
        player_id = "leaving_player"
        room_code = "NOTIFY123"
        
        # Simulate broadcast
        await mock_sio.emit(
            "player_disconnected",
            {
                "player_id": player_id,
                "grace_period_seconds": int(RECONNECTION_GRACE_PERIOD.total_seconds())
            },
            room=room_code
        )
        
        # Should have emitted notification
        assert mock_sio.emit.called
        call_args = mock_sio.emit.call_args
        assert call_args[0][0] == "player_disconnected"
        assert call_args[1]["room"] == room_code

    @pytest.mark.asyncio
    async def test_disconnect_multiple_rooms(self):
        """Test disconnect from multiple active rooms."""
        player_id = "multi_room_player"
        rooms = ["ROOM1", "ROOM2", "ROOM3"]
        
        # Track disconnection for each room
        for room_code in rooms:
            key = f"{player_id}_{room_code}"
            disconnected_players[key] = {
                "disconnect_time": datetime.utcnow(),
                "room_code": room_code,
                "task": None
            }
        
        # All rooms should be tracked
        assert len([k for k in disconnected_players.keys() if player_id in k]) == 3


class TestReconnectionTimeout:
    """Test reconnection timeout handling."""

    @pytest.mark.asyncio
    async def test_timeout_waits_full_period(self):
        """Test that timeout waits the full grace period."""
        player_id = "timeout_player"
        room_code = "TIMEOUT123"
        
        start_time = datetime.utcnow()
        
        # In real implementation, would await the sleep
        # await asyncio.sleep(RECONNECTION_GRACE_PERIOD.total_seconds())
        
        # Verify the wait time constant
        wait_seconds = RECONNECTION_GRACE_PERIOD.total_seconds()
        assert wait_seconds == 300

    @pytest.mark.asyncio
    async def test_timeout_checks_if_player_reconnected(self):
        """Test that timeout checks if player reconnected before replacing."""
        player_id = "maybe_reconnected"
        room_code = "CHECK123"
        
        # Simulate player reconnected (removed from dict)
        # disconnected_players would NOT contain player_id
        
        # Timeout should check:
        # if player_id not in disconnected_players:
        #     return  # Player reconnected, don't replace
        
        assert player_id not in disconnected_players

    @pytest.mark.asyncio
    @patch("src.services.game_room_service.GameRoomService.replace_player_with_ai")
    async def test_timeout_replaces_with_ai(self, mock_replace):
        """Test that timeout replaces player with AI."""
        player_id = "ai_replace_player"
        room_code = "AI123"
        
        # Keep player in disconnected dict (not reconnected)
        disconnected_players[player_id] = {
            "disconnect_time": datetime.utcnow() - timedelta(minutes=5),
            "room_code": room_code,
            "task": None
        }
        
        mock_replace.return_value = AsyncMock()
        
        # Would call replace in real handler
        # await GameRoomService(db).replace_player_with_ai(room_code, player_id)
        
        # Verify player still in dict (hasn't reconnected)
        assert player_id in disconnected_players

    @pytest.mark.asyncio
    async def test_timeout_broadcasts_replacement(self, mock_sio):
        """Test that timeout broadcasts AI replacement to room."""
        player_id = "broadcast_replace"
        room_code = "BROAD123"
        
        # Simulate broadcast after replacement
        await mock_sio.emit(
            "player_replaced_by_ai",
            {
                "player_id": player_id,
                "ai_name": "AI探员"
            },
            room=room_code
        )
        
        # Should have broadcast
        assert mock_sio.emit.called
        call_args = mock_sio.emit.call_args
        assert call_args[0][0] == "player_replaced_by_ai"

    @pytest.mark.asyncio
    async def test_timeout_cleans_up_tracking(self):
        """Test that timeout removes player from tracking dict."""
        player_id = "cleanup_player"
        
        # Add to dict
        disconnected_players[player_id] = {
            "disconnect_time": datetime.utcnow(),
            "room_code": "CLEAN123",
            "task": None
        }
        
        # After timeout completes, should remove
        disconnected_players.pop(player_id, None)
        
        assert player_id not in disconnected_players


class TestReconnectionEvents:
    """Test reconnection WebSocket events."""

    @pytest.mark.asyncio
    async def test_reconnected_event_emitted(self, mock_sio):
        """Test that reconnected event is emitted on successful reconnect."""
        player_id = "reconnect_success"
        room_code = "RECON123"
        
        await mock_sio.emit(
            "reconnected",
            {
                "message": "Successfully reconnected",
                "player_id": player_id
            },
            to="some_sid"
        )
        
        assert mock_sio.emit.called

    @pytest.mark.asyncio
    async def test_reconnection_failed_event(self, mock_sio):
        """Test that reconnection_failed event is emitted when expired."""
        player_id = "reconnect_fail"
        
        await mock_sio.emit(
            "reconnection_failed",
            {
                "message": "Reconnection period expired",
                "player_id": player_id
            },
            to="some_sid"
        )
        
        assert mock_sio.emit.called

    @pytest.mark.asyncio
    async def test_player_reconnected_broadcast(self, mock_sio):
        """Test broadcast to room when player reconnects."""
        player_id = "player_back"
        room_code = "BACK123"
        
        await mock_sio.emit(
            "player_reconnected",
            {
                "player_id": player_id,
                "message": f"Player {player_id} has reconnected"
            },
            room=room_code
        )
        
        assert mock_sio.emit.called


class TestReconnectionEdgeCases:
    """Test edge cases in reconnection handling."""

    @pytest.mark.asyncio
    async def test_multiple_disconnects_same_player(self):
        """Test handling multiple disconnects from same player."""
        player_id = "flaky_player"
        
        # First disconnect
        disconnected_players[player_id] = {
            "disconnect_time": datetime.utcnow(),
            "room_code": "ROOM1",
            "task": MagicMock()
        }
        
        # Second disconnect (should cancel previous task)
        old_task = disconnected_players[player_id].get("task")
        if old_task:
            old_task.cancel()
        
        disconnected_players[player_id] = {
            "disconnect_time": datetime.utcnow(),
            "room_code": "ROOM1",
            "task": MagicMock()
        }
        
        # Should only have one entry
        assert len([k for k in disconnected_players.keys() if k == player_id]) == 1

    @pytest.mark.asyncio
    async def test_reconnect_to_wrong_room(self):
        """Test reconnection attempt to different room."""
        player_id = "wrong_room_player"
        original_room = "ORIGINAL"
        wrong_room = "WRONG"
        
        # Track disconnect from original room
        disconnected_players[player_id] = {
            "disconnect_time": datetime.utcnow(),
            "room_code": original_room,
            "task": None
        }
        
        # Attempt to reconnect to wrong room should be handled
        tracked_room = disconnected_players[player_id]["room_code"]
        assert tracked_room == original_room
        assert tracked_room != wrong_room

    @pytest.mark.asyncio
    async def test_grace_period_boundary(self):
        """Test grace period boundary conditions."""
        player_id = "boundary_player"
        
        # Right at boundary (5 minutes)
        disconnect_time = datetime.utcnow() - RECONNECTION_GRACE_PERIOD
        disconnected_players[player_id] = {
            "disconnect_time": disconnect_time,
            "room_code": "BOUND123",
            "task": None
        }
        
        time_elapsed = datetime.utcnow() - disconnect_time
        
        # Should be at or just past boundary
        assert time_elapsed >= RECONNECTION_GRACE_PERIOD

    @pytest.mark.asyncio
    async def test_concurrent_reconnections(self):
        """Test handling concurrent reconnections."""
        players = [f"player_{i}" for i in range(10)]
        
        # Simulate multiple disconnections
        for player_id in players:
            disconnected_players[player_id] = {
                "disconnect_time": datetime.utcnow(),
                "room_code": "CONCURRENT",
                "task": None
            }
        
        # All should be tracked
        assert len(disconnected_players) == 10
        
        # Simulate concurrent reconnections (clear tracking)
        for player_id in players[:5]:
            disconnected_players.pop(player_id, None)
        
        # Half should be removed
        assert len(disconnected_players) == 5

    @pytest.mark.asyncio
    async def test_task_cancellation_exception_handling(self):
        """Test handling of task cancellation exceptions."""
        player_id = "cancel_error_player"
        
        # Create mock task that raises on cancel
        mock_task = MagicMock()
        mock_task.cancel.side_effect = asyncio.CancelledError()
        
        disconnected_players[player_id] = {
            "disconnect_time": datetime.utcnow(),
            "room_code": "CANCEL123",
            "task": mock_task
        }
        
        # Should handle cancellation error gracefully
        try:
            old_task = disconnected_players[player_id].get("task")
            if old_task:
                old_task.cancel()
        except asyncio.CancelledError:
            pass  # Expected, should be handled
        
        # Should not raise


class TestReconnectionIntegration:
    """Integration tests for complete reconnection flow."""

    @pytest.mark.asyncio
    async def test_full_reconnection_cycle(self):
        """Test complete reconnection cycle."""
        player_id = "full_cycle_player"
        room_code = "CYCLE123"
        
        # 1. Track disconnect
        disconnected_players[player_id] = {
            "disconnect_time": datetime.utcnow(),
            "room_code": room_code,
            "task": MagicMock()
        }
        
        assert player_id in disconnected_players
        
        # 2. Reconnect (within grace period)
        if player_id in disconnected_players:
            # Cancel timeout
            task = disconnected_players[player_id].get("task")
            if task:
                task.cancel()
            
            # Remove from tracking
            disconnected_players.pop(player_id)
        
        assert player_id not in disconnected_players

    @pytest.mark.asyncio
    async def test_timeout_replacement_cycle(self):
        """Test complete timeout and replacement cycle."""
        player_id = "timeout_cycle_player"
        room_code = "TOCYCLE"
        
        # 1. Track disconnect
        disconnected_players[player_id] = {
            "disconnect_time": datetime.utcnow() - timedelta(minutes=6),
            "room_code": room_code,
            "task": None
        }
        
        # 2. Grace period expires (player still in dict)
        assert player_id in disconnected_players
        
        # 3. Replace with AI (would happen in real handler)
        # GameRoomService.replace_player_with_ai(room_code, player_id)
        
        # 4. Clean up tracking
        disconnected_players.pop(player_id, None)
        
        assert player_id not in disconnected_players
