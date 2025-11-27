"""Session management utilities."""

import secrets
from typing import Optional

from fastapi import Cookie, Response


class SessionManager:
    """Manage user sessions with cookies."""

    SESSION_COOKIE_NAME = "vbrpg_session"
    SESSION_DURATION_DAYS = 30

    @staticmethod
    def generate_session_id() -> str:
        """Generate a secure random session ID.
        
        Returns:
            A 32-character hexadecimal session ID
        """
        return secrets.token_hex(16)

    @staticmethod
    def create_session(response: Response, player_id: str) -> str:
        """Create a new session and set the cookie.
        
        Args:
            response: FastAPI response object
            player_id: Player ID to associate with session
            
        Returns:
            The generated session ID
        """
        session_id = SessionManager.generate_session_id()

        response.set_cookie(
            key=SessionManager.SESSION_COOKIE_NAME,
            value=f"{session_id}:{player_id}",
            max_age=SessionManager.SESSION_DURATION_DAYS * 24 * 60 * 60,
            httponly=True,
            samesite="lax",
            secure=False  # Set to True in production with HTTPS
        )

        return session_id

    @staticmethod
    def get_player_from_session(
        session_cookie: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME)
    ) -> Optional[str]:
        """Extract player ID from session cookie.
        
        Args:
            session_cookie: The session cookie value
            
        Returns:
            Player ID if valid session, None otherwise
        """
        if not session_cookie:
            return None

        try:
            # Session format: "session_id:player_id"
            parts = session_cookie.split(":", 1)
            if len(parts) == 2:
                return parts[1]
        except Exception:
            pass

        return None

    @staticmethod
    def clear_session(response: Response):
        """Clear the session cookie.
        
        Args:
            response: FastAPI response object
        """
        response.delete_cookie(
            key=SessionManager.SESSION_COOKIE_NAME,
            httponly=True,
            samesite="lax"
        )
