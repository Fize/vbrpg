"""Application configuration using Pydantic settings."""
from datetime import datetime
from typing import Generic, List, Optional, TypeVar, Dict

from pydantic import BaseModel
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

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

    # OpenAI API (deprecated, use AI_* settings instead)
    OPENAI_API_KEY: str = ""

    # AI Configuration
    AI_API_BASE_URL: str = ""  # Custom API base URL (e.g., for local LLM or proxy)
    AI_API_KEY: str = ""  # AI API Key (fallback to OPENAI_API_KEY if not set)
    AI_MODEL: str = "gpt-4o-mini"  # Model name to use
    AI_TEMPERATURE: float = 0.7  # Temperature for generation
    AI_TIMEOUT: int = 60  # Request timeout in seconds
    AI_MAX_RETRIES: int = 3  # Maximum retry attempts
    AI_LOG_FILE: str = "logs/ai_calls.log"  # AI call log file path
    AI_LOG_LEVEL: str = "INFO"  # AI call log level

    # Security - optional for single-user mode
    SECRET_KEY: str = "dev-secret-key-not-for-production"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def effective_ai_api_key(self) -> str:
        """Get the effective AI API key (AI_API_KEY or fallback to OPENAI_API_KEY)."""
        return self.AI_API_KEY or self.OPENAI_API_KEY

    # Pydantic v2: use model_config (ConfigDict) instead of class-based `Config`
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
    )


settings = Settings()
