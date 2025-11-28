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
from src.database import get_db
from src.models.game import GameType, GameRole
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
    return GameRoomResponse(
        id=room.id,
        code=room.code,
        status=room.status,
        max_players=room.max_players,
        min_players=room.min_players,
        created_at=room.created_at,
        started_at=room.started_at,
        completed_at=room.completed_at,
        game_type=room.game_type,
        current_player_count=room.get_active_participants_count()
    )


def map_room_to_detailed_response(room) -> GameRoomDetailedResponse:
    """Map GameRoom model to detailed response schema."""
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
        game_type=room.game_type,
        current_player_count=room.get_active_participants_count(),
        participants=participants
    )


# =============================================================================
# Game Type Endpoints
# =============================================================================

@router.get("/api/v1/games", response_model=List[GameTypeResponse])
async def list_games(
    available_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """List all game types.
    
    Args:
        available_only: If True, only return available games
        db: Database session
        
    Returns:
        List of game types with details
    """
    query = select(GameType)

    if available_only:
        query = query.where(GameType.is_available == True)

    result = await db.execute(query)
    games = result.scalars().all()

    return [GameTypeResponse.from_orm(game) for game in games]


@router.get("/api/v1/games/{slug}", response_model=GameTypeResponse)
async def get_game_details(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific game.
    
    Args:
        slug: Game slug identifier
        db: Database session
        
    Returns:
        Game type details
        
    Raises:
        HTTPException: If game not found
    """
    query = select(GameType).where(GameType.slug == slug)
    result = await db.execute(query)
    game = result.scalar_one_or_none()

    if not game:
        raise HTTPException(status_code=404, detail=f"Game '{slug}' not found")

    return GameTypeResponse.from_orm(game)


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
    """
    try:
        service = GameRoomService(db)
        room = await service.create_room(
            game_type_slug=request.game_type_slug,
            max_players=request.max_players,
            min_players=request.min_players
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
        ai_agent = await service.create_ai_agent(room.id)

        # Broadcast AI agent added event
        ai_data = {
            "id": ai_agent.id,
            "username": ai_agent.username,
            "is_ai": True
        }
        await ws_handlers.broadcast_ai_agent_added(room_code, ai_data)

        # Return response
        return {
            "ai_agent": {
                "id": ai_agent.id,
                "username": ai_agent.username,
                "is_guest": ai_agent.is_guest,
                "player_type": "ai",
                "created_at": ai_agent.created_at.isoformat(),
                "last_active": ai_agent.last_active.isoformat(),
                "expires_at": ai_agent.expires_at.isoformat() if ai_agent.expires_at else None
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
                "name": room.game_type.name,
                "slug": room.game_type.slug
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
    db: AsyncSession = Depends(get_db)
):
    """Get available roles for a game type (from database).

    单人模式下，用户可以选择扮演特定角色或作为旁观者。
    """
    # Get game type
    result = await db.execute(
        select(GameType).where(GameType.slug == game_type_slug)
    )
    game_type = result.scalar_one_or_none()

    if not game_type:
        raise HTTPException(status_code=404, detail=f"Game type '{game_type_slug}' not found")

    # Load roles from DB
    roles_query = await db.execute(
        select(GameRole).where(GameRole.game_type_id == game_type.id)
    )
    roles = roles_query.scalars().all()

    return RoleListResponse(
        roles=[RoleResponse.from_orm(r) for r in roles],
        supports_spectating=game_type.supports_spectating
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

        await db.commit()
        await db.refresh(room)

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
