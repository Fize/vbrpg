"""GameRoom service for single-player gaming.

单人模式：所有玩家都是 AI 代理，用户可以选择观战或参与。
"""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.game import GameRoom, GameRoomParticipant, GameState, GameType
from src.models.user import AIAgent, Player
from src.utils.errors import (
    BadRequestError,
    GameAlreadyStartedError,
    NotFoundError,
    RoomFullError,
)
from src.utils.helpers import generate_room_code


class GameRoomService:
    """Service for managing game rooms in single-player environment.
    
    单人模式下：
    - 无需用户认证
    - 所有玩家都是 AI 代理
    - 用户可以选择观战或参与
    """

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.
        
        Args:
            db: Database session
        """
        self.db = db

    async def create_room(
        self,
        game_type_slug: str,
        max_players: int = 4,
        min_players: int = 2,
        user_role: str = "spectator",
        is_spectator_mode: bool = True
    ) -> GameRoom:
        """Create a new game room for single-player mode.
        
        Args:
            game_type_slug: Game type identifier
            max_players: Maximum number of players (all AI)
            min_players: Minimum number of players to start
            user_role: User's role ('spectator' or 'participant')
            is_spectator_mode: Whether user is in spectator mode
            
        Returns:
            Created game room
        """
        # Get game type
        result = await self.db.execute(
            select(GameType).where(GameType.slug == game_type_slug)
        )
        game_type = result.scalar_one_or_none()

        if not game_type:
            raise NotFoundError(f"Game type '{game_type_slug}' not found")

        # Validate player counts
        if min_players < game_type.min_players:
            raise BadRequestError(
                f"Minimum players cannot be less than {game_type.min_players}"
            )
        if max_players > game_type.max_players:
            raise BadRequestError(
                f"Maximum players cannot exceed {game_type.max_players}"
            )
        if min_players > max_players:
            raise BadRequestError(
                "Minimum players cannot exceed maximum players"
            )

        # Create room (no owner in single-player mode)
        room = GameRoom(
            code=generate_room_code(),
            game_type_id=game_type.id,
            status="Waiting",
            max_players=max_players,
            min_players=min_players,
            user_role=user_role,
            is_spectator_mode=is_spectator_mode
        )
        self.db.add(room)
        await self.db.commit()
        await self.db.refresh(room)

        # Load relationships
        await self.db.refresh(room, ["game_type", "participants"])

        return room

    async def get_room(self, room_code: str) -> GameRoom:
        """Get room by code with all relationships loaded.
        
        Args:
            room_code: Room code
            
        Returns:
            Game room
            
        Raises:
            NotFoundError: If room not found
        """
        result = await self.db.execute(
            select(GameRoom)
            .options(
                selectinload(GameRoom.game_type),
                selectinload(GameRoom.participants).selectinload(
                    GameRoomParticipant.player
                )
            )
            .where(GameRoom.code == room_code)
        )
        room = result.scalar_one_or_none()

        if not room:
            raise NotFoundError(f"Room '{room_code}' not found")

        return room

    async def list_rooms(
        self,
        status: Optional[str] = None,
        game_type_slug: Optional[str] = None,
        limit: int = 20
    ) -> List[GameRoom]:
        """List game rooms with optional filtering.
        
        Args:
            status: Filter by room status
            game_type_slug: Filter by game type
            limit: Maximum number of rooms to return
            
        Returns:
            List of game rooms
        """
        query = select(GameRoom).options(
            selectinload(GameRoom.game_type),
            selectinload(GameRoom.participants)
        )

        if status:
            query = query.where(GameRoom.status == status)

        if game_type_slug:
            query = query.join(GameType).where(GameType.slug == game_type_slug)

        query = query.limit(limit).order_by(GameRoom.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_ai_agent(
        self,
        room_id: str,
        personality_type: str = "balanced",
        difficulty_level: int = 3
    ) -> Player:
        """Create an AI agent and add to room.
        
        Args:
            room_id: Room ID
            personality_type: AI personality type
            difficulty_level: AI difficulty level (1-5)
            
        Returns:
            Created AI player
        """
        # Get room
        result = await self.db.execute(
            select(GameRoom).where(GameRoom.id == room_id)
        )
        room = result.scalar_one_or_none()

        if not room:
            raise NotFoundError("Room not found")

        # Create AI player
        ai_name = f"AI-{room.ai_agent_counter + 1}"
        room.ai_agent_counter += 1

        ai_player = Player(
            username=ai_name,
            display_name=ai_name,
            is_guest=True,
            player_type="ai"
        )
        self.db.add(ai_player)
        await self.db.flush()

        # Create participant
        participant = GameRoomParticipant(
            game_room_id=room.id,
            player_id=ai_player.id,
            is_ai_agent=True,
            ai_personality=personality_type
        )
        self.db.add(participant)

        # Create AI agent record
        ai_agent = AIAgent(
            player_id=ai_player.id,
            game_room_id=room.id,
            personality_type=personality_type,
            difficulty_level=difficulty_level
        )
        self.db.add(ai_agent)

        await self.db.commit()
        await self.db.refresh(ai_player)

        return ai_player

    async def remove_ai_agent(self, room_code: str, agent_id: str):
        """Remove an AI agent from room.
        
        Args:
            room_code: Room code
            agent_id: AI agent/participant ID
        """
        room = await self.get_room(room_code)

        if room.status != "Waiting":
            raise GameAlreadyStartedError("Cannot remove AI after game starts")

        # Find participant
        result = await self.db.execute(
            select(GameRoomParticipant).where(
                GameRoomParticipant.game_room_id == room.id,
                GameRoomParticipant.id == agent_id,
                GameRoomParticipant.is_ai_agent == True,
                GameRoomParticipant.left_at.is_(None)
            )
        )
        participant = result.scalar_one_or_none()

        if not participant:
            raise NotFoundError("AI agent not found in room")

        # Mark as left
        from datetime import datetime
        participant.left_at = datetime.utcnow()
        await self.db.commit()

    async def start_game(self, room_code: str) -> GameRoom:
        """Start a game.
        
        单人模式下无需验证房主，任何人都可以开始游戏。
        
        Args:
            room_code: Room code
            
        Returns:
            Updated room
        """
        room = await self.get_room(room_code)

        if room.status != "Waiting":
            raise GameAlreadyStartedError("Game already started")

        if not room.is_ready_to_start():
            raise BadRequestError(
                f"Need at least {room.min_players} players to start"
            )

        # Start game
        room.start()

        # Create initial game state
        game_state = GameState(
            game_room_id=room.id,
            current_turn="",  # Will be set by game logic
            game_data={}  # Use dict for MySQL JSON type
        )
        self.db.add(game_state)

        await self.db.commit()
        await self.db.refresh(room)

        return room

    async def delete_room(self, room_code: str):
        """Delete a room (only for Waiting status).
        
        单人模式下无需验证房主。
        
        Args:
            room_code: Room code
        """
        room = await self.get_room(room_code)

        if room.status != "Waiting":
            raise BadRequestError("Can only delete rooms in Waiting status")

        await self.db.delete(room)
        await self.db.commit()

    async def fill_ai_players(self, room: GameRoom) -> List[Player]:
        """Fill empty slots with AI players.
        
        根据房间的 min_players 配置自动创建 AI 玩家。
        
        Args:
            room: Game room to fill
            
        Returns:
            List of created AI players
        """
        active_count = room.get_active_participants_count()
        slots_to_fill = room.min_players - active_count

        if slots_to_fill <= 0:
            return []

        ai_personalities = [
            "analytical_detective",
            "intuitive_investigator",
            "cautious_observer",
            "bold_risk_taker",
            "strategic_thinker",
            "empathetic_listener"
        ]

        created_players = []
        for i in range(slots_to_fill):
            personality = ai_personalities[i % len(ai_personalities)]
            ai_player = await self.create_ai_agent(
                room.id,
                personality_type=personality,
                difficulty_level=3
            )
            created_players.append(ai_player)

        return created_players
