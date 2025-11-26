"""Session endpoints for creating and managing short-lived sessions."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.session import Session
from src.utils.config import BaseResponse

router = APIRouter(prefix="/api/v1/sessions", tags=["Session"])


# Response Models
class SessionCreateResponse(BaseModel):
    """Response model for session creation."""
    id: str
    session_id: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class SessionResponse(BaseModel):
    """Response model for session details."""
    id: str
    session_id: str
    created_at: datetime
    last_active: datetime
    expires_at: Optional[datetime] = None
    is_expired: bool


# Session Endpoints
@router.post("", response_model=BaseResponse[SessionCreateResponse], status_code=status.HTTP_201_CREATED)
async def create_session(
    expires_hours: int = 24,
    db: AsyncSession = Depends(get_db)
) -> BaseResponse[SessionCreateResponse]:
    """Create a new session for single-user gaming."""
    import uuid
    session_id = str(uuid.uuid4())

    # Create new session
    new_session = Session.create_new(session_id, expires_hours)
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)

    return BaseResponse(
        message="Session created successfully",
        data=SessionCreateResponse(
            id=new_session.id,
            session_id=new_session.session_id,
            created_at=new_session.created_at,
            expires_at=new_session.expires_at
        )
    )


@router.get("/{session_id}", response_model=BaseResponse[SessionResponse])
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
) -> BaseResponse[SessionResponse]:
    """Get session details."""
    result = await db.execute(
        select(Session).where(Session.session_id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    return BaseResponse(
        message="Session retrieved successfully",
        data=SessionResponse(
            id=session.id,
            session_id=session.session_id,
            created_at=session.created_at,
            last_active=session.last_active,
            expires_at=session.expires_at,
            is_expired=session.is_expired()
        )
    )


@router.post("/{session_id}/extend", response_model=BaseResponse[SessionResponse])
async def extend_session(
    session_id: str,
    hours: int = 24,
    db: AsyncSession = Depends(get_db)
) -> BaseResponse[SessionResponse]:
    """Extend session expiry."""
    result = await db.execute(
        select(Session).where(Session.session_id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if session.is_expired():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot extend expired session"
        )

    # Extend session
    session.extend_expiry(hours)
    await db.commit()
    await db.refresh(session)

    return BaseResponse(
        message="Session extended successfully",
        data=SessionResponse(
            id=session.id,
            session_id=session.session_id,
            created_at=session.created_at,
            last_active=session.last_active,
            expires_at=session.expires_at,
            is_expired=session.is_expired()
        )
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a session."""
    result = await db.execute(
        select(Session).where(Session.session_id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    await db.delete(session)
    await db.commit()
