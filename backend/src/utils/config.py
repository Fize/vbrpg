"""Application configuration and middleware using Pydantic settings."""
from datetime import datetime
from typing import Generic, List, Optional, TypeVar, Dict, TYPE_CHECKING

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.models.session import Session

T = TypeVar("T")


# Response Models
class BaseResponse(BaseModel, Generic[T]):
    """Base response model."""
    success: bool = True
    message: str = "Operation successful"
    data: Optional[T] = None
    timestamp: datetime = datetime.utcnow()


class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = False
    error: str
    code: str
    message: str
    details: Optional[Dict[str, object]] = None
    timestamp: datetime = datetime.utcnow()


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    timestamp: datetime = datetime.utcnow()
    version: str = "1.0.0"


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response model."""
    items: List[T]
    total: int
    page: int = 1
    per_page: int = 20
    total_pages: int
    
    def __init__(self, items: List[T], total: int, page: int = 1, per_page: int = 20):
        total_pages = (total + per_page - 1) // per_page
        super().__init__(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )


class Settings(BaseSettings):
    """Application settings."""

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/vbrpg.db"

    # OpenAI API
    OPENAI_API_KEY: str = ""

    # Security - optional for single-user mode
    SECRET_KEY: str = "dev-secret-key-not-for-production"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


class SessionMiddleware(BaseHTTPMiddleware):
    """Middleware to handle session validation and injection."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request and inject session."""
        # Get session ID from header or query param
        session_id = request.headers.get("X-Session-ID") or request.query_params.get("session_id")
        
        if session_id:
            # Validate session exists and is not expired
            from src.database import get_db
            async for db in get_db():
                session = await self._get_session(db, session_id)
                if session:
                    # Update last active time
                    from datetime import datetime
                    session.last_active = datetime.utcnow()
                    await db.commit()
                    # Add session to request state
                    request.state.session = session
                    request.state.session_id = session_id
                else:
                    # Session not found or expired
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid or expired session"
                    )
                break
        
        response = await call_next(request)
        return response
    
    async def _get_session(self, db: "AsyncSession", session_id: str) -> Optional["Session"]:
        """Get session from database and check if it's valid."""
        from sqlalchemy import select
        from src.models.session import Session
        
        result = await db.execute(select(Session).where(Session.session_id == session_id))
        session = result.scalar_one_or_none()
        
        if not session or session.is_expired():
            return None
        
        return session


class SessionSecurity(HTTPBearer):
    """Security scheme for session-based authentication."""
    
    async def __call__(self, request: Request) -> Optional[str]:
        """Extract session ID from request."""
        session_id = request.headers.get("X-Session-ID") or request.query_params.get("session_id")
        
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session ID required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return session_id


# Global instance for dependency injection
session_security = SessionSecurity()
