"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio

from src.database import init_db
from src.utils.config import settings, HealthResponse
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
    title="Single-User Tabletop Game Platform",
    description="Backend API for single-user tabletop games with AI agents",
    version="1.0.0",
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


@app.get("/api/v1/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.get("/", tags=["System"])
async def root():
    """Root endpoint."""
    return {
        "message": "Single-User Tabletop Game Platform API",
        "version": "1.0.0",
        "docs": "/docs"
    }


# Import and include merged API routers
from src.api import game_routes, user_routes, monitoring

# Include merged routers
app.include_router(game_routes.router)
app.include_router(user_routes.router)
app.include_router(monitoring.router)

# Mount Socket.IO app
socket_app = socketio.ASGIApp(sio, app)

