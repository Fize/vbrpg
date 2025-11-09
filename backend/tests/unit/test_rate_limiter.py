"""Tests for rate limiter utility.

Tests the token bucket rate limiting implementation.
"""
import time
from unittest.mock import Mock

import pytest
from fastapi import HTTPException, Request

from src.utils.rate_limiter import RateLimiter, RateLimiters, get_rate_limiter


class TestRateLimiter:
    """Test RateLimiter class."""
    
    def test_init_default_burst_size(self):
        """Test initialization with default burst size."""
        limiter = RateLimiter(requests_per_minute=60)
        assert limiter.rate == 1.0  # 60/60 = 1 per second
        assert limiter.burst_size == 60
    
    def test_init_custom_burst_size(self):
        """Test initialization with custom burst size."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=100)
        assert limiter.rate == 1.0
        assert limiter.burst_size == 100
    
    def test_get_client_id_from_user(self):
        """Test client ID extraction from user session."""
        limiter = RateLimiter()
        request = Mock(spec=Request)
        request.state.player_id = "test-player-123"
        request.client = Mock(host="192.168.1.1")
        
        client_id = limiter._get_client_id(request)
        assert client_id == "user_test-player-123"
    
    def test_get_client_id_from_ip(self):
        """Test client ID extraction from IP address."""
        limiter = RateLimiter()
        request = Mock(spec=Request)
        request.state = Mock(spec=[])  # No player_id
        request.client = Mock(host="192.168.1.1")
        
        client_id = limiter._get_client_id(request)
        assert client_id == "ip_192.168.1.1"
    
    def test_get_client_id_anonymous(self):
        """Test client ID fallback to anonymous."""
        limiter = RateLimiter()
        request = Mock(spec=Request)
        request.state = Mock(spec=[])
        request.client = None
        
        client_id = limiter._get_client_id(request)
        assert client_id == "anonymous"
    
    def test_check_limit_allows_requests(self):
        """Test that requests within limit are allowed."""
        limiter = RateLimiter(requests_per_minute=60)
        request = Mock(spec=Request)
        request.state = Mock(spec=[])
        request.client = Mock(host="192.168.1.1")
        
        # First request should be allowed
        assert limiter.check_limit(request) is True
        
        # Second request should also be allowed (burst)
        assert limiter.check_limit(request) is True
    
    def test_check_limit_blocks_excessive_requests(self):
        """Test that excessive requests are blocked."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=2)
        request = Mock(spec=Request)
        request.state = Mock(spec=[])
        request.client = Mock(host="192.168.1.1")
        
        # Use up burst
        assert limiter.check_limit(request) is True
        assert limiter.check_limit(request) is True
        
        # Next request should be blocked
        assert limiter.check_limit(request) is False
    
    def test_bucket_refills_over_time(self):
        """Test that bucket refills based on elapsed time."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=1)
        request = Mock(spec=Request)
        request.state = Mock(spec=[])
        request.client = Mock(host="192.168.1.1")
        
        # Use up token
        assert limiter.check_limit(request) is True
        assert limiter.check_limit(request) is False
        
        # Wait for refill (1 token per second)
        time.sleep(1.1)
        
        # Should be allowed now
        assert limiter.check_limit(request) is True
    
    def test_get_retry_after(self):
        """Test retry-after calculation."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=1)
        request = Mock(spec=Request)
        request.state = Mock(spec=[])
        request.client = Mock(host="192.168.1.1")
        
        # Use up token
        limiter.check_limit(request)
        
        # Get retry after
        retry_after = limiter.get_retry_after(request)
        assert retry_after > 0
        assert retry_after <= 2  # Should be ~1 second
    
    def test_get_retry_after_when_tokens_available(self):
        """Test retry-after returns 0 when tokens available."""
        limiter = RateLimiter(requests_per_minute=60)
        request = Mock(spec=Request)
        request.state = Mock(spec=[])
        request.client = Mock(host="192.168.1.1")
        
        retry_after = limiter.get_retry_after(request)
        assert retry_after == 0
    
    @pytest.mark.asyncio
    async def test_call_allows_request(self):
        """Test rate limiter as FastAPI dependency allows requests."""
        limiter = RateLimiter(requests_per_minute=60)
        request = Mock(spec=Request)
        request.state = Mock(spec=[])
        request.client = Mock(host="192.168.1.1")
        
        # Should not raise exception
        await limiter(request)
    
    @pytest.mark.asyncio
    async def test_call_blocks_excessive_requests(self):
        """Test rate limiter as FastAPI dependency blocks excessive requests."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=1)
        request = Mock(spec=Request)
        request.state = Mock(spec=[])
        request.client = Mock(host="192.168.1.1")
        
        # First request OK
        await limiter(request)
        
        # Second request should raise 429
        with pytest.raises(HTTPException) as exc_info:
            await limiter(request)
        
        assert exc_info.value.status_code == 429
        assert "Retry-After" in exc_info.value.headers
    
    def test_different_clients_separate_buckets(self):
        """Test that different clients have separate rate limit buckets."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=1)
        
        request1 = Mock(spec=Request)
        request1.state = Mock(spec=[])
        request1.client = Mock(host="192.168.1.1")
        
        request2 = Mock(spec=Request)
        request2.state = Mock(spec=[])
        request2.client = Mock(host="192.168.1.2")
        
        # Use up request1's tokens
        assert limiter.check_limit(request1) is True
        assert limiter.check_limit(request1) is False
        
        # request2 should still have tokens
        assert limiter.check_limit(request2) is True


class TestRateLimiters:
    """Test RateLimiters singleton collection."""
    
    def test_auth_limiter_exists(self):
        """Test auth rate limiter exists."""
        assert isinstance(RateLimiters.auth, RateLimiter)
    
    def test_room_creation_limiter_exists(self):
        """Test room creation rate limiter exists."""
        assert isinstance(RateLimiters.room_creation, RateLimiter)
    
    def test_api_limiter_exists(self):
        """Test API rate limiter exists."""
        assert isinstance(RateLimiters.api, RateLimiter)
    
    def test_websocket_limiter_exists(self):
        """Test WebSocket rate limiter exists."""
        assert isinstance(RateLimiters.websocket, RateLimiter)
    
    def test_auth_limiter_stricter(self):
        """Test auth limiter is stricter than API limiter."""
        # Auth should have lower rate
        assert RateLimiters.auth.rate < RateLimiters.api.rate


class TestGetRateLimiter:
    """Test get_rate_limiter helper function."""
    
    def test_get_auth_limiter(self):
        """Test getting auth rate limiter."""
        limiter = get_rate_limiter("auth")
        assert limiter is RateLimiters.auth
    
    def test_get_room_creation_limiter(self):
        """Test getting room creation rate limiter."""
        limiter = get_rate_limiter("room_creation")
        assert limiter is RateLimiters.room_creation
    
    def test_get_api_limiter(self):
        """Test getting API rate limiter."""
        limiter = get_rate_limiter("api")
        assert limiter is RateLimiters.api
    
    def test_get_websocket_limiter(self):
        """Test getting WebSocket rate limiter."""
        limiter = get_rate_limiter("websocket")
        assert limiter is RateLimiters.websocket
    
    def test_get_default_limiter(self):
        """Test getting default limiter for unknown type."""
        limiter = get_rate_limiter("unknown")
        assert limiter is RateLimiters.api
    
    def test_get_limiter_without_type(self):
        """Test getting limiter with default parameter."""
        limiter = get_rate_limiter()
        assert limiter is RateLimiters.api
