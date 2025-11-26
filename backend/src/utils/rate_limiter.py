"""Rate limiting utilities.

Implements token bucket algorithm for API rate limiting.
"""
import time
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException, Request, status


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: Optional[int] = None
    ):
        """Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests per minute
            burst_size: Maximum burst size (defaults to requests_per_minute)
        """
        self.rate = requests_per_minute / 60.0  # requests per second
        self.burst_size = burst_size or requests_per_minute
        self.buckets: dict[str, dict] = defaultdict(lambda: {
            "tokens": self.burst_size,
            "last_update": time.time()
        })

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request.
        
        Args:
            request: FastAPI request
            
        Returns:
            Client identifier (IP address or user ID)
        """
        # Try to get user ID from session
        if hasattr(request.state, "player_id"):
            return f"user_{request.state.player_id}"

        # Fall back to IP address
        if request.client:
            return f"ip_{request.client.host}"

        # Default fallback
        return "anonymous"

    def _refill_bucket(self, bucket: dict) -> None:
        """Refill bucket based on elapsed time.
        
        Args:
            bucket: Bucket dictionary with tokens and last_update
        """
        now = time.time()
        elapsed = now - bucket["last_update"]

        # Add tokens based on elapsed time
        bucket["tokens"] = min(
            self.burst_size,
            bucket["tokens"] + elapsed * self.rate
        )
        bucket["last_update"] = now

    def check_limit(self, request: Request) -> bool:
        """Check if request is within rate limit.
        
        Args:
            request: FastAPI request
            
        Returns:
            True if within limit, False otherwise
        """
        client_id = self._get_client_id(request)
        bucket = self.buckets[client_id]

        # Refill bucket
        self._refill_bucket(bucket)

        # Check if tokens available
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True

        return False

    def get_retry_after(self, request: Request) -> int:
        """Get retry-after time in seconds.
        
        Args:
            request: FastAPI request
            
        Returns:
            Seconds until next request allowed
        """
        client_id = self._get_client_id(request)
        bucket = self.buckets[client_id]

        # Calculate time until 1 token available
        tokens_needed = 1 - bucket["tokens"]
        if tokens_needed <= 0:
            return 0

        return int(tokens_needed / self.rate) + 1

    async def __call__(self, request: Request) -> None:
        """FastAPI dependency for rate limiting.
        
        Args:
            request: FastAPI request
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        if not self.check_limit(request):
            retry_after = self.get_retry_after(request)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求过于频繁，请稍后再试",
                headers={"Retry-After": str(retry_after)}
            )


# Global rate limiters for different endpoints
class RateLimiters:
    """Collection of rate limiters for different endpoint categories."""

    # Authentication endpoints (stricter limits)
    auth = RateLimiter(requests_per_minute=5, burst_size=10)

    # Room creation (prevent spam)
    room_creation = RateLimiter(requests_per_minute=10, burst_size=15)

    # General API endpoints
    api = RateLimiter(requests_per_minute=100, burst_size=150)

    # WebSocket messages
    websocket = RateLimiter(requests_per_minute=60, burst_size=100)


def get_rate_limiter(limit_type: str = "api") -> RateLimiter:
    """Get rate limiter by type.
    
    Args:
        limit_type: Type of rate limiter ("auth", "room_creation", "api", "websocket")
        
    Returns:
        RateLimiter instance
    """
    limiters = {
        "auth": RateLimiters.auth,
        "room_creation": RateLimiters.room_creation,
        "api": RateLimiters.api,
        "websocket": RateLimiters.websocket
    }

    return limiters.get(limit_type, RateLimiters.api)
