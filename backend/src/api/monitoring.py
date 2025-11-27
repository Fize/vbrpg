"""Monitoring and health check endpoints.

Provides system metrics and health status for monitoring.
"""
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.game import GameRoom
from src.models.user import Player

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# Store application start time
START_TIME = time.time()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Basic health check endpoint.
    
    Returns:
        Health status and basic info
    """
    try:
        # Test database connection
        await db.execute(select(1))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "uptime_seconds": int(time.time() - START_TIME),
        "database": db_status
    }


@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Get system metrics in Prometheus format.
    
    Returns:
        System and application metrics
    """
    # Count active games
    active_games_query = select(func.count(GameRoom.id)).where(
        GameRoom.status == "in_progress"
    )
    active_games_result = await db.execute(active_games_query)
    active_games = active_games_result.scalar() or 0

    # Count waiting rooms
    waiting_rooms_query = select(func.count(GameRoom.id)).where(
        GameRoom.status == "waiting"
    )
    waiting_rooms_result = await db.execute(waiting_rooms_query)
    waiting_rooms = waiting_rooms_result.scalar() or 0

    # Count total players
    total_players_query = select(func.count(Player.id))
    total_players_result = await db.execute(total_players_query)
    total_players = total_players_result.scalar() or 0

    # Count guest players
    guest_players_query = select(func.count(Player.id)).where(
        Player.is_guest == True
    )
    guest_players_result = await db.execute(guest_players_query)
    guest_players = guest_players_result.scalar() or 0

    # Count completed games (last 24h would require timestamp filtering)
    completed_games_query = select(func.count(GameRoom.id)).where(
        GameRoom.status == "completed"
    )
    completed_games_result = await db.execute(completed_games_query)
    completed_games = completed_games_result.scalar() or 0

    # Format as Prometheus metrics
    metrics = f"""# HELP active_games Number of active game sessions
# TYPE active_games gauge
active_games {active_games}

# HELP waiting_rooms Number of rooms waiting to start
# TYPE waiting_rooms gauge
waiting_rooms {waiting_rooms}

# HELP total_players Total registered players
# TYPE total_players gauge
total_players {total_players}

# HELP guest_players Number of guest players
# TYPE guest_players gauge
guest_players {guest_players}

# HELP completed_games_total Total completed games
# TYPE completed_games_total counter
completed_games_total {completed_games}

# HELP uptime_seconds Application uptime in seconds
# TYPE uptime_seconds counter
uptime_seconds {int(time.time() - START_TIME)}
"""

    return {
        "metrics": metrics,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/metrics/json")
async def get_metrics_json(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Get system metrics in JSON format.
    
    Returns:
        System and application metrics as JSON
    """
    # Count active games
    active_games_query = select(func.count(GameRoom.id)).where(
        GameRoom.status == "in_progress"
    )
    active_games_result = await db.execute(active_games_query)
    active_games = active_games_result.scalar() or 0

    # Count waiting rooms
    waiting_rooms_query = select(func.count(GameRoom.id)).where(
        GameRoom.status == "waiting"
    )
    waiting_rooms_result = await db.execute(waiting_rooms_query)
    waiting_rooms = waiting_rooms_result.scalar() or 0

    # Count total players
    total_players_query = select(func.count(Player.id))
    total_players_result = await db.execute(total_players_query)
    total_players = total_players_result.scalar() or 0

    # Count guest players
    guest_players_query = select(func.count(Player.id)).where(
        Player.is_guest == True
    )
    guest_players_result = await db.execute(guest_players_query)
    guest_players = guest_players_result.scalar() or 0

    # Count registered players
    registered_players = total_players - guest_players

    # Count completed games
    completed_games_query = select(func.count(GameRoom.id)).where(
        GameRoom.status == "completed"
    )
    completed_games_result = await db.execute(completed_games_query)
    completed_games = completed_games_result.scalar() or 0

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": int(time.time() - START_TIME),
        "games": {
            "active": active_games,
            "waiting": waiting_rooms,
            "completed_total": completed_games
        },
        "players": {
            "total": total_players,
            "registered": registered_players,
            "guests": guest_players
        }
    }


@router.get("/readiness")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Kubernetes readiness probe endpoint.
    
    Returns:
        Readiness status
    """
    try:
        # Check database is responsive
        await db.execute(select(1))

        return {
            "ready": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "ready": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/liveness")
async def liveness_check() -> dict[str, Any]:
    """Kubernetes liveness probe endpoint.
    
    Returns:
        Liveness status
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": int(time.time() - START_TIME)
    }
