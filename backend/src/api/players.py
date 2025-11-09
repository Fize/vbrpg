"""Players API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.database import get_db
from src.services.player_service import PlayerService
from src.utils.sessions import SessionManager
from src.utils.errors import NotFoundError, BadRequestError
from src.api.schemas import PlayerResponse


router = APIRouter(prefix="/api/v1/players", tags=["players"])


# Request/Response models
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


@router.post("/guest", response_model=PlayerResponse, status_code=201)
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


@router.get("/me", response_model=PlayerResponse)
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


@router.post("/me/upgrade", response_model=PlayerResponse)
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


@router.get("/me/stats", response_model=PlayerStatsResponse)
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
