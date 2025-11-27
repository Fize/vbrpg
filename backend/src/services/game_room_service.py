"""GameRoom service for single-user gaming."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ai_agent import AIAgent
from src.models.game_room import GameRoom
from src.models.game_room_participant import GameRoomParticipant
from src.models.game_state import GameState
from src.models.game_type import GameType
from src.utils.errors import GameAlreadyStartedError, RoomFullError, RoomNotFoundError
from src.utils.room_codes import generate_room_code


class GameRoomService:
    """Service for managing game rooms in single-user environment."""

    @staticmethod
    async def create_room(
        db: AsyncSession,
        game_type_slug: str,
        max_players: int = 4,
        min_players: int = 2,
        session_id: Optional[str] = None
    ) -> GameRoom:
        """Create a new game room.
        
        Args:
            db: Database session
            game_type_slug: Game type identifier
            max_players: Maximum number of players
            min_players: Minimum number of players to start
            session_id: Optional session ID for auto-join
            
        Returns:
            Created game room
        """
        # Get game type
        result = await db.execute(
            select(GameType).where(GameType.slug == game_type_slug)
        )
        game_type = result.scalar_one_or_none()

        if not game_type:
            raise ValueError(f"Game type '{game_type_slug}' not found")

        # Create room
        room = GameRoom(
            code=generate_room_code(),
            game_type_id=game_type.id,
            status="Waiting",
            max_players=max_players,
            min_players=min_players
        )
        db.add(room)
        await db.commit()
        await db.refresh(room)

        # Auto-join session if provided
        if session_id:
            await GameRoomService.join_room(db, room.code, session_id)

        return room

    @staticmethod
    async def get_room_by_code(db: AsyncSession, room_code: str) -> Optional[GameRoom]:
        """Get room by code."""
        result = await db.execute(
            select(GameRoom).where(GameRoom.code == room_code)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def join_room(db: AsyncSession, room_code: str, session_id: str) -> GameRoomParticipant:
        """Join a room with a session.
        
        Args:
            db: Database session
            room_code: Room code
            session_id: Session ID
            
        Returns:
            Created participant
        """
        # Get room
        room = await GameRoomService.get_room_by_code(db, room_code)
        if not room:
            raise RoomNotFoundError()

        # Check if can join
        if not room.can_join():
            raise GameAlreadyStartedError()

        if room.get_active_participants_count() >= room.max_players:
            raise RoomFullError()

        # Check if session already in room
        existing = await db.execute(
            select(GameRoomParticipant).where(
                GameRoomParticipant.game_room_id == room.id,
                GameRoomParticipant.session_id == session_id,
                GameRoomParticipant.left_at.is_(None)
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Session already in room")

        # Create participant
        participant = GameRoomParticipant(
            game_room_id=room.id,
            session_id=session_id,
            is_ai_agent=False
        )
        db.add(participant)
        await db.commit()
        await db.refresh(participant)

        return participant

    @staticmethod
    async def leave_room(db: AsyncSession, room_code: str, session_id: str):
        """Leave a room.
        
        Args:
            db: Database session
            room_code: Room code
            session_id: Session ID
        """
        # Get room
        room = await GameRoomService.get_room_by_code(db, room_code)
        if not room:
            raise RoomNotFoundError()

        # Get participant
        result = await db.execute(
            select(GameRoomParticipant).where(
                GameRoomParticipant.game_room_id == room.id,
                GameRoomParticipant.session_id == session_id,
                GameRoomParticipant.left_at.is_(None)
            )
        )
        participant = result.scalar_one_or_none()

        if not participant:
            raise ValueError("Session not in room")

        # Leave room
        participant.leave()
        await db.commit()

    @staticmethod
    async def add_ai_agent(
        db: AsyncSession,
        room_code: str,
        personality_type: str,
        difficulty_level: int
    ) -> (GameRoomParticipant, AIAgent):
        """Add AI agent to room.
        
        Args:
            db: Database session
            room_code: Room code
            personality_type: AI personality type
            difficulty_level: AI difficulty level (1-5)
            
        Returns:
            Created participant and AI agent
        """
        # Get room
        room = await GameRoomService.get_room_by_code(db, room_code)
        if not room:
            raise RoomNotFoundError()

        if not room.can_join():
            raise GameAlreadyStartedError()

        # Check AI limits based on game type
        current_ai_count = await db.execute(
            select(GameRoomParticipant).where(
                GameRoomParticipant.game_room_id == room.id,
                GameRoomParticipant.is_ai_agent == True,
                GameRoomParticipant.left_at.is_(None)
            )
        )
        ai_count = len(current_ai_count.scalars().all())

        if ai_count >= room.game_type.max_ai_opponents:
            raise ValueError("Maximum AI agents reached for this game type")

        # Create AI agent
        ai_name = room.increment_ai_counter()
        ai_agent = AIAgent(
            username=ai_name,
            personality_type=personality_type,
            difficulty_level=difficulty_level
        )
        db.add(ai_agent)
        await db.flush()  # Get ID without committing

        # Create participant
        participant = GameRoomParticipant(
            game_room_id=room.id,
            is_ai_agent=True,
            ai_personality=personality_type
        )
        db.add(participant)
        await db.commit()

        return participant, ai_agent

    @staticmethod
    async def remove_ai_agent(db: AsyncSession, room_code: str, ai_agent_id: str):
        """Remove AI agent from room.
        
        Args:
            db: Database session
            room_code: Room code
            ai_agent_id: AI agent ID
        """
        # Get room
        room = await GameRoomService.get_room_by_code(db, room_code)
        if not room:
            raise RoomNotFoundError()

        # Get AI participant
        result = await db.execute(
            select(GameRoomParticipant).where(
                GameRoomParticipant.game_room_id == room.id,
                GameRoomParticipant.is_ai_agent == True,
                GameRoomParticipant.id == ai_agent_id,
                GameRoomParticipant.left_at.is_(None)
            )
        )
        participant = result.scalar_one_or_none()

        if not participant:
            raise ValueError("AI agent not in room")

        # Remove participant
        participant.leave()
        await db.commit()

    @staticmethod
    async def start_game(db: AsyncSession, room_code: str) -> GameRoom:
        """Start a game.
        
        Args:
            db: Database session
            room_code: Room code
            
        Returns:
            Updated room
        """
        # Get room
        room = await GameRoomService.get_room_by_code(db, room_code)
        if not room:
            raise RoomNotFoundError()

        if not room.can_join():
            raise GameAlreadyStartedError()

        if not room.is_ready_to_start():
            raise ValueError("Not enough participants to start")

        # Start game
        room.start()

        # Create game state
        game_state = GameState(
            game_room_id=room.id,
            current_turn="",  # Will be set by game logic
            game_data="{}"  # Initial game state
        )
        db.add(game_state)

        await db.commit()
        await db.refresh(room)

        return room

    @staticmethod
    async def delete_room(db: AsyncSession, room_code: str, session_id: str):
        """Delete a room (only for Waiting status).
        
        Args:
            db: Database session
            room_code: Room code
            session_id: Session ID of room creator
        """
        # Get room
        room = await GameRoomService.get_room_by_code(db, room_code)
        if not room:
            raise RoomNotFoundError()

        if room.status != "Waiting":
            raise ValueError("Can only delete rooms in Waiting status")

        # For single-user, allow any session to delete waiting rooms
        await db.delete(room)
        await db.commit()
