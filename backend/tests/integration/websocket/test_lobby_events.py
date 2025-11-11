"""Integration tests for WebSocket lobby event broadcasting."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.websocket.handlers import (
    broadcast_player_joined,
    broadcast_player_left,
)


@pytest.mark.asyncio
class TestLobbyEventBroadcasting:
    """Test WebSocket event broadcasting for lobby actions."""
    
    async def test_player_joined_event_sent_to_all_participants(self):
        """Test player_joined event broadcast to all room participants (FR-008)."""
        room_code = "TEST01"
        player_data = {
            "id": "player-1",
            "username": "TestPlayer",
            "joined_at": "2025-11-09T10:00:00Z"
        }
        
        with patch('src.websocket.handlers.sio') as mock_sio:
            mock_sio.emit = AsyncMock()
            
            await broadcast_player_joined(room_code, player_data)
            
            # Verify emit was called with correct parameters
            mock_sio.emit.assert_called_once()
            call_args = mock_sio.emit.call_args
            
            assert call_args[0][0] == "player_joined"  # Event name
            assert call_args[0][1]["room_code"] == room_code
            assert call_args[0][1]["player"]["id"] == "player-1"
            assert call_args[1]["room"] == room_code  # Broadcast to room
    
    async def test_player_left_event_sent_to_remaining_participants(self):
        """Test player_left event broadcast to remaining participants."""
        room_code = "TEST02"
        player_id = "player-2"
        player_name = "LeavingPlayer"
        
        with patch('src.websocket.handlers.sio') as mock_sio:
            mock_sio.emit = AsyncMock()
            
            await broadcast_player_left(room_code, player_id, player_name)
            
            mock_sio.emit.assert_called_once()
            call_args = mock_sio.emit.call_args
            
            assert call_args[0][0] == "player_left"
            assert call_args[0][1]["room_code"] == room_code
            assert call_args[0][1]["player_id"] == player_id
            assert call_args[0][1]["player_name"] == player_name
            assert call_args[1]["room"] == room_code
    
    async def test_ownership_transferred_event_on_owner_leave(self):
        """Test ownership_transferred event sent when owner leaves (FR-014)."""
        # This test will be implemented in T027
        # For now, just check the handler exists
        from src.websocket import handlers
        assert hasattr(handlers, 'broadcast_ownership_transferred'), \
            "broadcast_ownership_transferred handler should exist"
    
    async def test_room_dissolved_event_when_only_ai_remain(self):
        """Test room_dissolved event sent when only AI remain."""
        # This test will be implemented in T027
        from src.websocket import handlers
        assert hasattr(handlers, 'broadcast_room_dissolved'), \
            "broadcast_room_dissolved handler should exist"
    
    async def test_events_delivered_within_one_second(self):
        """Test events delivered within 1 second (FR-009, SC-003)."""
        room_code = "PERF01"
        player_data = {
            "id": "perf-player",
            "username": "PerfTest",
            "joined_at": "2025-11-09T10:00:00Z"
        }
        
        with patch('src.websocket.handlers.sio') as mock_sio:
            mock_sio.emit = AsyncMock()
            
            start_time = asyncio.get_event_loop().time()
            await broadcast_player_joined(room_code, player_data)
            elapsed = asyncio.get_event_loop().time() - start_time
            
            assert elapsed < 1.0, f"Event broadcast took {elapsed}s, should be < 1s"
            mock_sio.emit.assert_called_once()
    
    async def test_multiple_events_in_sequence(self):
        """Test broadcasting multiple events in sequence without blocking."""
        room_code = "SEQ01"
        
        with patch('src.websocket.handlers.sio') as mock_sio:
            mock_sio.emit = AsyncMock()
            
            # Simulate join → leave sequence
            player1_data = {"id": "p1", "username": "Player1", "joined_at": "2025-11-09T10:00:00Z"}
            player2_data = {"id": "p2", "username": "Player2", "joined_at": "2025-11-09T10:00:01Z"}
            
            await broadcast_player_joined(room_code, player1_data)
            await broadcast_player_joined(room_code, player2_data)
            await broadcast_player_left(room_code, "p1", "Player1")
            
            assert mock_sio.emit.call_count == 3
    
    async def test_broadcast_handles_errors_gracefully(self):
        """Test that broadcast errors are logged but don't crash."""
        room_code = "ERR01"
        player_data = {"id": "err-player", "username": "ErrorTest", "joined_at": "2025-11-09T10:00:00Z"}
        
        with patch('src.websocket.handlers.sio') as mock_sio:
            mock_sio.emit = AsyncMock(side_effect=Exception("Socket error"))
            
            # Should not raise exception
            try:
                await broadcast_player_joined(room_code, player_data)
            except Exception as e:
                pytest.fail(f"broadcast_player_joined should handle errors gracefully, but raised: {e}")
