"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio

from src.database import init_db
from src.utils.config import settings
from src.utils.logging_config import setup_logging
from src.websocket.server import sio

# Import all models to ensure relationships are properly configured
import src.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    setup_logging()
    await init_db()
    yield
    # Shutdown
    pass


# Create FastAPI app
app = FastAPI(
    title="AI-Powered Tabletop Game Platform",
    description="Backend API for multiplayer tabletop games with AI agents",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
origins = settings.CORS_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from datetime import datetime
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI-Powered Tabletop Game Platform API",
        "version": "0.1.0",
        "docs": "/docs"
    }


# Import and include routers
from src.api import rooms, games, players, monitoring

app.include_router(rooms.router)
app.include_router(games.router)
app.include_router(players.router)
app.include_router(monitoring.router)

# Mount Socket.IO app
socket_app = socketio.ASGIApp(sio, app)

