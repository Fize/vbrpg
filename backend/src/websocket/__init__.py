"""WebSocket package."""


def __getattr__(name):
    """Lazy import to avoid circular dependencies."""
    if name == "sio":
        from src.websocket.server import sio
        return sio
    
    # Import werewolf handlers functions
    werewolf_funcs = [
        "broadcast_to_room",
        "broadcast_host_announcement",
        "stream_host_announcement",
        "broadcast_game_state_update",
        "broadcast_phase_change",
        "notify_werewolf_turn",
        "notify_seer_turn",
        "notify_seer_result",
        "notify_witch_turn",
        "notify_hunter_shoot",
        "stream_ai_speech",
        "broadcast_vote_update",
        "broadcast_vote_result",
        "broadcast_game_over",
    ]
    
    if name in werewolf_funcs:
        from src.websocket import werewolf_handlers
        return getattr(werewolf_handlers, name)
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "sio",
    "broadcast_to_room",
    "broadcast_host_announcement",
    "stream_host_announcement",
    "broadcast_game_state_update",
    "broadcast_phase_change",
    "notify_werewolf_turn",
    "notify_seer_turn",
    "notify_seer_result",
    "notify_witch_turn",
    "notify_hunter_shoot",
    "stream_ai_speech",
    "broadcast_vote_update",
    "broadcast_vote_result",
    "broadcast_game_over",
]