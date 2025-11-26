"""Games API endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import GameTypeResponse
from src.database import get_db
from src.models.game_type import GameType

router = APIRouter(prefix="/api/v1/games", tags=["games"])


@router.get("", response_model=List[GameTypeResponse])
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


@router.get("/{slug}", response_model=GameTypeResponse)
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
