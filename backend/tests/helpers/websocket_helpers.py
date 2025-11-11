"""WebSocket event validation helpers for testing.

Provides utilities for testing Socket.IO event broadcasting and client connections.
"""
import asyncio
from typing import Any, Callable, Optional
from unittest.mock import AsyncMock, MagicMock

import socketio


class MockSocketIOClient:
    """Mock Socket.IO client for testing WebSocket events."""
    
    def __init__(self):
        self.events: dict[str, list[Any]] = {}
        self.connected = False
        self.sio = MagicMock(spec=socketio.AsyncClient)
    
    async def connect(self, url: str, auth: Optional[dict] = None):
        """Simulate connection to Socket.IO server."""
        self.connected = True
        self.events.clear()
    
    async def disconnect(self):
        """Simulate disconnection from server."""
        self.connected = False
    
    def on(self, event_name: str, handler: Optional[Callable] = None):
        """Register event handler."""
        if event_name not in self.events:
            self.events[event_name] = []
        
        def decorator(func):
            self.events[event_name].append(func)
            return func
        
        return decorator if handler is None else decorator(handler)
    
    async def emit(self, event_name: str, data: Any = None):
        """Emit event to server."""
        # Simulate event emission
        pass
    
    def get_events(self, event_name: str) -> list[Any]:
        """Get all received events of a specific type."""
        return self.events.get(event_name, [])
    
    def clear_events(self):
        """Clear all recorded events."""
        self.events.clear()


def connect_test_client() -> MockSocketIOClient:
    """Create and return a mock Socket.IO test client.
    
    Returns:
        MockSocketIOClient instance for testing
    
    Example:
        >>> client = connect_test_client()
        >>> await client.connect("http://localhost:8000")
        >>> @client.on("lobby_updated")
        >>> async def on_lobby_update(data):
        >>>     print(f"Lobby updated: {data}")
    """
    return MockSocketIOClient()


async def wait_for_event(
    client: MockSocketIOClient,
    event_name: str,
    timeout: float = 1.0,
    predicate: Optional[Callable[[Any], bool]] = None
) -> Optional[Any]:
    """Wait for a specific WebSocket event to be received.
    
    Args:
        client: Mock Socket.IO client instance
        event_name: Name of the event to wait for
        timeout: Maximum time to wait in seconds (default: 1.0)
        predicate: Optional function to filter events (returns True for matching events)
    
    Returns:
        Event data if received within timeout, None otherwise
    
    Example:
        >>> client = connect_test_client()
        >>> await client.connect("http://localhost:8000")
        >>> data = await wait_for_event(client, "lobby_updated", timeout=2.0)
        >>> assert data["room_code"] == "TEST1234"
    """
    start_time = asyncio.get_event_loop().time()
    
    while asyncio.get_event_loop().time() - start_time < timeout:
        events = client.get_events(event_name)
        
        if events:
            # If predicate provided, find matching event
            if predicate:
                for event_data in events:
                    if predicate(event_data):
                        return event_data
            else:
                # Return most recent event
                return events[-1]
        
        # Small delay before checking again
        await asyncio.sleep(0.01)
    
    return None


async def assert_event_broadcast(
    room_code: str,
    event_name: str,
    expected_payload: dict,
    mock_sio_server: Any,
    timeout: float = 1.0
) -> None:
    """Assert that a WebSocket event was broadcast to a room with expected payload.
    
    Args:
        room_code: Game room code (used as Socket.IO room identifier)
        event_name: Name of the event that should have been broadcast
        expected_payload: Expected event payload data
        mock_sio_server: Mock Socket.IO server instance
        timeout: Maximum time to wait for event (default: 1.0)
    
    Raises:
        AssertionError: If event was not broadcast or payload doesn't match
    
    Example:
        >>> await assert_event_broadcast(
        >>>     room_code="TEST1234",
        >>>     event_name="player_joined",
        >>>     expected_payload={"player_id": "abc123", "username": "Alice"},
        >>>     mock_sio_server=mock_server
        >>> )
    """
    # Wait for event to be broadcast
    await asyncio.sleep(0.05)  # Small delay for async operations
    
    # Verify emit was called on the mock server
    if not hasattr(mock_sio_server, "emit"):
        raise AttributeError("mock_sio_server must have an 'emit' method")
    
    # Check if emit was called with correct parameters
    emit_calls = [
        call for call in mock_sio_server.emit.call_args_list
        if len(call[0]) >= 1 and call[0][0] == event_name
    ]
    
    assert len(emit_calls) > 0, (
        f"Event '{event_name}' was not broadcast. "
        f"Available events: {[call[0][0] for call in mock_sio_server.emit.call_args_list]}"
    )
    
    # Find matching call with expected room
    matching_call = None
    for call in emit_calls:
        kwargs = call[1]
        if kwargs.get("room") == room_code:
            matching_call = call
            break
    
    assert matching_call is not None, (
        f"Event '{event_name}' was not broadcast to room '{room_code}'. "
        f"Rooms: {[call[1].get('room') for call in emit_calls]}"
    )
    
    # Verify payload matches expected
    actual_payload = matching_call[0][1] if len(matching_call[0]) > 1 else {}
    
    for key, expected_value in expected_payload.items():
        assert key in actual_payload, (
            f"Expected key '{key}' not found in payload. "
            f"Actual keys: {list(actual_payload.keys())}"
        )
        
        assert actual_payload[key] == expected_value, (
            f"Payload mismatch for key '{key}': "
            f"expected {expected_value}, got {actual_payload[key]}"
        )


class WebSocketEventRecorder:
    """Records WebSocket events for later assertion in tests."""
    
    def __init__(self):
        self.recorded_events: list[tuple[str, Any, Optional[str]]] = []
    
    def record_emit(self, event_name: str, data: Any, room: Optional[str] = None):
        """Record an emitted event."""
        self.recorded_events.append((event_name, data, room))
    
    def get_events_by_name(self, event_name: str) -> list[tuple[Any, Optional[str]]]:
        """Get all recorded events with a specific name.
        
        Returns:
            List of tuples (data, room) for matching events
        """
        return [
            (data, room)
            for name, data, room in self.recorded_events
            if name == event_name
        ]
    
    def get_events_by_room(self, room: str) -> list[tuple[str, Any]]:
        """Get all recorded events for a specific room.
        
        Returns:
            List of tuples (event_name, data) for matching room
        """
        return [
            (name, data)
            for name, data, event_room in self.recorded_events
            if event_room == room
        ]
    
    def assert_event_emitted(
        self,
        event_name: str,
        room: Optional[str] = None,
        data_matcher: Optional[Callable[[Any], bool]] = None
    ):
        """Assert that an event was emitted with optional filters.
        
        Args:
            event_name: Name of the event
            room: Optional room filter
            data_matcher: Optional function to validate event data
        
        Raises:
            AssertionError: If no matching event found
        """
        matching_events = [
            (data, event_room)
            for name, data, event_room in self.recorded_events
            if name == event_name and (room is None or event_room == room)
        ]
        
        assert len(matching_events) > 0, (
            f"Event '{event_name}' not found. "
            f"Recorded events: {[(name, room) for name, _, room in self.recorded_events]}"
        )
        
        if data_matcher:
            matching_with_data = [
                (data, event_room)
                for data, event_room in matching_events
                if data_matcher(data)
            ]
            
            assert len(matching_with_data) > 0, (
                f"Event '{event_name}' found but data didn't match predicate. "
                f"Available data: {[data for data, _ in matching_events]}"
            )
    
    def clear(self):
        """Clear all recorded events."""
        self.recorded_events.clear()
