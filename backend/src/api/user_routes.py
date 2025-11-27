"""User-related API endpoints.

This module consolidates all user-related REST API endpoints:
- Player management (create guest, get profile, upgrade)
- Session management (create, get, extend, delete)
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import PlayerResponse
from src.database import get_db
from src.models.user import Session
from src.services.player_service import PlayerService
from src.utils.config import BaseResponse
from src.utils.errors import BadRequestError, NotFoundError
from src.utils.sessions import SessionManager

# Create router with combined user routes
router = APIRouter(tags=["users"])


# =============================================================================
# Request/Response Models
# =============================================================================

class UpgradeAccountRequest(BaseModel):
    """Request body for upgrading guest account."""
    username: str


class PlayerStatsResponse(BaseModel):
    """Player statistics response."""
    player_id: str
    username: str
    is_guest: bool
    total_games: int
    wins: int
    win_rate: float
    favorite_game: str | None
    total_play_time_minutes: int
    created_at: str
    last_active_at: str | None


class SessionCreateResponse(BaseModel):
    """Response model for session creation."""
    id: str
    session_id: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class SessionResponse(BaseModel):
    """Response model for session details."""
    id: str
    session_id: str
    created_at: datetime
    last_active: datetime
    expires_at: Optional[datetime] = None
    is_expired: bool


# =============================================================================
# Player Endpoints
# =============================================================================

@router.post("/api/v1/players/guest", response_model=PlayerResponse, status_code=201)
async def create_guest_account(
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Create a new guest account.
    
    Automatically generates a username in format: Guest_形容词_动物
    Sets session cookie for the new guest player.
    
    Returns:
        The created guest player
    """
    service = PlayerService(db)

    try:
        player = await service.create_guest()

        # Create session
        SessionManager.create_session(response, player.id)

        return PlayerResponse.from_orm(player)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/players/me", response_model=PlayerResponse)
async def get_current_player(
    session_cookie: str = Depends(SessionManager.get_player_from_session),
    db: AsyncSession = Depends(get_db)
):
    """Get current player profile.
    
    Requires valid session cookie.
    
    Returns:
        Current player information
    """
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = PlayerService(db)

    try:
        player, _ = await service.get_profile(session_cookie)
        return PlayerResponse.from_orm(player)

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/v1/players/me/upgrade", response_model=PlayerResponse)
async def upgrade_account(
    request: UpgradeAccountRequest,
    session_cookie: str = Depends(SessionManager.get_player_from_session),
    db: AsyncSession = Depends(get_db)
):
    """Upgrade guest account to permanent.
    
    Changes username from Guest_X_X to chosen permanent username.
    Removes account expiration.
    
    Args:
        request: New username
        
    Returns:
        Updated player information
    """
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = PlayerService(db)

    try:
        player = await service.upgrade_to_permanent(
            session_cookie,
            request.username
        )
        return PlayerResponse.from_orm(player)

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/v1/players/me/stats", response_model=PlayerStatsResponse)
async def get_player_stats(
    session_cookie: str = Depends(SessionManager.get_player_from_session),
    db: AsyncSession = Depends(get_db)
):
    """Get player statistics.
    
    Returns game history, win rate, and other statistics.
    
    Returns:
        Player statistics
    """
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = PlayerService(db)

    try:
        stats = await service.get_stats(session_cookie)
        return PlayerStatsResponse(**stats)

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# Session Endpoints
# =============================================================================

@router.post(
    "/api/v1/sessions",
    response_model=BaseResponse[SessionCreateResponse],
    status_code=status.HTTP_201_CREATED
)
async def create_session(
    expires_hours: int = 24,
    db: AsyncSession = Depends(get_db)
) -> BaseResponse[SessionCreateResponse]:
    """Create a new session for single-user gaming."""
    session_id = str(uuid.uuid4())

    # Create new session
    new_session = Session.create_new(session_id, expires_hours)
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)

    return BaseResponse(
        message="Session created successfully",
        data=SessionCreateResponse(
            id=new_session.id,
            session_id=new_session.session_id,
            created_at=new_session.created_at,
            expires_at=new_session.expires_at
        )
    )


@router.get("/api/v1/sessions/{session_id}", response_model=BaseResponse[SessionResponse])
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
) -> BaseResponse[SessionResponse]:
    """Get session details."""
    result = await db.execute(
        select(Session).where(Session.session_id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    return BaseResponse(
        message="Session retrieved successfully",
        data=SessionResponse(
            id=session.id,
            session_id=session.session_id,
            created_at=session.created_at,
            last_active=session.last_active,
            expires_at=session.expires_at,
            is_expired=session.is_expired()
        )
    )


@router.post(
    "/api/v1/sessions/{session_id}/extend",
    response_model=BaseResponse[SessionResponse]
)
async def extend_session(
    session_id: str,
    hours: int = 24,
    db: AsyncSession = Depends(get_db)
) -> BaseResponse[SessionResponse]:
    """Extend session expiry."""
    result = await db.execute(
        select(Session).where(Session.session_id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if session.is_expired():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot extend expired session"
        )

    # Extend session
    session.extend_expiry(hours)
    await db.commit()
    await db.refresh(session)

    return BaseResponse(
        message="Session extended successfully",
        data=SessionResponse(
            id=session.id,
            session_id=session.session_id,
            created_at=session.created_at,
            last_active=session.last_active,
            expires_at=session.expires_at,
            is_expired=session.is_expired()
        )
    )


@router.delete("/api/v1/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a session."""
    result = await db.execute(
        select(Session).where(Session.session_id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    await db.delete(session)
    await db.commit()
