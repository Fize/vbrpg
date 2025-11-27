"""Compatibility shim for legacy `core_api` imports.

This module exposes `sessions_router` and `game_types_router` for backward
compatibility. It delegates to the newer modules in `src.api`.
"""
from fastapi import APIRouter

from src.api.sessions import router as sessions_router
from src.api.games import list_games, get_game_details

# Create a minimal APIRouter for game types so older imports keep working
game_types_router = APIRouter(prefix="/api/v1/game-types", tags=["Game Types"])


# Response Models
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


class GameTypeResponse(BaseModel):
    """Response model for game type."""
    id: str
    name: str
    slug: str
    description: str
    min_ai_opponents: int
    max_ai_opponents: int
    supports_spectating: bool


@game_types_router.get("")
async def _list_game_types():
    """Compatibility wrapper around `list_games` in `games.py`."""
    return await list_games()


@game_types_router.get("/{slug}")
async def _get_game_details(slug: str):
    """Compatibility wrapper around `get_game_details` in `games.py`."""
    return await get_game_details(slug)


# Note: Sessions are handled by `src.api.sessions`. This shim keeps the old
# module name for backward compatibility while delegating to the new module.


@sessions_router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
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


# Game Types Endpoints
@game_types_router.get("", response_model=BaseResponse[list[GameTypeResponse]])
async def list_game_types(
    db: AsyncSession = Depends(get_db)
) -> BaseResponse[list[GameTypeResponse]]:
    """List all available game types."""
    result = await db.execute(select(GameType).where(GameType.is_available))
    game_types = result.scalars().all()
    
    game_type_data = []
    for gt in game_types:
        game_type_data.append(GameTypeResponse(
            id=gt.id,
            name=gt.name,
            slug=gt.slug,
            description=gt.description,
            min_ai_opponents=gt.min_ai_opponents,
            max_ai_opponents=gt.max_ai_opponents,
            supports_spectating=gt.supports_spectating
        ))
    
    return BaseResponse(
        message="Game types retrieved successfully",
        data=game_type_data
    )