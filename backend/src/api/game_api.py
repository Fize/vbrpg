"""Compatibility shim: re-export router from `src.api.rooms`."""
from src.api.rooms import router

# Deprecated: `game_api` used to include full route implementations. We now
# serve those routes from `src.api.rooms` directly. The module remains to
# preserve any imports of `src.api.game_api.router`.

from datetime import datetime
from typing import Dict, Generic, List, Optional, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_db
from src.models.game_room import GameRoom
from src.models.game_type import GameType
from src.models.game_room_participant import GameRoomParticipant
from src.models.ai_agent import AIAgent
from src.services.game_room_service import GameRoomService
from src.utils.config import session_security, BaseResponse, PaginatedResponse
from src.utils.errors import RoomNotFoundError, RoomFullError, GameAlreadyStartedError

T = TypeVar("T")


class CreateRoomRequest(BaseModel):
    """Request model for creating a room."""
    game_type_slug: str
    max_players: int = 4
    min_players: int = 2


class AddAIRequest(BaseModel):
    """Request model for adding AI agent."""
    personality_type: str  # aggressive, defensive, balanced
    difficulty_level: int  # 1-5


class GameRoomResponse(BaseModel):
    """Response model for game room."""
    id: str
    code: str
    status: str
    max_players: int
    min_players: int
    current_player_count: int
    game_type: dict
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    participants: List[dict] = []


# Create router
router = APIRouter(prefix="/api/v1/rooms", tags=["Game Rooms"])


@router.post("", response_model=BaseResponse[GameRoomResponse], status_code=status.HTTP_201_CREATED)
async def create_room(
    request: CreateRoomRequest,
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(session_security)
) -> BaseResponse[GameRoomResponse]:
    """Create a new game room."""
    # Create room with session auto-join
    room = await GameRoomService.create_room(
        db,
        request.game_type_slug,
        request.max_players,
        request.min_players,
        session_id
    )
    
    # Get game type
    result = await db.execute(
        select(GameType).where(GameType.id == room.game_type_id)
    )
    game_type = result.scalar_one()
    
    # Get participants
    participants_result = await db.execute(
        select(GameRoomParticipant).where(
            GameRoomParticipant.game_room_id == room.id,
            GameRoomParticipant.left_at.is_(None)
        )
    )
    participants = participants_result.scalars().all()
    
    # Transform participants to response format
    participant_data = []
    for p in participants:
        if p.is_ai_agent:
            participant_data.append({
                "id": p.id,
                "is_ai_agent": True,
                "ai_personality": p.ai_personality,
                "joined_at": p.joined_at.isoformat()
            })
        else:
            participant_data.append({
                "id": p.id,
                "is_ai_agent": False,
                "joined_at": p.joined_at.isoformat()
            })
    
    return BaseResponse(
        message="Room created successfully",
        data=GameRoomResponse(
            id=room.id,
            code=room.code,
            status=room.status,
            max_players=room.max_players,
            min_players=room.min_players,
            current_player_count=room.get_active_participants_count(),
            game_type={
                "id": game_type.id,
                "name": game_type.name,
                "slug": game_type.slug,
                "description": game_type.description,
                "max_ai_opponents": game_type.max_ai_opponents,
                "min_ai_opponents": game_type.min_ai_opponents
            },
            created_at=room.created_at.isoformat(),
            started_at=room.started_at.isoformat() if room.started_at else None,
            completed_at=room.completed_at.isoformat() if room.completed_at else None,
            participants=participant_data
        )
    )


@router.get("", response_model=BaseResponse[PaginatedResponse[dict]])
async def list_rooms(
    status_filter: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
) -> BaseResponse[PaginatedResponse[dict]]:
    """List game rooms."""
    query = select(GameRoom)
    
    # Filter by status
    if status_filter:
        query = query.where(GameRoom.status == status_filter)
    
    # Execute query
    result = await db.execute(query.limit(limit))
    rooms = result.scalars().all()
    
    # Transform rooms to response format
    room_data = []
    for room in rooms:
        # Get game type
        gt_result = await db.execute(
            select(GameType).where(GameType.id == room.game_type_id)
        )
        game_type = gt_result.scalar_one()
        
        room_data.append({
            "id": room.id,
            "code": room.code,
            "status": room.status,
            "max_players": room.max_players,
            "min_players": room.min_players,
            "current_player_count": room.get_active_participants_count(),
            "game_type": {
                "id": game_type.id,
                "name": game_type.name,
                "slug": game_type.slug
            },
            "created_at": room.created_at.isoformat(),
            "started_at": room.started_at.isoformat() if room.started_at else None,
            "completed_at": room.completed_at.isoformat() if room.completed_at else None
        })
    
    return BaseResponse(
        message="Rooms retrieved successfully",
        data=PaginatedResponse(
            items=room_data,
            total=len(room_data),
            page=1,
            per_page=limit
        )
    )


@router.get("/{room_code}", response_model=BaseResponse[GameRoomResponse])
async def get_room(
    room_code: str,
    db: AsyncSession = Depends(get_db)
) -> BaseResponse[GameRoomResponse]:
    """Get room details."""
    room = await GameRoomService.get_room_by_code(db, room_code)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    # Get game type
    result = await db.execute(
        select(GameType).where(GameType.id == room.game_type_id)
    )
    game_type = result.scalar_one()
    
    # Get participants
    participants_result = await db.execute(
        select(GameRoomParticipant).where(
            GameRoomParticipant.game_room_id == room.id,
            GameRoomParticipant.left_at.is_(None)
        )
    )
    participants = participants_result.scalars().all()
    
    # Transform participants
    participant_data = []
    for p in participants:
        if p.is_ai_agent:
            participant_data.append({
                "id": p.id,
                "is_ai_agent": True,
                "ai_personality": p.ai_personality,
                "joined_at": p.joined_at.isoformat()
            })
        else:
            participant_data.append({
                "id": p.id,
                "is_ai_agent": False,
                "joined_at": p.joined_at.isoformat()
            })
    
    return BaseResponse(
        message="Room retrieved successfully",
        data=GameRoomResponse(
            id=room.id,
            code=room.code,
            status=room.status,
            max_players=room.max_players,
            min_players=room.min_players,
            current_player_count=room.get_active_participants_count(),
            game_type={
                "id": game_type.id,
                "name": game_type.name,
                "slug": game_type.slug,
                "description": game_type.description,
                "max_ai_opponents": game_type.max_ai_opponents,
                "min_ai_opponents": game_type.min_ai_opponents
            },
            created_at=room.created_at.isoformat(),
            started_at=room.started_at.isoformat() if room.started_at else None,
            completed_at=room.completed_at.isoformat() if room.completed_at else None,
            participants=participant_data
        )
    )


@router.post("/{room_code}/join", response_model=BaseResponse[dict])
async def join_room(
    room_code: str,
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(session_security)
) -> BaseResponse[dict]:
    """Join a game room."""
    participant = await GameRoomService.join_room(db, room_code, session_id)
    
    return BaseResponse(
        message="Joined room successfully",
        data={
            "participant_id": participant.id,
            "room_code": room_code,
            "joined_at": participant.joined_at.isoformat()
        }
    )


@router.post("/{room_code}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_room(
    room_code: str,
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(session_security)
):
    """Leave a game room."""
    await GameRoomService.leave_room(db, room_code, session_id)


@router.delete("/{room_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_code: str,
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(session_security)
):
    """Delete a game room (Waiting status only)."""
    await GameRoomService.delete_room(db, room_code, session_id)


@router.post("/{room_code}/ai-agents", response_model=BaseResponse[dict])
async def add_ai_agent(
    room_code: str,
    request: AddAIRequest,
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(session_security)
) -> BaseResponse[dict]:
    """Add AI agent to room."""
    participant, ai_agent = await GameRoomService.add_ai_agent(
        db,
        room_code,
        request.personality_type,
        request.difficulty_level
    )
    
    return BaseResponse(
        message="AI agent added successfully",
        data={
            "participant_id": participant.id,
            "ai_agent_id": ai_agent.id,
            "username": ai_agent.username,
            "personality_type": ai_agent.personality_type,
            "difficulty_level": ai_agent.difficulty_level,
            "added_at": participant.joined_at.isoformat()
        }
    )


@router.get("/{room_code}/ai-agents", response_model=BaseResponse[List[dict]])
async def list_ai_agents(
    room_code: str,
    db: AsyncSession = Depends(get_db)
) -> BaseResponse[List[dict]]:
    """List AI agents in room."""
    room = await GameRoomService.get_room_by_code(db, room_code)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    # Get AI participants
    result = await db.execute(
        select(GameRoomParticipant).where(
            GameRoomParticipant.game_room_id == room.id,
            GameRoomParticipant.is_ai_agent == True,
            GameRoomParticipant.left_at.is_(None)
        )
    )
    ai_participants = result.scalars().all()
    
    ai_data = []
    for p in ai_participants:
        ai_data.append({
            "id": p.id,
            "username": f"AI玩家{room.ai_agent_counter}",
            "personality_type": p.ai_personality,
            "joined_at": p.joined_at.isoformat()
        })
    
    return BaseResponse(
        message="AI agents retrieved successfully",
        data=ai_data
    )


@router.delete("/{room_code}/ai-agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_ai_agent(
    room_code: str,
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(session_security)
):
    """Remove AI agent from room."""
    await GameRoomService.remove_ai_agent(db, room_code, agent_id)


@router.post("/{room_code}/start", response_model=BaseResponse[GameRoomResponse])
async def start_game(
    room_code: str,
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(session_security)
) -> BaseResponse[GameRoomResponse]:
    """Start a game in room."""
    room = await GameRoomService.start_game(db, room_code)
    
    # Get game type
    result = await db.execute(
        select(GameType).where(GameType.id == room.game_type_id)
    )
    game_type = result.scalar_one()
    
    # Get participants
    participants_result = await db.execute(
        select(GameRoomParticipant).where(
            GameRoomParticipant.game_room_id == room.id,
            GameRoomParticipant.left_at.is_(None)
        )
    )
    participants = participants_result.scalars().all()
    
    # Transform participants
    participant_data = []
    for p in participants:
        if p.is_ai_agent:
            participant_data.append({
                "id": p.id,
                "is_ai_agent": True,
                "ai_personality": p.ai_personality,
                "joined_at": p.joined_at.isoformat()
            })
        else:
            participant_data.append({
                "id": p.id,
                "is_ai_agent": False,
                "joined_at": p.joined_at.isoformat()
            })
    
    return BaseResponse(
        message="Game started successfully",
        data=GameRoomResponse(
            id=room.id,
            code=room.code,
            status=room.status,
            max_players=room.max_players,
            min_players=room.min_players,
            current_player_count=room.get_active_participants_count(),
            game_type={
                "id": game_type.id,
                "name": game_type.name,
                "slug": game_type.slug
            },
            created_at=room.created_at.isoformat(),
            started_at=room.started_at.isoformat() if room.started_at else None,
            completed_at=room.completed_at.isoformat() if room.completed_at else None,
            participants=participant_data
        )
    )