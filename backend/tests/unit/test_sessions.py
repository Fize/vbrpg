"""Tests for session management utilities."""

import pytest
from fastapi import Response
from fastapi.testclient import TestClient

from src.utils.sessions import SessionManager


class TestSessionManager:
    """Test SessionManager methods."""

    def test_generate_session_id(self):
        """Test session ID generation."""
        session_id = SessionManager.generate_session_id()
        
        # Should be 32 characters (16 bytes in hex)
        assert len(session_id) == 32
        
        # Should be hexadecimal
        assert all(c in "0123456789abcdef" for c in session_id)
        
        # Should be unique
        session_id2 = SessionManager.generate_session_id()
        assert session_id != session_id2

    def test_generate_multiple_unique_ids(self):
        """Test generating multiple unique session IDs."""
        ids = [SessionManager.generate_session_id() for _ in range(100)]
        
        # All should be unique
        assert len(set(ids)) == 100

    def test_create_session(self):
        """Test creating a session with cookie."""
        response = Response()
        player_id = "test_player_123"
        
        session_id = SessionManager.create_session(response, player_id)
        
        # Session ID should be returned
        assert session_id is not None
        assert len(session_id) == 32
        
        # Cookie should be set
        cookie_value = None
        for cookie in response.raw_headers:
            if cookie[0] == b'set-cookie':
                cookie_str = cookie[1].decode()
                if SessionManager.SESSION_COOKIE_NAME in cookie_str:
                    cookie_value = cookie_str
                    break
        
        assert cookie_value is not None
        assert f"{session_id}:{player_id}" in cookie_value
        assert "HttpOnly" in cookie_value
        assert "SameSite=lax" in cookie_value

    def test_create_session_cookie_attributes(self):
        """Test session cookie has correct attributes."""
        response = Response()
        player_id = "test_player_456"
        
        SessionManager.create_session(response, player_id)
        
        # Check cookie attributes
        cookie_str = None
        for cookie in response.raw_headers:
            if cookie[0] == b'set-cookie':
                cookie_str = cookie[1].decode()
                if SessionManager.SESSION_COOKIE_NAME in cookie_str:
                    break
        
        assert cookie_str is not None
        
        # Should have max-age
        assert "Max-Age=" in cookie_str
        
        # Should be HttpOnly
        assert "HttpOnly" in cookie_str
        
        # Should have SameSite
        assert "SameSite=lax" in cookie_str

    def test_get_player_from_session_valid(self):
        """Test extracting player ID from valid session cookie."""
        session_id = "abc123def456"
        player_id = "player_789"
        cookie_value = f"{session_id}:{player_id}"
        
        result = SessionManager.get_player_from_session(cookie_value)
        
        assert result == player_id

    def test_get_player_from_session_none(self):
        """Test handling None session cookie."""
        result = SessionManager.get_player_from_session(None)
        
        assert result is None

    def test_get_player_from_session_empty(self):
        """Test handling empty session cookie."""
        result = SessionManager.get_player_from_session("")
        
        assert result is None

    def test_get_player_from_session_invalid_format(self):
        """Test handling invalid session cookie format."""
        result = SessionManager.get_player_from_session("invalid")
        
        assert result is None

    def test_get_player_from_session_missing_player_id(self):
        """Test handling session cookie without player ID."""
        result = SessionManager.get_player_from_session("abc123def456:")
        
        # Should return empty string (no player ID after colon)
        assert result == ""

    def test_clear_session(self):
        """Test clearing a session."""
        response = Response()
        
        SessionManager.clear_session(response)
        
        # Should set cookie with max_age=0 to delete it
        cookie_str = None
        for cookie in response.raw_headers:
            if cookie[0] == b'set-cookie':
                cookie_str = cookie[1].decode()
                if SessionManager.SESSION_COOKIE_NAME in cookie_str:
                    break
        
        assert cookie_str is not None
        assert "Max-Age=0" in cookie_str

    def test_session_duration(self):
        """Test session duration constant."""
        assert SessionManager.SESSION_DURATION_DAYS == 30

    def test_session_cookie_name(self):
        """Test session cookie name constant."""
        assert SessionManager.SESSION_COOKIE_NAME == "vbrpg_session"

    def test_create_session_with_special_characters_in_player_id(self):
        """Test creating session with special characters in player ID."""
        response = Response()
        player_id = "player_with_underscore_123"
        
        session_id = SessionManager.create_session(response, player_id)
        
        # Should work with underscores
        assert session_id is not None
        
        # Retrieve should work
        cookie_value = f"{session_id}:{player_id}"
        result = SessionManager.get_player_from_session(cookie_value)
        assert result == player_id

    def test_session_id_randomness(self):
        """Test that session IDs are sufficiently random."""
        ids = [SessionManager.generate_session_id() for _ in range(1000)]
        
        # All should be unique
        assert len(set(ids)) == 1000
        
        # Should have good distribution (no repeated patterns)
        # Check first 8 characters
        prefixes = [id[:8] for id in ids]
        assert len(set(prefixes)) > 990  # At least 99% unique prefixes

    def test_session_cookie_max_age_calculation(self):
        """Test that max-age is calculated correctly."""
        response = Response()
        player_id = "test_player"
        
        SessionManager.create_session(response, player_id)
        
        # Extract max-age from cookie
        cookie_str = None
        for cookie in response.raw_headers:
            if cookie[0] == b'set-cookie':
                cookie_str = cookie[1].decode()
                if SessionManager.SESSION_COOKIE_NAME in cookie_str:
                    break
        
        # Expected: 30 days * 24 hours * 60 minutes * 60 seconds
        expected_max_age = SessionManager.SESSION_DURATION_DAYS * 24 * 60 * 60
        assert f"Max-Age={expected_max_age}" in cookie_str


class TestSessionIntegration:
    """Integration tests for session management."""

    def test_full_session_lifecycle(self):
        """Test complete session lifecycle: create, read, clear."""
        # Create session
        response_create = Response()
        player_id = "lifecycle_test_player"
        
        session_id = SessionManager.create_session(response_create, player_id)
        assert session_id is not None
        
        # Simulate reading session cookie
        cookie_value = f"{session_id}:{player_id}"
        retrieved_player_id = SessionManager.get_player_from_session(cookie_value)
        assert retrieved_player_id == player_id
        
        # Clear session
        response_clear = Response()
        SessionManager.clear_session(response_clear)
        
        # Verify clear cookie was set
        cookie_str = None
        for cookie in response_clear.raw_headers:
            if cookie[0] == b'set-cookie':
                cookie_str = cookie[1].decode()
                if SessionManager.SESSION_COOKIE_NAME in cookie_str:
                    break
        
        assert "Max-Age=0" in cookie_str

    def test_session_with_multiple_players(self):
        """Test creating sessions for multiple players."""
        players = [f"player_{i}" for i in range(10)]
        sessions = {}
        
        for player_id in players:
            response = Response()
            session_id = SessionManager.create_session(response, player_id)
            sessions[player_id] = session_id
        
        # All sessions should be unique
        assert len(set(sessions.values())) == 10
        
        # Each player should be retrievable
        for player_id, session_id in sessions.items():
            cookie_value = f"{session_id}:{player_id}"
            retrieved = SessionManager.get_player_from_session(cookie_value)
            assert retrieved == player_id
