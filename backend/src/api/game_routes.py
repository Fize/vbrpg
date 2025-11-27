"""Game-related API endpoints.

This module consolidates all game-related REST API endpoints:
- Game types listing and details
- Room management (create, join, leave, start)
- AI agent management
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    CreateRoomRequest,
    GameRoomDetailedResponse,
    GameRoomResponse,
    GameTypeResponse,
    JoinRoomResponse,
    ParticipantResponse,
    PlayerResponse,
    RoomListResponse,
)
from src.database import get_db
from src.models.game import GameType
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


@router.post("/api/v1/rooms/{room_code}/join", response_model=JoinRoomResponse)
async def join_room(
    room_code: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Join a game room."""
    try:
        service = GameRoomService(db)
        room = await service.join_room(room_code, user_id)

        # Determine if current user is owner
        is_owner = room.owner_id == user_id

        # Map participants
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

        return JoinRoomResponse(
            room=map_room_to_detailed_response(room),
            participants=participants,
            is_owner=is_owner
        )
    except APIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete("/api/v1/rooms/{room_code}/participants/{player_id}", status_code=204)
async def leave_room(
    room_code: str,
    player_id: str,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """Remove a participant from a game room (RESTful leave endpoint)."""
    try:
        service = GameRoomService(db)

        # Get room state before leaving
        room = await service.get_room(room_code)
        player_name = None
        is_owner_leaving = False

        for participant in room.participants:
            if participant.player_id == player_id and participant.is_active():
                player_name = participant.player.username if participant.player else "Unknown"
                is_owner_leaving = participant.is_owner
                break

        # Perform leave operation
        await service.leave_room(room_code, player_id)

        # Broadcast player left event via WebSocket
        await ws_handlers.broadcast_player_left(room_code, player_id, player_name)

        # If owner left, check for ownership transfer or room dissolution
        if is_owner_leaving:
            # Reload room to check new state
            try:
                updated_room = await service.get_room(room_code)

                if updated_room.status == "Dissolved":
                    # Room was dissolved (no human participants remain)
                    await ws_handlers.broadcast_room_dissolved(
                        room_code,
                        "No human participants remain"
                    )
                else:
                    # Ownership was transferred
                    new_owner_name = None
                    for participant in updated_room.participants:
                        if participant.is_owner and participant.is_active():
                            new_owner_name = participant.player.username if participant.player else "Unknown"
                            await ws_handlers.broadcast_ownership_transferred(
                                room_code,
                                player_id,
                                participant.player_id,
                                new_owner_name
                            )
                            break
            except NotFoundError:
                # Room was deleted/dissolved
                await ws_handlers.broadcast_room_dissolved(
                    room_code,
                    "Room has been dissolved"
                )

        return Response(status_code=204)
    except APIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# =============================================================================
# AI Agent Endpoints
# =============================================================================

@router.post("/api/v1/rooms/{room_code}/ai-agents", status_code=201)
async def add_ai_agent(
    room_code: str,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """Add an AI agent to the room (owner only)."""
    try:
        service = GameRoomService(db)

        # Get room and validate owner
        room = await service.get_room(room_code)

        if room.owner_id != current_user_id:
            from src.utils.errors import ForbiddenError
            raise ForbiddenError("Only room owner can add AI agents")

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
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """Remove an AI agent from the room (owner only)."""
    try:
        service = GameRoomService(db)

        # Remove AI agent (service will validate)
        await service.remove_ai_agent(room_code, agent_id, current_user_id)

        # Broadcast AI agent removed event
        # Note: We don't need AI name for this event as client has the ID
        await ws_handlers.broadcast_ai_agent_removed(room_code, agent_id, None)

        return Response(status_code=204)
    except APIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/api/v1/rooms/{room_code}/start", response_model=GameRoomDetailedResponse)
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
