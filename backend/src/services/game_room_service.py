"""GameRoom service for managing game rooms."""
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.game_room import GameRoom
from src.models.game_room_participant import GameRoomParticipant
from src.models.game_state import GameState
from src.models.game_type import GameType
from src.models.player import Player
from src.utils.errors import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from src.utils.logging_config import get_logger
from src.utils.room_codes import generate_room_code

logger = get_logger(__name__)


class GameRoomService:
    """Service for game room operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_room(
        self,
        game_type_slug: str,
        max_players: int,
        min_players: int,
        creator_id: str
    ) -> GameRoom:
        """Create a new game room."""
        # Validate game type
        result = await self.db.execute(
            select(GameType).where(GameType.slug == game_type_slug)
        )
        game_type = result.scalar_one_or_none()
        if not game_type:
            raise NotFoundError(f"Game type '{game_type_slug}' not found")

        if not game_type.is_available:
            raise BadRequestError(f"Game '{game_type.name}' is not available yet")

        # Validate player counts
        if min_players < game_type.min_players or min_players > game_type.max_players:
            raise BadRequestError(
                f"min_players must be between {game_type.min_players} and {game_type.max_players}"
            )
        if max_players < game_type.min_players or max_players > game_type.max_players:
            raise BadRequestError(
                f"max_players must be between {game_type.min_players} and {game_type.max_players}"
            )
        if min_players > max_players:
            raise BadRequestError("min_players cannot be greater than max_players")

        # Generate unique room code
        room_code = await self._generate_unique_code()

        # Create room
        room = GameRoom(
            code=room_code,
            game_type_id=game_type.id,
            status="Waiting",
            max_players=max_players,
            min_players=min_players,
            created_by=creator_id
        )
        self.db.add(room)
        await self.db.flush()  # Flush to generate room.id

        # Add creator as participant
        participant = GameRoomParticipant(
            game_room_id=room.id,
            player_id=creator_id,
            is_ai_agent=False
        )
        self.db.add(participant)

        await self.db.commit()

        # Reload room with all relationships
        room = await self.get_room(room.code)

        logger.info(f"Created room {room.code} for game {game_type.name}")
        return room

    async def get_room(self, room_code: str) -> GameRoom:
        """Get room by code with all relationships loaded."""
        result = await self.db.execute(
            select(GameRoom)
            .where(GameRoom.code == room_code)
            .options(
                selectinload(GameRoom.game_type),
                selectinload(GameRoom.participants).selectinload(GameRoomParticipant.player),
                selectinload(GameRoom.game_state)
            )
        )
        room = result.scalar_one_or_none()
        if not room:
            raise NotFoundError(f"Room '{room_code}' not found")
        return room

    async def list_rooms(
        self,
        status: str | None = None,
        game_type_slug: str | None = None,
        limit: int = 20
    ) -> list[GameRoom]:
        """List game rooms with optional filtering."""
        query = select(GameRoom).options(
            selectinload(GameRoom.game_type),
            selectinload(GameRoom.participants)
        )

        if status:
            query = query.where(GameRoom.status == status)
        if game_type_slug:
            query = query.join(GameType).where(GameType.slug == game_type_slug)

        query = query.order_by(GameRoom.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def join_room(self, room_code: str, player_id: str) -> GameRoom:
        """Add player to game room."""
        room = await self.get_room(room_code)

        # Validate can join
        if not room.can_join():
            raise BadRequestError(f"Room is {room.status}, cannot join")

        # Check if already in room
        for participant in room.participants:
            if participant.player_id == player_id and participant.is_active():
                raise ConflictError("Already in this room")

        # Check if room is full
        active_count = room.get_active_participants_count()
        if active_count >= room.max_players:
            raise BadRequestError("Room is full")

        # Add participant
        participant = GameRoomParticipant(
            game_room_id=room.id,
            player_id=player_id,
            is_ai_agent=False
        )
        self.db.add(participant)
        await self.db.commit()

        # Reload room with updated participants
        room = await self.get_room(room.code)

        logger.info(f"Player {player_id} joined room {room.code}")
        return room

    async def leave_room(self, room_code: str, player_id: str) -> None:
        """Remove player from game room."""
        room = await self.get_room(room_code)

        # Find participant
        participant = None
        for p in room.participants:
            if p.player_id == player_id and p.is_active():
                participant = p
                break

        if not participant:
            raise NotFoundError("Not in this room")

        participant.leave()
        await self.db.commit()

        logger.info(f"Player {player_id} left room {room.code}")

    async def start_game(self, room_code: str, player_id: str) -> GameRoom:
        """Start the game (creator only)."""
        room = await self.get_room(room_code)

        # Validate creator
        if room.created_by != player_id:
            raise ForbiddenError("Only room creator can start the game")

        # Validate status
        if room.status != "Waiting":
            raise BadRequestError(f"Room is already {room.status}")

        # Check if we need AI agents to fill empty slots
        active_count = room.get_active_participants_count()
        if active_count < room.min_players:
            logger.info(
                f"Room {room.code} has {active_count}/{room.min_players} players, "
                f"filling with AI agents"
            )
            from src.services.ai_agent_service import AIAgentService
            ai_service = AIAgentService(self.db)
            ai_participants = await ai_service.fill_empty_slots(room)
            
            if ai_participants:
                # Refresh room relationships to include new AI participants
                await self.db.refresh(room, ['participants'])
                logger.info(f"Added {len(ai_participants)} AI agents to room {room.code}")
        
        # Validate ready to start (should be true now after AI fill)
        if not room.is_ready_to_start():
            active_count = room.get_active_participants_count()
            raise BadRequestError(
                f"Need at least {room.min_players} players to start (currently have {active_count})"
            )

        # Start game
        room.start()
        
        # Create initial game state
        initial_game_data = {
            "phase": "setup",
            "round": 1,
            "participants": [
                {
                    "id": p.id,
                    "player_id": p.player_id,
                    "is_ai": p.is_ai_agent,
                    "personality": p.ai_personality,
                    "status": "active"
                }
                for p in room.participants if p.is_active()
            ],
            "game_type": room.game_type.slug,
            "started_at": datetime.utcnow().isoformat()
        }
        
        game_state = GameState(
            game_room_id=room.id,
            current_phase="setup",
            current_turn_player_id=None,  # Will be set when game actually starts
            turn_number=1,
            game_data=json.dumps(initial_game_data)
        )
        self.db.add(game_state)
        
        await self.db.commit()

        # Reload room with all relationships including new game_state
        room = await self.get_room(room.code)

        logger.info(
            f"Game started in room {room.code} with {room.get_active_participants_count()} players "
            f"(phase: {game_state.current_phase})"
        )
        return room

    async def replace_player_with_ai(self, room_code: str, player_id: str) -> GameRoom:
        """
        Replace a disconnected player with an AI agent.
        
        Args:
            room_code: The room code
            player_id: The player to replace
            
        Returns:
            Updated GameRoom
            
        Raises:
            NotFoundError: If room or participant not found
            BadRequestError: If game is not in progress
        """
        # Get room
        room = await self.get_room(room_code)
        
        if room.status != "In Progress":
            raise BadRequestError("Can only replace players in games that are in progress")
        
        # Find participant
        result = await self.db.execute(
            select(GameRoomParticipant).where(
                GameRoomParticipant.game_room_id == room.id,
                GameRoomParticipant.player_id == player_id,
                GameRoomParticipant.left_at.is_(None)
            )
        )
        participant = result.scalar_one_or_none()
        
        if not participant:
            raise NotFoundError(f"Player {player_id} not found in room {room_code}")
        
        if participant.is_ai_agent:
            raise BadRequestError("Participant is already an AI agent")
        
        # Mark player as left
        participant.left_at = datetime.utcnow()
        
        # Create AI replacement
        ai_personalities = ["福尔摩斯", "柯南", "波洛", "马普尔"]
        
        # Find which AI personalities are already in use
        existing_ai_result = await self.db.execute(
            select(GameRoomParticipant.ai_personality).where(
                GameRoomParticipant.game_room_id == room.id,
                GameRoomParticipant.is_ai_agent.is_(True),
                GameRoomParticipant.left_at.is_(None)
            )
        )
        used_personalities = {row[0] for row in existing_ai_result.all()}
        
        # Pick unused personality
        available_personalities = [p for p in ai_personalities if p not in used_personalities]
        ai_personality = available_personalities[0] if available_personalities else f"AI探员{len(used_personalities) + 1}"
        
        # Create AI participant
        ai_participant = GameRoomParticipant(
            game_room_id=room.id,
            player_id=None,
            is_ai_agent=True,
            ai_personality=ai_personality,
            joined_at=datetime.utcnow()
        )
        self.db.add(ai_participant)
        
        logger.info(
            f"Replaced player {player_id} with AI agent '{ai_personality}' "
            f"in room {room_code}"
        )
        
        await self.db.commit()
        await self.db.refresh(room)
        return room

    async def _generate_unique_code(self) -> str:
        """Generate a unique room code."""
        max_attempts = 10
        for _ in range(max_attempts):
            code = generate_room_code()
            result = await self.db.execute(
                select(GameRoom).where(GameRoom.code == code)
            )
            if result.scalar_one_or_none() is None:
                return code
        raise ConflictError("Failed to generate unique room code")
