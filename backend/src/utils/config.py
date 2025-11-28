"""Application configuration using Pydantic settings."""
from datetime import datetime
from typing import Generic, List, Optional, TypeVar, Dict

from pydantic import BaseModel
from pydantic_settings import BaseSettings

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
    DATABASE_URL: str = "mysql+aiomysql://vbrpg:vbrpgpassword@localhost:3306/vbrpg"

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
