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
        "broadcast_role_assignment",
        "broadcast_role_selected",
        "broadcast_ai_action",
        "broadcast_waiting_for_human",
        "broadcast_speech_options",
        "broadcast_human_speech_complete",
        "broadcast_player_speech",
        "broadcast_last_words_options",
        "broadcast_spectator_mode",
        "broadcast_vote_options",
        "broadcast_human_vote_complete",
        "broadcast_human_night_action_complete",
        "broadcast_wolf_chat_message",
        "broadcast_wolf_chat_history",
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
    "broadcast_role_assignment",
    "broadcast_role_selected",
    "broadcast_ai_action",
    "broadcast_waiting_for_human",
    "broadcast_speech_options",
    "broadcast_human_speech_complete",
    "broadcast_player_speech",
    "broadcast_last_words_options",
    "broadcast_spectator_mode",
    "broadcast_vote_options",
    "broadcast_human_vote_complete",
    "broadcast_human_night_action_complete",
    "broadcast_wolf_chat_message",
    "broadcast_wolf_chat_history",
]