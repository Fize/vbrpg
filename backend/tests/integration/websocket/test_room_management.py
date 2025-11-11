"""Integration tests for Socket.IO room management (join_lobby/leave_lobby)."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, call
from datetime import datetime

from src.models.game_room import GameRoom
from src.models.game_room_participant import GameRoomParticipant
from src.models.player import Player


@pytest.mark.asyncio
class TestSocketIORoomManagement:
    """Test Socket.IO room join/leave handlers for lobby subscriptions."""
    
    async def test_join_lobby_subscribes_to_room(self):
        """Test client joining lobby subscribes to lobby:{room_code} room."""
        from src.websocket.handlers import join_lobby
        
        sid = "test-sid-001"
        room_code = "ABC123"
        player_id = "player-uuid-1"
        
        with patch('src.websocket.handlers.sio') as mock_sio, \
             patch('src.database.get_db') as mock_get_db:
            
            # Mock database session
            mock_db = MagicMock()
            mock_get_db.return_value.__aiter__.return_value = [mock_db]
            
            # Mock room query result
            mock_room = MagicMock(spec=GameRoom)
            mock_room.code = room_code
            mock_room.id = 1
            mock_room.status = "Waiting"
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_room
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            # Mock socketio methods
            mock_sio.enter_room = AsyncMock()
            mock_sio.emit = AsyncMock()
            
            # Call handler
            await join_lobby(sid, {"room_code": room_code, "player_id": player_id})
            
            # Verify room subscription
            mock_sio.enter_room.assert_called_once_with(sid, room_code)
            
            # Verify success confirmation sent to client
            assert mock_sio.emit.call_count >= 1
            emit_calls = [call[0] for call in mock_sio.emit.call_args_list]
            assert any("lobby_joined" in str(call) for call in emit_calls)
    
    async def test_broadcast_only_sends_to_subscribed_clients(self):
        """Test broadcast to room only sends to subscribed clients."""
        from src.websocket.handlers import broadcast_player_joined
        
        room_code = "TEST01"
        player_data = {
            "id": "player-1",
            "username": "TestPlayer",
            "joined_at": datetime.utcnow().isoformat()
        }
        
        with patch('src.websocket.handlers.sio') as mock_sio:
            mock_sio.emit = AsyncMock()
            
            # Broadcast event
            await broadcast_player_joined(room_code, player_data)
            
            # Verify emit was called with room parameter (ensures room-scoped broadcast)
            mock_sio.emit.assert_called_once()
            call_kwargs = mock_sio.emit.call_args[1]
            assert "room" in call_kwargs
            assert call_kwargs["room"] == room_code
    
    async def test_leave_lobby_unsubscribes_from_room(self):
        """Test client leaving lobby unsubscribes from lobby:{room_code} room."""
        from src.websocket.handlers import leave_lobby
        
        sid = "test-sid-002"
        room_code = "DEF456"
        player_id = "player-uuid-2"
        
        with patch('src.websocket.handlers.sio') as mock_sio:
            # Mock socketio methods
            mock_sio.leave_room = AsyncMock()
            mock_sio.emit = AsyncMock()
            
            # Call handler
            await leave_lobby(sid, {"room_code": room_code, "player_id": player_id})
            
            # Verify room unsubscription
            mock_sio.leave_room.assert_called_once_with(sid, room_code)
            
            # Verify confirmation sent to client
            assert mock_sio.emit.call_count >= 1
    
    async def test_room_dissolution_disconnects_all_clients(self):
        """Test room dissolution disconnects all clients from lobby room."""
        from src.websocket.handlers import broadcast_room_dissolved
        
        room_code = "GHI789"
        reason = "no_human_players_remaining"
        
        with patch('src.websocket.handlers.sio') as mock_sio:
            mock_sio.emit = AsyncMock()
            
            # Broadcast dissolution event
            await broadcast_room_dissolved(room_code, reason)
            
            # Verify event sent to all clients in room
            mock_sio.emit.assert_called_once()
            call_args = mock_sio.emit.call_args
            
            assert call_args[0][0] == "room_dissolved"
            assert call_args[0][1]["room_code"] == room_code
            assert call_args[0][1]["reason"] == reason
            assert call_args[1]["room"] == room_code
    
    async def test_join_lobby_validates_room_exists(self):
        """Test join_lobby handler validates room exists before subscribing."""
        from src.websocket.handlers import join_lobby
        
        sid = "test-sid-003"
        room_code = "NOEXIST"
        player_id = "player-uuid-3"
        
        with patch('src.websocket.handlers.sio') as mock_sio, \
             patch('src.database.get_db') as mock_get_db:
            
            # Mock database session with non-existent room
            mock_db = MagicMock()
            mock_get_db.return_value.__aiter__.return_value = [mock_db]
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None  # Room not found
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            # Mock socketio methods
            mock_sio.enter_room = AsyncMock()
            mock_sio.emit = AsyncMock()
            
            # Call handler
            await join_lobby(sid, {"room_code": room_code, "player_id": player_id})
            
            # Verify room was NOT joined
            mock_sio.enter_room.assert_not_called()
            
            # Verify error message sent to client
            error_calls = [
                call for call in mock_sio.emit.call_args_list
                if "error" in str(call[0][0]).lower() or "Room not found" in str(call)
            ]
            assert len(error_calls) > 0, "Should send error for non-existent room"
    
    async def test_join_lobby_validates_player_permissions(self):
        """Test join_lobby validates player is participant in room."""
        from src.websocket.handlers import join_lobby
        
        sid = "test-sid-004"
        room_code = "JKL012"
        player_id = "unauthorized-player"
        
        with patch('src.websocket.handlers.sio') as mock_sio, \
             patch('src.database.get_db') as mock_get_db:
            
            # Mock database session
            mock_db = MagicMock()
            mock_get_db.return_value.__aiter__.return_value = [mock_db]
            
            # Mock room exists
            mock_room = MagicMock(spec=GameRoom)
            mock_room.code = room_code
            mock_room.id = 1
            mock_room.status = "Waiting"
            
            # Mock participant query - player NOT found
            mock_room_result = MagicMock()
            mock_room_result.scalar_one_or_none.return_value = mock_room
            
            mock_participant_result = MagicMock()
            mock_participant_result.scalar_one_or_none.return_value = None  # Not a participant
            
            # Set up execute to return different results for different queries
            mock_db.execute = AsyncMock(side_effect=[mock_room_result, mock_participant_result])
            
            # Mock socketio methods
            mock_sio.enter_room = AsyncMock()
            mock_sio.emit = AsyncMock()
            
            # Call handler
            await join_lobby(sid, {"room_code": room_code, "player_id": player_id})
            
            # Verify room was NOT joined
            mock_sio.enter_room.assert_not_called()
            
            # Verify error/permission denied message sent
            error_calls = [
                call for call in mock_sio.emit.call_args_list
                if "error" in str(call[0][0]).lower() or "not a participant" in str(call).lower()
            ]
            assert len(error_calls) > 0, "Should send error for unauthorized player"
    
    async def test_multiple_clients_in_same_room_receive_events(self):
        """Test multiple clients in same room all receive broadcast events."""
        from src.websocket.handlers import broadcast_player_joined
        
        room_code = "MULTI1"
        player_data = {
            "id": "new-player",
            "username": "NewPlayer",
            "joined_at": datetime.utcnow().isoformat()
        }
        
        with patch('src.websocket.handlers.sio') as mock_sio:
            mock_sio.emit = AsyncMock()
            
            # Broadcast to room with multiple clients
            await broadcast_player_joined(room_code, player_data)
            
            # Verify single broadcast call to room (socket.io handles multi-client delivery)
            mock_sio.emit.assert_called_once()
            call_kwargs = mock_sio.emit.call_args[1]
            assert call_kwargs["room"] == room_code
            
            # Socket.IO's room broadcast ensures all subscribed clients receive the event
            # No need to call emit multiple times - room parameter handles distribution
