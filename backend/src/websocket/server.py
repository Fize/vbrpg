"""Socket.IO server configuration."""
import socketio

from src.utils.config import settings

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=settings.CORS_ORIGINS.split(","),
    logger=settings.ENVIRONMENT == "development",
    engineio_logger=settings.ENVIRONMENT == "development"
)


# Import Socket.IO event handlers to register them
# This must be done after sio is created but before the app uses it
from src.websocket import handlers  # noqa: F401, E402

