"""Game-related API endpoints.

This module consolidates all game-related REST API endpoints:
- Game types listing and details
- Room management (create, start)
- AI agent management
- Role selection (单人模式)
- Game control (pause/resume/stop)
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    CreateRoomRequest,
    GameControlResponse,
    GameRoomDetailedResponse,
    GameRoomResponse,
    GameTypeResponse,
    ParticipantResponse,
    PlayerResponse,
    RoleListResponse,
    RoleResponse,
    RoomListResponse,
    SelectRoleRequest,
)
from src.constants import GAME_TYPES, get_game_type_by_slug, ROLES_BY_GAME, get_roles_by_game_slug
from src.database import get_db
from src.services.ai_service import AIAgentService
from src.services.game_room_service import GameRoomService
from src.utils.errors import APIError, NotFoundError
from src.websocket import handlers as ws_handlers

logger = logging.getLogger(__name__)

# Create router with combined game routes
router = APIRouter(tags=["games"])


# =============================================================================
# Helper Functions
# =============================================================================


def map_room_to_response(room) -> GameRoomResponse:
    """Map GameRoom model to response schema."""
    game_type = get_game_type_by_slug(room.game_type_id)
    return GameRoomResponse(
        id=room.id,
        code=room.code,
        status=room.status,
        max_players=room.max_players,
        min_players=room.min_players,
        created_at=room.created_at,
        started_at=room.started_at,
        completed_at=room.completed_at,
        game_type=game_type,
        current_player_count=room.get_active_participants_count()
    )


def map_room_to_detailed_response(room) -> GameRoomDetailedResponse:
    """Map GameRoom model to detailed response schema."""
    game_type = get_game_type_by_slug(room.game_type_id)
    participants = []
    for p in room.participants:
        participants.append(ParticipantResponse(
            id=p.id,
            player=PlayerResponse.from_orm(p.player) if p.player else None,
            is_ai_agent=p.is_ai_agent,
            ai_personality=p.ai_personality,
            joined_at=p.joined_at,
            left_at=p.left_at,
            replaced_by_ai=p.replaced_by_ai
        ))

    return GameRoomDetailedResponse(
        id=room.id,
        code=room.code,
        status=room.status,
        max_players=room.max_players,
        min_players=room.min_players,
        created_at=room.created_at,
        started_at=room.started_at,
        completed_at=room.completed_at,
        game_type=game_type,
        current_player_count=room.get_active_participants_count(),
        participants=participants,
        user_role=room.user_role,
        is_spectator_mode=room.is_spectator_mode
    )


# =============================================================================
# Game Type Endpoints
# =============================================================================

@router.get("/api/v1/games", response_model=List[GameTypeResponse])
async def list_games(
    available_only: bool = False,
):
    """List all game types.
    
    Args:
        available_only: If True, only return available games
        
    Returns:
        List of game types with details
    """
    games = GAME_TYPES
    if available_only:
        games = [g for g in games if g["is_available"]]

    return [GameTypeResponse(**game) for game in games]


@router.get("/api/v1/games/{slug}", response_model=GameTypeResponse)
async def get_game_details(
    slug: str,
):
    """Get detailed information about a specific game.
    
    Args:
        slug: Game slug identifier
        
    Returns:
        Game type details
        
    Raises:
        HTTPException: If game not found
    """
    game = get_game_type_by_slug(slug)

    if not game:
        raise HTTPException(status_code=404, detail=f"Game '{slug}' not found")

    return GameTypeResponse(**game)


# =============================================================================
# Room Management Endpoints
# =============================================================================

@router.post("/api/v1/rooms", response_model=GameRoomDetailedResponse, status_code=201)
async def create_room(
    request: CreateRoomRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new game room for single-player mode.
    
    All players are AI agents. User can be spectator or participant.
    Room is automatically filled with AI agents (10 for werewolf).
    """
    try:
        service = GameRoomService(db)
        room = await service.create_room(
            game_type_slug=request.game_type_slug,
            max_players=request.max_players,
            min_players=request.min_players,
            user_role=request.user_role,
            is_spectator_mode=request.is_spectator_mode,
        )
        return map_room_to_detailed_response(room)
    except APIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/api/v1/rooms", response_model=RoomListResponse)
async def list_rooms(
    status: str | None = Query(None),
    game_type: str | None = Query(None, alias="gameType"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List game rooms with optional filtering."""
    try:
        service = GameRoomService(db)
        rooms = await service.list_rooms(
            status=status,
            game_type_slug=game_type,
            limit=limit
        )
        return RoomListResponse(
            rooms=[map_room_to_response(room) for room in rooms],
            total=len(rooms)
        )
    except APIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/api/v1/rooms/{room_code}", response_model=GameRoomDetailedResponse)
async def get_room(
    room_code: str,
    db: AsyncSession = Depends(get_db)
):
    """Get room details by code."""
    try:
        service = GameRoomService(db)
        room = await service.get_room(room_code)
        return map_room_to_detailed_response(room)
    except APIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# 单人模式下移除了以下端点：
# - POST /api/v1/rooms/{room_code}/join (加入房间)
# - DELETE /api/v1/rooms/{room_code}/participants/{player_id} (离开房间)
# 所有玩家都是 AI，用户只能观战或参与


# =============================================================================
# AI Agent Endpoints
# =============================================================================

@router.post("/api/v1/rooms/{room_code}/ai-agents", status_code=201)
async def add_ai_agent(
    room_code: str,
    db: AsyncSession = Depends(get_db)
):
    """Add an AI agent to the room.
    
    单人模式下，用户可以随时添加 AI 代理。
    """
    try:
        service = GameRoomService(db)

        # Get room
        room = await service.get_room(room_code)

        # Validate room status
        if room.status != "Waiting":
            from src.utils.errors import GameAlreadyStartedError
            raise GameAlreadyStartedError("Cannot add AI agents after game starts")

        # Validate capacity
        if room.current_participant_count >= room.max_players:
            from src.utils.errors import RoomFullError
            raise RoomFullError("Room is at maximum capacity")

        # Create AI agent
        participant = await service.create_ai_agent(room.id)

        # Broadcast AI agent added event
        ai_data = {
            "id": participant.id,
            "username": participant.player.username,
            "is_ai": True
        }
        await ws_handlers.broadcast_ai_agent_added(room_code, ai_data)

        # Return response
        return {
            "ai_agent": {
                "id": participant.id,
                "username": participant.player.username,
                "is_guest": participant.player.is_guest,
                "player_type": "ai",
                "created_at": participant.joined_at.isoformat(),
                "last_active": participant.player.last_active.isoformat(),
                "expires_at": participant.player.expires_at.isoformat() if participant.player.expires_at else None
            },
            "room_code": room_code
        }
    except APIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete("/api/v1/rooms/{room_code}/ai-agents/{agent_id}", status_code=204)
async def remove_ai_agent(
    room_code: str,
    agent_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Remove an AI agent from the room.
    
    单人模式下，用户可以随时移除 AI 代理。
    """
    try:
        service = GameRoomService(db)

        # Remove AI agent (service will validate)
        await service.remove_ai_agent(room_code, agent_id)

        # Broadcast AI agent removed event
        # Note: We don't need AI name for this event as client has the ID
        await ws_handlers.broadcast_ai_agent_removed(room_code, agent_id, None)

        return Response(status_code=204)
    except APIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/api/v1/rooms/{room_code}/start", response_model=GameRoomDetailedResponse)
async def start_game(
    room_code: str,
    db: AsyncSession = Depends(get_db)
):
    """Start a game. Auto-fills empty slots with AI agents.
    
    单人模式下，所有玩家都是 AI 代理。
    """
    try:
        room_service = GameRoomService(db)
        ai_service = AIAgentService(db)

        # Get room
        room = await room_service.get_room(room_code)

        # Fill empty slots with AI agents
        await ai_service.fill_empty_slots(room)

        # Refresh room to get AI participants
        await db.refresh(room)

        # Start game (no owner validation in single-player mode)
        room = await room_service.start_game(room_code)

        # Get game type from constants
        game_type = get_game_type_by_slug(room.game_type_id)

        # Prepare game data for broadcast
        game_data = {
            "participants": [
                {
                    "id": p.player_id,
                    "name": p.player.username if p.player else f"AI-{p.ai_personality}",
                    "is_ai": p.is_ai_agent,
                    "personality": p.ai_personality
                }
                for p in room.participants if p.is_active()
            ],
            "game_type": {
                "name": game_type["name"] if game_type else "Unknown",
                "slug": game_type["slug"] if game_type else room.game_type_id
            },
            "started_at": room.started_at.isoformat() if room.started_at else None,
            "initial_state": None  # Will be populated by GameStateService in Phase 4
        }

        # Broadcast game started event via WebSocket
        await ws_handlers.broadcast_game_started(room_code, game_data)

        return map_room_to_detailed_response(room)
    except APIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# =============================================================================
# Role Selection Endpoints (单人模式)
# =============================================================================

@router.get("/api/v1/games/{game_type_slug}/roles", response_model=RoleListResponse)
async def get_roles(
    game_type_slug: str,
):
    """Get available roles for a game type (from constants).

    单人模式下，用户可以选择扮演特定角色或作为旁观者。
    """
    # Get game type from constants
    game_type = get_game_type_by_slug(game_type_slug)

    if not game_type:
        raise HTTPException(status_code=404, detail=f"Game type '{game_type_slug}' not found")

    # Load roles from constants
    roles = get_roles_by_game_slug(game_type_slug) or []

    return RoleListResponse(
        roles=[RoleResponse(**r) for r in roles],
        supports_spectating=game_type["supports_spectating"]
    )


@router.post("/api/v1/rooms/{room_code}/select-role", response_model=GameRoomDetailedResponse)
async def select_role(
    room_code: str,
    request: SelectRoleRequest,
    db: AsyncSession = Depends(get_db)
):
    """Select a role for the current game.
    
    单人模式下，用户选择角色后将锁定，游戏自动开始。
    """
    try:
        from src.models.game import GameRoomParticipant
        from src.models.user import Player

        service = GameRoomService(db)
        room = await service.get_room(room_code)

        if room.status != "Waiting":
            raise HTTPException(status_code=400, detail="Cannot select role after game starts")

        # Update room with user's role selection
        if request.is_spectator:
            room.user_role = "spectator"
            room.is_spectator_mode = True
        else:
            room.user_role = request.role_id
            room.is_spectator_mode = False

            if not request.player_id:
                raise HTTPException(status_code=400, detail="player_id is required for player mode")

            # Ensure human player exists
            human_player = await db.get(Player, request.player_id)
            if not human_player:
                human_player = Player(
                    id=request.player_id,
                    username=f"玩家_{request.player_id[:8]}",
                    is_guest=True,
                )
                db.add(human_player)
                await db.flush()

            # Ensure human participant exists
            has_human_participant = any(
                (p.left_at is None and p.player_id == request.player_id and not p.is_ai_agent)
                for p in room.participants
            )
            logger.info(
                f"select_role check: room={room_code}, has_human_participant={has_human_participant}, "
                f"player_id={request.player_id}, participant_count_before={room.get_active_participants_count()}"
            )
            if not has_human_participant:
                human_participant = GameRoomParticipant(
                    game_room_id=room.id,
                    player_id=human_player.id,
                    is_ai_agent=False,
                    is_owner=True,
                )
                db.add(human_participant)
                logger.info(f"Created human participant for player_id={request.player_id} in room {room_code}")

        await db.flush()  # Flush to database before commit
        await db.commit()

        # Fill AI participants after role selection
        # Expire the room object to force reload from database
        db.expire(room)
        room = await service.get_room(room_code)
        current_count = room.get_active_participants_count()
        target_total = room.max_players
        needed = target_total - current_count
        
        logger.info(
            f"select_role AI fill: room={room_code}, current_count={current_count}, "
            f"target_total={target_total}, needed={needed}, "
            f"participants={[(p.player_id, p.is_ai_agent, p.left_at) for p in room.participants]}"
        )

        for i in range(needed):
            try:
                await service.create_ai_agent(room.id)
                logger.info(f"Created AI agent {i + 1}/{needed} for room {room_code}")
            except Exception as e:
                logger.warning("Failed to add AI agent: %s", e)
                break

        # Refresh room with all participants
        room = await service.get_room(room_code)
        return map_room_to_detailed_response(room)
    except APIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# =============================================================================
# Game Control Endpoints (暂停/恢复/停止)
# =============================================================================

@router.post("/api/v1/rooms/{room_code}/pause", response_model=GameControlResponse)
async def pause_game(
    room_code: str,
    db: AsyncSession = Depends(get_db)
):
    """Pause the current game.
    
    单人模式下，用户可以随时暂停游戏。
    """
    try:
        service = GameRoomService(db)
        room = await service.get_room(room_code)

        if room.status != "In Progress":
            raise HTTPException(status_code=400, detail="Game is not in progress")

        # Update status to Paused
        room.status = "Paused"
        await db.commit()

        # Broadcast pause event
        await ws_handlers.broadcast_game_paused(room_code)

        return GameControlResponse(
            room_code=room_code,
            status="Paused",
            message="游戏已暂停"
        )
    except APIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/api/v1/rooms/{room_code}/resume", response_model=GameControlResponse)
async def resume_game(
    room_code: str,
    db: AsyncSession = Depends(get_db)
):
    """Resume a paused game.
    
    恢复已暂停的游戏。
    """
    try:
        service = GameRoomService(db)
        room = await service.get_room(room_code)

        if room.status != "Paused":
            raise HTTPException(status_code=400, detail="Game is not paused")

        # Update status back to In Progress
        room.status = "In Progress"
        await db.commit()

        # Broadcast resume event
        await ws_handlers.broadcast_game_resumed(room_code)

        return GameControlResponse(
            room_code=room_code,
            status="In Progress",
            message="游戏已恢复"
        )
    except APIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/api/v1/rooms/{room_code}/stop", response_model=GameControlResponse)
async def stop_game(
    room_code: str,
    db: AsyncSession = Depends(get_db)
):
    """Stop the current game.
    
    停止并结束当前游戏。
    """
    try:
        service = GameRoomService(db)
        room = await service.get_room(room_code)

        if room.status not in ["In Progress", "Paused"]:
            raise HTTPException(status_code=400, detail="Game is not running")

        # Complete the game
        room.complete()
        await db.commit()

        # Broadcast stop event
        await ws_handlers.broadcast_game_stopped(room_code)

        return GameControlResponse(
            room_code=room_code,
            status="Completed",
            message="游戏已停止"
        )
    except APIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
