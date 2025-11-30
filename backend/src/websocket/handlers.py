"""WebSocket event handlers."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select

from src.models.user import Player
from src.services.game_room_service import GameRoomService
from src.models.game import GameRoom, GameRoomParticipant
from src.utils.errors import BadRequestError
from src.websocket.server import sio
from src.websocket.sessions import user_sessions

logger = logging.getLogger(__name__)

# Store disconnection timestamps: {player_id: {"room_code": str, "disconnect_time": datetime, "task": asyncio.Task}}
disconnected_players: dict[str, dict[str, Any]] = {}

# Reconnection grace period (5 minutes)
RECONNECTION_GRACE_PERIOD = timedelta(minutes=5)


@sio.event
async def connect(sid: str, environ: dict, auth: dict | None = None):
    """Handle client connection."""
    logger.info(f"Client connected: {sid}")

    # Extract player_id from auth
    player_id = None
    if auth and "player_id" in auth:
        player_id = auth["player_id"]
        user_sessions[sid] = player_id
        logger.info(f"Authenticated user {player_id} connected with sid {sid}")

        # Check if this is a reconnection
        if player_id in disconnected_players:
            disconnect_info = disconnected_players[player_id]
            room_code = disconnect_info["room_code"]
            disconnect_time = disconnect_info["disconnect_time"]
            timeout_task = disconnect_info["task"]

            # Calculate time elapsed
            time_elapsed = datetime.utcnow() - disconnect_time

            if time_elapsed < RECONNECTION_GRACE_PERIOD:
                # Cancel timeout task
                if timeout_task and not timeout_task.done():
                    timeout_task.cancel()

                # Rejoin room
                await sio.enter_room(sid, room_code)

                # Notify successful reconnection
                await sio.emit(
                    "reconnected",
                    {
                        "player_id": player_id,
                        "room_code": room_code,
                        "message": "成功重连到游戏",
                        "disconnect_duration_seconds": int(time_elapsed.total_seconds())
                    },
                    room=sid
                )

                # Notify other players
                await sio.emit(
                    "player_reconnected",
                    {
                        "player_id": player_id,
                        "room_code": room_code,
                        "message": "玩家已重连"
                    },
                    room=room_code,
                    skip_sid=sid
                )

                # Clean up disconnection record
                disconnected_players.pop(player_id, None)

                logger.info(
                    f"Player {player_id} reconnected to room {room_code} "
                    f"after {time_elapsed.total_seconds():.1f} seconds"
                )
            else:
                logger.warning(
                    f"Player {player_id} reconnection attempt after grace period expired"
                )
                await sio.emit(
                    "reconnection_failed",
                    {
                        "message": "重连超时，您已被AI替代",
                        "reason": "timeout"
                    },
                    room=sid
                )

    await sio.emit("connected", {"sid": sid}, room=sid)


@sio.event
async def disconnect(sid: str):
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {sid}")

    # Get player info before cleanup
    player_id = user_sessions.get(sid)

    if player_id:
        # Find which room(s) the player was in
        from src.database import get_db

        async for db in get_db():
            try:
                # Get active participant records for this player
                result = await db.execute(
                    select(GameRoomParticipant, GameRoom)
                    .join(GameRoom, GameRoomParticipant.game_room_id == GameRoom.id)
                    .where(
                        GameRoomParticipant.player_id == player_id,
                        GameRoomParticipant.left_at.is_(None),
                        GameRoom.status == "In Progress"
                    )
                )
                participants_rooms = result.all()

                # Start reconnection grace period for each active game
                for participant, room in participants_rooms:
                    room_code = room.code

                    # Cancel any existing timeout task
                    if player_id in disconnected_players:
                        old_task = disconnected_players[player_id].get("task")
                        if old_task and not old_task.done():
                            old_task.cancel()

                    # Create timeout task
                    timeout_task = asyncio.create_task(
                        handle_reconnection_timeout(player_id, room_code)
                    )

                    # Store disconnection info
                    disconnected_players[player_id] = {
                        "room_code": room_code,
                        "disconnect_time": datetime.utcnow(),
                        "task": timeout_task
                    }

                    logger.info(
                        f"Player {player_id} disconnected from room {room_code}. "
                        f"Grace period started (5 minutes)"
                    )

                    # Notify other players
                    await sio.emit(
                        "player_disconnected",
                        {
                            "player_id": player_id,
                            "room_code": room_code,
                            "grace_period_seconds": int(RECONNECTION_GRACE_PERIOD.total_seconds()),
                            "message": "玩家断线，等待重连中..."
                        },
                        room=room_code,
                        skip_sid=sid
                    )

            except Exception as e:
                logger.error(f"Error handling disconnection for {player_id}: {e}")
            finally:
                break

        # Clean up session
        user_sessions.pop(sid, None)
        logger.info(f"User {player_id} session cleaned up")


async def handle_reconnection_timeout(player_id: str, room_code: str):
    """
    Handle timeout after reconnection grace period expires.
    Replace player with AI if they don't reconnect within 5 minutes.
    """
    try:
        # Wait for grace period
        await asyncio.sleep(RECONNECTION_GRACE_PERIOD.total_seconds())

        # Check if player reconnected during grace period
        if player_id not in disconnected_players:
            logger.info(f"Player {player_id} reconnected before timeout")
            return

        logger.warning(
            f"Player {player_id} did not reconnect to room {room_code}. "
            f"Replacing with AI..."
        )

        # Replace player with AI
        from src.database import get_db

        async for db in get_db():
            try:
                game_room_service = GameRoomService(db)

                # Replace player with AI
                await game_room_service.replace_player_with_ai(room_code, player_id)

                # Broadcast replacement
                await sio.emit(
                    "player_replaced_by_ai",
                    {
                        "player_id": player_id,
                        "room_code": room_code,
                        "message": "玩家长时间未重连，已被AI替代"
                    },
                    room=room_code
                )

                logger.info(f"Player {player_id} replaced with AI in room {room_code}")

            except Exception as e:
                logger.error(f"Error replacing player {player_id} with AI: {e}")
            finally:
                break

        # Clean up disconnection record
        disconnected_players.pop(player_id, None)

    except asyncio.CancelledError:
        logger.info(f"Reconnection timeout cancelled for player {player_id}")
    except Exception as e:
        logger.error(f"Error in reconnection timeout handler: {e}")


@sio.event
async def join_room(sid: str, data: dict, callback=None):
    """
    Handle player joining a room via WebSocket.
    
    Args:
        sid: Socket session ID
        data: {"room_code": str, "player_id": str}
        callback: Optional callback function
    """
    try:
        room_code = data.get("room_code")
        player_id = data.get("player_id")

        if not room_code or not player_id:
            await sio.emit(
                "error",
                {"message": "room_code and player_id are required"},
                room=sid
            )
            return

        # Store player session
        user_sessions[sid] = player_id

        # Add socket to room
        await sio.enter_room(sid, room_code)
        logger.info(f"Player {player_id} joined WebSocket room {room_code}")

        # Send confirmation to the player
        await sio.emit(
            "room_joined",
            {
                "room_code": room_code,
                "player_id": player_id,
                "message": "Successfully joined room"
            },
            room=sid
        )

    except Exception as e:
        logger.error(f"Error in join_room: {e}")
        await sio.emit(
            "error",
            {"message": f"Failed to join room: {str(e)}"},
            room=sid
        )


@sio.event
async def join_lobby(sid: str, data: dict, callback=None):
    """
    Handle player joining a lobby room for real-time updates.
    Validates room exists and player is a participant before subscribing.
    
    Args:
        sid: Socket session ID
        data: {"room_code": str, "player_id": str}
        callback: Optional callback function
    """
    try:
        room_code = data.get("room_code")
        player_id = data.get("player_id")

        if not room_code or not player_id:
            await sio.emit(
                "error",
                {"message": "room_code and player_id are required"},
                room=sid
            )
            return

        # Validate room exists and player is a participant
        from src.database import get_db

        async for db in get_db():
            try:
                # Check room exists
                room_result = await db.execute(
                    select(GameRoom)
                    .where(GameRoom.code == room_code)
                )
                room = room_result.scalar_one_or_none()

                if not room:
                    await sio.emit(
                        "error",
                        {"message": "Room not found"},
                        room=sid
                    )
                    return

                # Check player is participant in room
                participant_result = await db.execute(
                    select(GameRoomParticipant)
                    .where(
                        GameRoomParticipant.game_room_id == room.id,
                        GameRoomParticipant.player_id == player_id,
                        GameRoomParticipant.left_at.is_(None)  # Active participant
                    )
                )
                participant = participant_result.scalar_one_or_none()

                if not participant:
                    await sio.emit(
                        "error",
                        {"message": "You are not a participant in this room"},
                        room=sid
                    )
                    return

                # Subscribe to lobby room
                await sio.enter_room(sid, room_code)
                logger.info(f"Player {player_id} subscribed to lobby:{room_code}")

                # Send confirmation
                await sio.emit(
                    "lobby_joined",
                    {
                        "room_code": room_code,
                        "player_id": player_id,
                        "message": "Successfully subscribed to lobby updates"
                    },
                    room=sid
                )

            except Exception as e:
                logger.error(f"Error validating lobby join: {e}")
                await sio.emit(
                    "error",
                    {"message": f"Failed to join lobby: {str(e)}"},
                    room=sid
                )
            finally:
                break

    except Exception as e:
        logger.error(f"Error in join_lobby: {e}")
        await sio.emit(
            "error",
            {"message": f"Failed to join lobby: {str(e)}"},
            room=sid
        )


@sio.event
async def leave_room(sid: str, data: dict, callback=None):
    """
    Handle player leaving a room via WebSocket.
    
    Args:
        sid: Socket session ID
        data: {"room_code": str, "player_id": str}
        callback: Optional callback function
    """
    try:
        room_code = data.get("room_code")
        player_id = data.get("player_id")

        if not room_code:
            await sio.emit(
                "error",
                {"message": "room_code is required"},
                room=sid
            )
            return

        # Remove socket from room
        await sio.leave_room(sid, room_code)
        logger.info(f"Player {player_id} left WebSocket room {room_code}")

        # Clean up session if this was their last room
        if player_id and sid in user_sessions and user_sessions[sid] == player_id:
            # We don't remove from user_sessions yet in case they're in other rooms
            pass

        # Send confirmation
        await sio.emit(
            "room_left",
            {
                "room_code": room_code,
                "player_id": player_id,
                "message": "Successfully left room"
            },
            room=sid
        )

    except Exception as e:
        logger.error(f"Error in leave_room: {e}")
        await sio.emit(
            "error",
            {"message": f"Failed to leave room: {str(e)}"},
            room=sid
        )


@sio.event
async def leave_lobby(sid: str, data: dict, callback=None):
    """
    Handle player leaving a lobby room (unsubscribe from real-time updates).
    
    Args:
        sid: Socket session ID
        data: {"room_code": str, "player_id": str}
        callback: Optional callback function
    """
    try:
        room_code = data.get("room_code")
        player_id = data.get("player_id")

        if not room_code:
            await sio.emit(
                "error",
                {"message": "room_code is required"},
                room=sid
            )
            return

        # Unsubscribe from lobby room
        await sio.leave_room(sid, room_code)
        logger.info(f"Player {player_id} unsubscribed from lobby:{room_code}")

        # Send confirmation
        await sio.emit(
            "lobby_left",
            {
                "room_code": room_code,
                "player_id": player_id,
                "message": "Successfully unsubscribed from lobby updates"
            },
            room=sid
        )

    except Exception as e:
        logger.error(f"Error in leave_lobby: {e}")
        await sio.emit(
            "error",
            {"message": f"Failed to leave lobby: {str(e)}"},
            room=sid
        )


@sio.event
async def game_action(sid: str, data: dict):
    """
    Handle player game action.
    
    Args:
        sid: Socket session ID
        data: {
            "room_code": str,
            "player_id": str,
            "action": {
                "action_type": str,
                "parameters": dict
            }
        }
    """
    try:
        from uuid import UUID

        from src.database import get_db
        from src.services.game_state_service import GameStateService

        room_code = data.get("room_code")
        player_id = data.get("player_id")
        action = data.get("action")

        if not all([room_code, player_id, action]):
            await sio.emit(
                "error",
                {"message": "room_code, player_id, and action are required"},
                room=sid
            )
            return

        # Get database session
        async for db in get_db():
            # Get game room
            result = await db.execute(
                select(GameRoom).where(GameRoom.code == room_code)
            )
            room = result.scalar_one_or_none()

            if not room:
                await sio.emit(
                    "error",
                    {"message": f"Room {room_code} not found"},
                    room=sid
                )
                return

            # Apply action
            game_state_service = GameStateService(db)

            try:
                updated_state = await game_state_service.update_state(
                    game_room_id=UUID(room.id),
                    player_id=player_id,
                    action=action
                )

                # Broadcast state update
                await broadcast_game_state_update(
                    room_code=room_code,
                    game_state=updated_state.to_dict()
                )

                # Broadcast turn changed
                await broadcast_turn_changed(
                    room_code=room_code,
                    current_player_id=updated_state.current_turn_player_id,
                    turn_number=updated_state.turn_number
                )

                # Check win condition
                winner = await game_state_service.check_win_condition(UUID(room.id))
                if winner:
                    # Record game session and update statistics
                    await game_state_service.record_game_session(
                        game_room_id=UUID(room.id),
                        winner_id=winner
                    )

                    # Get winner info
                    winner_result = await db.execute(
                        select(Player).where(Player.id == winner)
                    )
                    winner_player = winner_result.scalar_one_or_none()
                    winner_name = winner_player.username if winner_player else "Unknown"

                    # Broadcast game ended
                    await broadcast_game_ended(
                        room_code=room_code,
                        winner_id=winner,
                        winner_name=winner_name,
                        final_state=updated_state.to_dict()
                    )

            except BadRequestError as e:
                await sio.emit(
                    "error",
                    {"message": str(e)},
                    room=sid
                )
                return

            break

    except Exception as e:
        logger.error(f"Error in game_action: {e}")
        await sio.emit(
            "error",
            {"message": f"Failed to process game action: {str(e)}"},
            room=sid
        )


async def broadcast_game_state_update(
    room_code: str,
    game_state: dict[str, Any]
):
    """
    Broadcast game state update to all players in room.
    
    Args:
        room_code: Room code to broadcast to
        game_state: Updated game state
    """
    try:
        await sio.emit(
            "game_state_update",
            {
                "room_code": room_code,
                "game_state": game_state
            },
            room=room_code
        )
        logger.info(f"Broadcasted game_state_update for room {room_code}")

    except Exception as e:
        logger.error(f"Error broadcasting game_state_update: {e}")


async def broadcast_turn_changed(
    room_code: str,
    current_player_id: str,
    turn_number: int
):
    """
    Broadcast turn change to all players.
    
    Args:
        room_code: Room code to broadcast to
        current_player_id: ID of current turn player
        turn_number: Current turn number
    """
    try:
        await sio.emit(
            "turn_changed",
            {
                "room_code": room_code,
                "current_player_id": current_player_id,
                "turn_number": turn_number
            },
            room=room_code
        )
        logger.info(f"Broadcasted turn_changed for room {room_code}, turn {turn_number}")

    except Exception as e:
        logger.error(f"Error broadcasting turn_changed: {e}")


async def broadcast_player_joined(
    room_code: str,
    player_data: dict[str, Any]
):
    """
    Broadcast to all room participants that a player joined.
    
    Args:
        room_code: Room code to broadcast to
        player_data: Player information to broadcast
    """
    try:
        await sio.emit(
            "player_joined",
            {
                "room_code": room_code,
                "player": player_data,
                "timestamp": player_data.get("joined_at")
            },
            room=room_code
        )
        logger.info(f"Broadcasted player_joined for room {room_code}")

    except Exception as e:
        logger.error(f"Error broadcasting player_joined: {e}")


async def broadcast_player_left(
    room_code: str,
    player_id: str,
    player_name: str | None = None,
    reconnection_window: int = 300  # 5 minutes in seconds
):
    """
    Broadcast to all room participants that a player left.
    
    Args:
        room_code: Room code to broadcast to
        player_id: ID of player who left
        player_name: Name of player who left
        reconnection_window: Seconds until player is replaced by AI (default 5 minutes)
    """
    try:
        await sio.emit(
            "player_left",
            {
                "room_code": room_code,
                "player_id": player_id,
                "player_name": player_name,
                "reconnection_window_seconds": reconnection_window,
                "message": f"Player {player_name or player_id} left the room"
            },
            room=room_code
        )
        logger.info(f"Broadcasted player_left for room {room_code}, player {player_id}")

    except Exception as e:
        logger.error(f"Error broadcasting player_left: {e}")


async def broadcast_ownership_transferred(
    room_code: str,
    old_owner_id: str,
    new_owner_id: str,
    new_owner_name: str | None = None
):
    """
    Broadcast ownership transfer event to all room participants.
    
    Args:
        room_code: Room code to broadcast to
        old_owner_id: ID of previous owner
        new_owner_id: ID of new owner
        new_owner_name: Name of new owner
    """
    try:
        await sio.emit(
            "ownership_transferred",
            {
                "room_code": room_code,
                "old_owner_id": old_owner_id,
                "new_owner_id": new_owner_id,
                "new_owner_name": new_owner_name,
                "message": f"Room ownership transferred to {new_owner_name or new_owner_id}"
            },
            room=room_code
        )
        logger.info(f"Broadcasted ownership_transferred for room {room_code}, new owner {new_owner_id}")

    except Exception as e:
        logger.error(f"Error broadcasting ownership_transferred: {e}")


async def broadcast_room_dissolved(
    room_code: str,
    reason: str = "No human participants remain"
):
    """
    Broadcast room dissolution event to all participants.
    
    Args:
        room_code: Room code to broadcast to
        reason: Reason for dissolution
    """
    try:
        await sio.emit(
            "room_dissolved",
            {
                "room_code": room_code,
                "reason": reason,
                "message": f"Room {room_code} has been dissolved: {reason}"
            },
            room=room_code
        )
        logger.info(f"Broadcasted room_dissolved for room {room_code}: {reason}")

    except Exception as e:
        logger.error(f"Error broadcasting room_dissolved: {e}")


async def broadcast_ai_agent_added(
    room_code: str,
    ai_data: dict[str, Any]
):
    """
    Broadcast AI agent addition to all room participants.
    
    Args:
        room_code: Room code to broadcast to
        ai_data: AI agent information
    """
    try:
        await sio.emit(
            "ai_agent_added",
            {
                "room_code": room_code,
                "ai_agent": ai_data,
                "message": f"AI agent {ai_data.get('username')} added to room"
            },
            room=room_code
        )
        logger.info(f"Broadcasted ai_agent_added for room {room_code}")

    except Exception as e:
        logger.error(f"Error broadcasting ai_agent_added: {e}")


async def broadcast_ai_agent_removed(
    room_code: str,
    ai_agent_id: str,
    ai_agent_name: str | None = None
):
    """
    Broadcast AI agent removal to all room participants.
    
    Args:
        room_code: Room code to broadcast to
        ai_agent_id: ID of removed AI agent
        ai_agent_name: Name of removed AI agent
    """
    try:
        await sio.emit(
            "ai_agent_removed",
            {
                "room_code": room_code,
                "ai_agent_id": ai_agent_id,
                "ai_agent_name": ai_agent_name,
                "message": f"AI agent {ai_agent_name or ai_agent_id} removed from room"
            },
            room=room_code
        )
        logger.info(f"Broadcasted ai_agent_removed for room {room_code}")

    except Exception as e:
        logger.error(f"Error broadcasting ai_agent_removed: {e}")


async def broadcast_game_started(
    room_code: str,
    game_data: dict[str, Any]
):
    """
    Broadcast to all room participants that the game has started.
    
    Args:
        room_code: Room code to broadcast to
        game_data: Game information including participants, initial state, etc.
    """
    try:
        await sio.emit(
            "game_started",
            {
                "room_code": room_code,
                "status": "In Progress",
                "participants": game_data.get("participants", []),
                "game_type": game_data.get("game_type"),
                "initial_state": game_data.get("initial_state"),
                "started_at": game_data.get("started_at"),
                "message": "Game has started! Get ready to play."
            },
            room=room_code
        )
        logger.info(f"Broadcasted game_started for room {room_code}")

    except Exception as e:
        logger.error(f"Error broadcasting game_started: {e}")


async def broadcast_game_state_update(
    room_code: str,
    state_data: dict[str, Any]
):
    """
    Broadcast game state update to all room participants.
    
    Args:
        room_code: Room code to broadcast to
        state_data: Current game state
    """
    try:
        await sio.emit(
            "game_state_update",
            {
                "room_code": room_code,
                "state": state_data
            },
            room=room_code
        )
        logger.debug(f"Broadcasted game_state_update for room {room_code}")

    except Exception as e:
        logger.error(f"Error broadcasting game_state_update: {e}")


async def broadcast_turn_changed(
    room_code: str,
    current_player_id: str,
    current_player_name: str | None,
    turn_number: int,
    is_ai: bool = False
):
    """
    Broadcast turn change to all room participants.
    
    Args:
        room_code: Room code to broadcast to
        current_player_id: ID of player whose turn it is
        current_player_name: Name of current player
        turn_number: Current turn number
        is_ai: Whether current player is AI
    """
    try:
        await sio.emit(
            "turn_changed",
            {
                "room_code": room_code,
                "current_player_id": current_player_id,
                "current_player_name": current_player_name,
                "turn_number": turn_number,
                "is_ai": is_ai,
                "message": f"It's {current_player_name or 'AI'}'s turn"
            },
            room=room_code
        )
        logger.info(f"Broadcasted turn_changed for room {room_code}, turn {turn_number}")

    except Exception as e:
        logger.error(f"Error broadcasting turn_changed: {e}")


async def broadcast_ai_thinking(
    room_code: str,
    ai_player_id: str,
    ai_personality: str | None = None
):
    """
    Broadcast that an AI agent is thinking.
    
    Args:
        room_code: Room code to broadcast to
        ai_player_id: ID of AI agent
        ai_personality: Personality type of AI
    """
    try:
        await sio.emit(
            "ai_thinking",
            {
                "room_code": room_code,
                "ai_player_id": ai_player_id,
                "ai_personality": ai_personality,
                "message": "AI正在思考..."
            },
            room=room_code
        )
        logger.info(f"Broadcasted ai_thinking for room {room_code}")

    except Exception as e:
        logger.error(f"Error broadcasting ai_thinking: {e}")


async def broadcast_ai_action(
    room_code: str,
    ai_player_id: str,
    action: dict[str, Any]
):
    """
    Broadcast AI agent's action.
    
    Args:
        room_code: Room code to broadcast to
        ai_player_id: ID of AI agent
        action: Action data
    """
    try:
        await sio.emit(
            "ai_action",
            {
                "room_code": room_code,
                "ai_player_id": ai_player_id,
                "action": action,
                "message": "AI made a move"
            },
            room=room_code
        )
        logger.info(f"Broadcasted ai_action for room {room_code}")

    except Exception as e:
        logger.error(f"Error broadcasting ai_action: {e}")


async def broadcast_game_ended(
    room_code: str,
    winner_id: str | None,
    winner_name: str | None,
    final_state: dict[str, Any] | None = None
):
    """
    Broadcast that the game has ended.
    
    Args:
        room_code: Room code to broadcast to
        winner_id: ID of winning player (None for draw)
        winner_name: Name of winning player
        final_state: Final game state
    """
    try:
        message = f"{winner_name} wins!" if winner_id else "Game ended in a draw"

        await sio.emit(
            "game_ended",
            {
                "room_code": room_code,
                "winner_id": winner_id,
                "winner_name": winner_name,
                "final_state": final_state,
                "message": message
            },
            room=room_code
        )
        logger.info(f"Broadcasted game_ended for room {room_code}")

    except Exception as e:
        logger.error(f"Error broadcasting game_ended: {e}")


async def broadcast_game_error(
    room_code: str,
    error_type: str,
    error_message: str,
    recoverable: bool = True,
    details: dict[str, Any] | None = None
):
    """
    Broadcast a game error to all players in the room.
    
    Args:
        room_code: Room code to broadcast to
        error_type: Type of error (e.g., "llm_failure", "invalid_action", "service_unavailable")
        error_message: Human-readable error message
        recoverable: Whether the game can continue after this error
        details: Additional error context
    """
    try:
        await sio.emit(
            "game_error",
            {
                "room_code": room_code,
                "error_type": error_type,
                "message": error_message,
                "recoverable": recoverable,
                "details": details or {},
                "timestamp": datetime.utcnow().isoformat()
            },
            room=room_code
        )
        logger.warning(f"Broadcasted game_error to room {room_code}: {error_type} - {error_message}")

    except Exception as e:
        logger.error(f"Error broadcasting game_error: {e}")


async def broadcast_game_terminated(
    room_code: str,
    reason: str,
    message: str,
    final_state: dict[str, Any] | None = None
):
    """
    Broadcast that the game has been terminated due to unrecoverable error.
    
    Args:
        room_code: Room code to broadcast to
        reason: Termination reason (e.g., "service_unavailable", "llm_timeout", "critical_error")
        message: Human-readable termination message
        final_state: Final game state before termination
    """
    try:
        await sio.emit(
            "game_terminated",
            {
                "room_code": room_code,
                "reason": reason,
                "message": message,
                "final_state": final_state,
                "terminated_at": datetime.utcnow().isoformat()
            },
            room=room_code
        )
        logger.error(f"Game terminated in room {room_code}: {reason} - {message}")

    except Exception as e:
        logger.error(f"Error broadcasting game_terminated: {e}")


# =============================================================================
# Single-Player Mode Game Control Events
# =============================================================================

async def broadcast_game_paused(room_code: str):
    """
    Broadcast that the game has been paused.
    
    单人模式下用户暂停游戏时触发。
    
    Args:
        room_code: Room code to broadcast to
    """
    try:
        await sio.emit(
            "game_paused",
            {
                "room_code": room_code,
                "paused_at": datetime.utcnow().isoformat()
            },
            room=room_code
        )
        logger.info(f"Game paused in room {room_code}")

    except Exception as e:
        logger.error(f"Error broadcasting game_paused: {e}")


async def broadcast_game_resumed(room_code: str):
    """
    Broadcast that the game has been resumed.
    
    单人模式下用户恢复暂停的游戏时触发。
    
    Args:
        room_code: Room code to broadcast to
    """
    try:
        await sio.emit(
            "game_resumed",
            {
                "room_code": room_code,
                "resumed_at": datetime.utcnow().isoformat()
            },
            room=room_code
        )
        logger.info(f"Game resumed in room {room_code}")

    except Exception as e:
        logger.error(f"Error broadcasting game_resumed: {e}")


async def broadcast_game_stopped(room_code: str):
    """
    Broadcast that the game has been stopped by user.
    
    单人模式下用户主动停止游戏时触发。
    
    Args:
        room_code: Room code to broadcast to
    """
    try:
        await sio.emit(
            "game_stopped",
            {
                "room_code": room_code,
                "stopped_at": datetime.utcnow().isoformat()
            },
            room=room_code
        )
        logger.info(f"Game stopped in room {room_code}")

    except Exception as e:
        logger.error(f"Error broadcasting game_stopped: {e}")
