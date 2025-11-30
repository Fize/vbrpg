"""Shared session storage for WebSocket connections."""

# Store session connections: {sid: player_id}
user_sessions: dict[str, str] = {}
