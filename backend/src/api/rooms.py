"""REST API endpoints for game rooms."""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    CreateRoomRequest,
    GameRoomDetailedResponse,
    GameRoomResponse,
    ParticipantResponse,
    PlayerResponse,
    RoomListResponse
)
from src.database import get_db
from src.services.game_room_service import GameRoomService
from src.services.ai_agent_service import AIAgentService
from src.utils.errors import APIError
from src.websocket import handlers as ws_handlers

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1", tags=["rooms"])

# Temporary: Mock current user (will be replaced with real auth)
async def get_current_user_id() -> str:
    """Get current authenticated user ID."""
    # TODO: Implement real authentication
    return "temp-user-id-123"


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


@router.post("/rooms", response_model=GameRoomDetailedResponse, status_code=201)
async def create_room(
    request: CreateRoomRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Create a new game room."""
    try:
        service = GameRoomService(db)
        room = await service.create_room(
            game_type_slug=request.game_type_slug,
            max_players=request.max_players,
            min_players=request.min_players,
            creator_id=user_id
        )
        return map_room_to_detailed_response(room)
    except APIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/rooms", response_model=RoomListResponse)
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


@router.get("/rooms/{room_code}", response_model=GameRoomDetailedResponse)
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


@router.post("/rooms/{room_code}/join", response_model=GameRoomDetailedResponse)
async def join_room(
    room_code: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Join a game room."""
    try:
        service = GameRoomService(db)
        room = await service.join_room(room_code, user_id)
        
        # Broadcast player joined event via WebSocket
        player_data = None
        for participant in room.participants:
            if participant.player_id == user_id and participant.is_active():
                player_data = {
                    "id": participant.player_id,
                    "name": participant.player.display_name if participant.player else "Unknown",
                    "is_ai": participant.is_ai_agent,
                    "joined_at": participant.joined_at.isoformat()
                }
                break
        
        if player_data:
            await ws_handlers.broadcast_player_joined(room_code, player_data)
        
        return map_room_to_detailed_response(room)
    except APIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/rooms/{room_code}/leave")
async def leave_room(
    room_code: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Leave a game room."""
    try:
        service = GameRoomService(db)
        
        # Get player name before leaving
        room = await service.get_room(room_code)
        player_name = None
        for participant in room.participants:
            if participant.player_id == user_id and participant.is_active():
                player_name = participant.player.username if participant.player else "Unknown"
                break
        
        await service.leave_room(room_code, user_id)
        
        # Broadcast player left event via WebSocket
        await ws_handlers.broadcast_player_left(room_code, user_id, player_name)
        
        return {"message": "Successfully left room"}
    except APIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/rooms/{room_code}/start", response_model=GameRoomDetailedResponse)
async def start_game(
    room_code: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Start a game (creator only). Auto-fills empty slots with AI agents."""
    try:
        room_service = GameRoomService(db)
        ai_service = AIAgentService(db)
        
        # Get room
        room = await room_service.get_room(room_code)
        
        # Fill empty slots with AI agents
        await ai_service.fill_empty_slots(room)
        
        # Refresh room to get AI participants
        await db.refresh(room)
        
        # Start game
        room = await room_service.start_game(room_code, user_id)
        
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

