"""Game state management service."""

import json
import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import PlayerProfile
from src.services.games.crime_scene_engine import CrimeSceneEngine
from src.models.game import GameRoom, GameSession, GameState, GameType
from src.utils.errors import BadRequestError, NotFoundError

logger = logging.getLogger(__name__)

# Game duration limits (in minutes)
GAME_WARNING_DURATION = 120  # 2 hours - send warning
GAME_MAX_DURATION = 180  # 3 hours - terminate game

# Turn locks to prevent concurrent actions
_turn_locks: dict[str, bool] = {}


class GameStateService:
    """Service for managing game state during gameplay.
    
    Responsibilities:
    - Initialize game state when room starts
    - Update state after each action
    - Validate actions before applying
    - Check win conditions
    - Manage turn progression
    """

    def __init__(self, db: AsyncSession):
        """Initialize service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.crime_scene_engine = CrimeSceneEngine()

    async def initialize_game(
        self,
        game_room_id: UUID,
        game_type_slug: str = "crime-scene"
    ) -> GameState:
        """Initialize game state for a room that's starting.
        
        Args:
            game_room_id: Room to initialize game for
            game_type_slug: Type of game (currently only crime-scene)
            
        Returns:
            Created GameState
            
        Raises:
            NotFoundError: If room not found
            BadRequestError: If room not ready to start
        """
        # Get room and participants
        result = await self.db.execute(
            select(GameRoom).where(GameRoom.id == str(game_room_id))
        )
        room = result.scalar_one_or_none()

        if not room:
            raise NotFoundError(f"Game room {game_room_id} not found")

        if room.status != "In Progress":
            raise BadRequestError("Game room must be 'In Progress' to initialize game state")

        # Get active participants
        active_participants = [p for p in room.participants if p.left_at is None]
        player_ids = [str(p.player_id) if p.player_id else f"AI_{p.id}" for p in active_participants]

        # Initialize game based on type
        if game_type_slug == "crime-scene":
            game_data = self.crime_scene_engine.initialize_game(player_ids)
        else:
            raise BadRequestError(f"Unsupported game type: {game_type_slug}")

        # Create game state
        current_player_id = game_data["players"][0]

        game_state = GameState(
            game_room_id=str(game_room_id),
            current_phase=game_data["phase"],
            current_turn_player_id=current_player_id,
            turn_number=game_data["turn_number"],
            game_data=json.dumps(game_data)
        )

        self.db.add(game_state)
        await self.db.commit()
        await self.db.refresh(game_state)

        logger.info(f"Game state initialized for room {game_room_id}")
        return game_state

    async def get_current_state(self, game_room_id: UUID) -> GameState:
        """Get current game state for a room.
        
        Args:
            game_room_id: Room to get state for
            
        Returns:
            Current GameState
            
        Raises:
            NotFoundError: If state not found
        """
        result = await self.db.execute(
            select(GameState).where(GameState.game_room_id == str(game_room_id))
        )
        state = result.scalar_one_or_none()

        if not state:
            raise NotFoundError(f"Game state not found for room {game_room_id}")

        return state

    async def validate_action(
        self,
        game_room_id: UUID,
        player_id: str,
        action: dict[str, Any]
    ) -> bool:
        """Validate if an action is legal in current state.
        
        Args:
            game_room_id: Room where action is being taken
            player_id: Player taking action
            action: Action to validate
            
        Returns:
            True if valid, False otherwise
        """
        state = await self.get_current_state(game_room_id)
        game_data = json.loads(state.game_data)

        # Check if it's player's turn
        current_player = self.crime_scene_engine.get_current_player(game_data)
        if current_player != player_id:
            logger.warning(f"Action rejected: not {player_id}'s turn (current: {current_player})")
            return False

        # Check if action is valid
        valid_actions = self.crime_scene_engine.get_valid_actions(game_data, player_id)
        action_type = action.get("action_type") or action.get("type")
        valid_types = [a["type"] for a in valid_actions]

        if action_type not in valid_types:
            logger.warning(f"Action rejected: {action_type} not in valid actions {valid_types}")
            return False

        return True

    async def update_state(
        self,
        game_room_id: UUID,
        player_id: str,
        action: dict[str, Any]
    ) -> GameState:
        """Update game state after validated action.
        
        Args:
            game_room_id: Room to update
            player_id: Player who took action
            action: Action that was taken
            
        Returns:
            Updated GameState
            
        Raises:
            NotFoundError: If state not found
            BadRequestError: If action invalid or concurrent action conflict
        """
        room_key = str(game_room_id)

        # Check and acquire turn lock
        if _turn_locks.get(room_key, False):
            raise BadRequestError("另一个玩家正在行动，请稍候再试")

        try:
            # Acquire lock
            _turn_locks[room_key] = True

            # Validate action first
            if not await self.validate_action(game_room_id, player_id, action):
                raise BadRequestError("Invalid action for current game state")

            state = await self.get_current_state(game_room_id)
            game_data = json.loads(state.game_data)

            # Double-check it's still this player's turn (race condition check)
            current_player = self.crime_scene_engine.get_current_player(game_data)
            if current_player != player_id:
                raise BadRequestError("现在不是你的回合")

            # Apply action
            updated_data = self.crime_scene_engine.apply_action(game_data, player_id, action)

            # Update state
            state.game_data = json.dumps(updated_data)
            state.current_phase = updated_data["phase"]
            state.turn_number = updated_data["turn_number"]

            # Update current turn player
            next_player = self.crime_scene_engine.get_current_player(updated_data)
            state.current_turn_player_id = next_player
            state.updated_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(state)

            logger.info(f"Game state updated for room {game_room_id}, turn {state.turn_number}")
            return state

        finally:
            # Release lock
            _turn_locks[room_key] = False

    async def next_turn(self, game_room_id: UUID) -> str:
        """Advance to next player's turn.
        
        Args:
            game_room_id: Room to advance turn for
            
        Returns:
            Next player ID
        """
        state = await self.get_current_state(game_room_id)
        game_data = json.loads(state.game_data)

        # Get next player
        next_player = self.crime_scene_engine.get_current_player(game_data)
        state.current_turn_player_id = next_player

        await self.db.commit()
        return next_player

    async def check_win_condition(self, game_room_id: UUID) -> Optional[str]:
        """Check if game has been won.
        
        Args:
            game_room_id: Room to check
            
        Returns:
            Winner player_id if won, None otherwise
        """
        state = await self.get_current_state(game_room_id)
        game_data = json.loads(state.game_data)

        winner = self.crime_scene_engine.check_win_condition(game_data)
        return winner

    async def handle_timeout(self, game_room_id: UUID) -> None:
        """Handle turn timeout (player took too long).
        
        Args:
            game_room_id: Room where timeout occurred
        """
        logger.warning(f"Turn timeout in room {game_room_id}, skipping turn")

        # Skip to next turn
        state = await self.get_current_state(game_room_id)
        game_data = json.loads(state.game_data)

        # Advance turn index
        game_data["current_turn_index"] = (game_data["current_turn_index"] + 1) % len(game_data["players"])
        if game_data["current_turn_index"] == 0:
            game_data["turn_number"] += 1

        state.game_data = json.dumps(game_data)
        state.turn_number = game_data["turn_number"]
        state.current_turn_player_id = self.crime_scene_engine.get_current_player(game_data)
        state.updated_at = datetime.utcnow()

        await self.db.commit()

    async def record_game_session(
        self,
        game_room_id: UUID,
        winner_id: Optional[str] = None
    ) -> GameSession:
        """Record completed game session and update player statistics.
        
        Args:
            game_room_id: Room that completed
            winner_id: Player who won (None for tie)
            
        Returns:
            Created GameSession
            
        Raises:
            NotFoundError: If room or state not found
        """
        # Get room
        result = await self.db.execute(
            select(GameRoom).where(GameRoom.id == str(game_room_id))
        )
        room = result.scalar_one_or_none()

        if not room:
            raise NotFoundError(f"Game room {game_room_id} not found")

        # Get game state
        state = await self.get_current_state(game_room_id)

        # Get game type
        result = await self.db.execute(
            select(GameType).where(GameType.slug == "crime-scene")
        )
        game_type = result.scalar_one_or_none()

        if not game_type:
            raise NotFoundError("Game type 'crime-scene' not found")

        # Get active participants
        active_participants = [p for p in room.participants if p.left_at is None]
        human_participants = [p for p in active_participants if p.player_id is not None]
        ai_count = len([p for p in active_participants if p.player_id is None])

        # Calculate duration
        if not room.started_at:
            duration_minutes = 0
        else:
            duration = datetime.utcnow() - room.started_at
            duration_minutes = int(duration.total_seconds() / 60)

        # Create game session
        game_session = GameSession(
            game_room_id=str(game_room_id),
            game_type_id=game_type.id,
            winner_id=winner_id,
            started_at=room.started_at or datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_minutes=duration_minutes,
            participants_count=len(active_participants),
            ai_agents_count=ai_count,
            final_state=state.game_data
        )

        self.db.add(game_session)

        # Update player statistics
        for participant in human_participants:
            if participant.player_id:
                await self._update_player_stats(
                    participant.player_id,
                    game_type.id,
                    winner_id == participant.player_id,
                    duration_minutes
                )

        await self.db.commit()
        await self.db.refresh(game_session)

        logger.info(f"Game session recorded for room {game_room_id}, winner: {winner_id}")
        return game_session

    async def _update_player_stats(
        self,
        player_id: str,
        game_type_id: str,
        is_winner: bool,
        duration_minutes: int
    ) -> None:
        """Update player profile statistics after game.
        
        Args:
            player_id: Player to update
            game_type_id: Type of game played
            is_winner: Whether player won
            duration_minutes: Game duration
        """
        # Get or create player profile
        result = await self.db.execute(
            select(PlayerProfile).where(PlayerProfile.player_id == player_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            # Create new profile
            profile = PlayerProfile(player_id=player_id)
            self.db.add(profile)

        # Update stats
        profile.total_games += 1
        if is_winner:
            profile.total_wins += 1

        # Update favorite game (most played)
        # Simple approach: count games by type for this player
        result = await self.db.execute(
            select(GameSession)
            .join(GameRoom, GameSession.game_room_id == GameRoom.id)
            .join(GameRoom.participants)
            .where(GameRoom.participants.any(player_id=player_id))
            .where(GameSession.game_type_id == game_type_id)
        )
        games_of_this_type = len(result.scalars().all())

        # If this is the most played game type, set as favorite
        if not profile.favorite_game_id:
            profile.favorite_game_id = game_type_id
        else:
            # Check if this game type has more plays than current favorite
            result = await self.db.execute(
                select(GameSession)
                .join(GameRoom, GameSession.game_room_id == GameRoom.id)
                .join(GameRoom.participants)
                .where(GameRoom.participants.any(player_id=player_id))
                .where(GameSession.game_type_id == profile.favorite_game_id)
            )
            favorite_games_count = len(result.scalars().all())

            if games_of_this_type > favorite_games_count:
                profile.favorite_game_id = game_type_id

        profile.updated_at = datetime.utcnow()

        logger.info(f"Updated stats for player {player_id}: {profile.total_games} games, {profile.total_wins} wins")

    async def check_game_duration(self, game_room_id: UUID) -> dict[str, Any]:
        """Check if game has been running too long.
        
        Args:
            game_room_id: Room to check
            
        Returns:
            Dict with status: "ok", "warning", or "exceeded"
            and duration_minutes
            
        Raises:
            NotFoundError: If room not found
        """
        result = await self.db.execute(
            select(GameRoom).where(GameRoom.id == str(game_room_id))
        )
        room = result.scalar_one_or_none()

        if not room:
            raise NotFoundError(f"Game room {game_room_id} not found")

        # Calculate game duration
        if room.started_at:
            duration = datetime.utcnow() - room.started_at
            duration_minutes = int(duration.total_seconds() / 60)

            if duration_minutes >= GAME_MAX_DURATION:
                logger.warning(
                    f"Game {game_room_id} exceeded max duration "
                    f"({duration_minutes}/{GAME_MAX_DURATION} minutes)"
                )
                return {
                    "status": "exceeded",
                    "duration_minutes": duration_minutes,
                    "warning_threshold": GAME_WARNING_DURATION,
                    "max_duration": GAME_MAX_DURATION,
                    "message": f"游戏已运行{duration_minutes}分钟，超过最大时长限制"
                }
            elif duration_minutes >= GAME_WARNING_DURATION:
                logger.info(
                    f"Game {game_room_id} approaching max duration "
                    f"({duration_minutes}/{GAME_MAX_DURATION} minutes)"
                )
                return {
                    "status": "warning",
                    "duration_minutes": duration_minutes,
                    "warning_threshold": GAME_WARNING_DURATION,
                    "max_duration": GAME_MAX_DURATION,
                    "message": f"游戏已运行{duration_minutes}分钟，建议尽快结束"
                }
            else:
                return {
                    "status": "ok",
                    "duration_minutes": duration_minutes,
                    "warning_threshold": GAME_WARNING_DURATION,
                    "max_duration": GAME_MAX_DURATION
                }

        return {
            "status": "ok",
            "duration_minutes": 0,
            "warning_threshold": GAME_WARNING_DURATION,
            "max_duration": GAME_MAX_DURATION
        }
