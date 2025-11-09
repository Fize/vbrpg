"""API routers initialization."""
from fastapi import APIRouter

# Base router for API v1
api_router = APIRouter()

# Routers will be imported and included here
# from src.api import players, games, rooms
# api_router.include_router(players.router, prefix="/players", tags=["players"])
# api_router.include_router(games.router, prefix="/games", tags=["games"])
# api_router.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
