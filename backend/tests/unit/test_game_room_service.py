"""Unit tests for GameRoomService (单人模式).

单人模式下：
- 无需用户认证
- 所有玩家都是 AI 代理
- 用户可以选择观战或参与
"""
import pytest
from sqlalchemy import select

from src.services.game_room_service import GameRoomService
from src.models.game import GameRoom, GameRoomParticipant, GameState
from src.utils.errors import NotFoundError, BadRequestError, GameAlreadyStartedError


@pytest.mark.asyncio
class TestGameRoomServiceCreate:
    """Test GameRoomService.create_room method for single-player mode."""
    
    async def test_create_room_success(self, test_db, sample_game_type):
        """Test successful room creation without user authentication."""
        service = GameRoomService(test_db)
        
        room = await service.create_room(
            game_type_slug=sample_game_type["slug"],
            max_players=10,
            min_players=10
        )
        
        assert room is not None
        assert room.code is not None
        assert len(room.code) == 8
        assert room.game_type_id == sample_game_type["slug"]
        assert room.status == "Waiting"
        assert room.max_players == 10
        assert room.min_players == 10
        # 单人模式默认为旁观者模式
        assert room.user_role == "spectator"
        assert room.is_spectator_mode is True
    
    async def test_create_room_with_participant_role(self, test_db, sample_game_type):
        """Test room creation with participant role selection."""
        service = GameRoomService(test_db)
        
        room = await service.create_room(
            game_type_slug=sample_game_type["slug"],
            max_players=10,
            min_players=10,
            user_role="detective",
            is_spectator_mode=False
        )
        
        assert room.user_role == "detective"
        assert room.is_spectator_mode is False
    
    async def test_create_room_game_type_not_found(self, test_db):
        """Test room creation fails with invalid game type."""
        service = GameRoomService(test_db)
        
        with pytest.raises(NotFoundError, match="Game type .* not found"):
            await service.create_room(
                game_type_slug="nonexistent-game",
                max_players=10,
                min_players=10
            )
    
    async def test_create_room_invalid_player_counts(self, test_db, sample_game_type):
        """Test room creation fails with invalid player counts."""
        service = GameRoomService(test_db)
        
        # min_players greater than max_players
        with pytest.raises(BadRequestError, match="cannot exceed maximum"):
            await service.create_room(
                game_type_slug=sample_game_type["slug"],
                max_players=8,
                min_players=10
            )
        
        # min_players less than required for werewolf
        with pytest.raises(BadRequestError, match="Minimum players cannot be less than 6"):
            await service.create_room(
                game_type_slug=sample_game_type["slug"],
                max_players=10,
                min_players=4
            )


@pytest.mark.asyncio
class TestGameRoomServiceGet:
    """Test GameRoomService.get_room method."""
    
    async def test_get_room_success(self, test_db, sample_game_room):
        """Test getting an existing room."""
        service = GameRoomService(test_db)
        
        room = await service.get_room(sample_game_room.code)
        
        assert room is not None
        assert room.id == sample_game_room.id
        assert room.code == sample_game_room.code
    
    async def test_get_room_not_found(self, test_db):
        """Test getting a nonexistent room."""
        service = GameRoomService(test_db)
        
        with pytest.raises(NotFoundError, match="Room .* not found"):
            await service.get_room("NOTFOUND")


@pytest.mark.asyncio
class TestGameRoomServiceList:
    """Test GameRoomService.list_rooms method."""
    
    async def test_list_all_rooms(self, test_db, sample_game_type):
        """Test listing all rooms."""
        service = GameRoomService(test_db)
        
        # Create multiple rooms
        await service.create_room(sample_game_type["slug"], 10, 10)
        await service.create_room(sample_game_type["slug"], 12, 10)
        
        rooms = await service.list_rooms()
        
        assert len(rooms) >= 2
    
    async def test_list_rooms_by_status(self, test_db, sample_game_type):
        """Test listing rooms filtered by status."""
        service = GameRoomService(test_db)
        
        room1 = await service.create_room(sample_game_type["slug"], 10, 10)
        room2 = await service.create_room(sample_game_type["slug"], 10, 10)
        
        # Change room2 to In Progress
        room2.status = "In Progress"
        await test_db.commit()
        
        waiting_rooms = await service.list_rooms(status="Waiting")
        
        assert any(r.code == room1.code for r in waiting_rooms)
        assert not any(r.code == room2.code for r in waiting_rooms)
    
    async def test_list_rooms_by_game_type(self, test_db, sample_game_type):
        """Test listing rooms filtered by game type."""
        service = GameRoomService(test_db)
        
        room = await service.create_room(sample_game_type["slug"], 10, 10)
        
        rooms = await service.list_rooms(game_type_slug=sample_game_type["slug"])
        
        assert any(r.code == room.code for r in rooms)
        assert all(r.game_type_id == sample_game_type["slug"] for r in rooms)
    
    async def test_list_rooms_with_limit(self, test_db, sample_game_type):
        """Test listing rooms with limit."""
        service = GameRoomService(test_db)
        
        # Create multiple rooms
        for _ in range(5):
            await service.create_room(sample_game_type["slug"], 10, 10)
        
        rooms = await service.list_rooms(limit=3)
        
        assert len(rooms) == 3


@pytest.mark.asyncio
class TestGameRoomServiceAI:
    """Test AI agent management for single-player mode."""
    
    async def test_create_ai_agent(self, test_db, sample_game_room):
        """Test creating an AI agent in a room."""
        service = GameRoomService(test_db)
        
        participant = await service.create_ai_agent(
            room_id=sample_game_room.id,
            personality_type="analytical_detective",
            difficulty_level=3
        )
        
        assert participant is not None
        assert participant.is_ai_agent is True
        assert participant.ai_personality == "analytical_detective"
        assert "AI" in participant.player.username
        assert participant.player.is_guest is True
    
    async def test_fill_ai_players(self, test_db, sample_game_room):
        """Test auto-filling room with AI players."""
        service = GameRoomService(test_db)
        
        # sample_game_room has min_players=4, currently 1 participant (the creator)
        ai_players = await service.fill_ai_players(sample_game_room)
        
        # Should create min_players - 1 AI players (since creator is already a participant)
        assert len(ai_players) == sample_game_room.min_players - 1
        
        # Verify participants were created
        stmt = select(GameRoomParticipant).where(
            GameRoomParticipant.game_room_id == sample_game_room.id,
            GameRoomParticipant.is_ai_agent == True
        )
        result = await test_db.execute(stmt)
        participants = result.scalars().all()
        
        # Should have min_players - 1 AI participants (plus 1 human creator = min_players total)
        assert len(participants) == sample_game_room.min_players - 1
    
    async def test_remove_ai_agent(self, test_db, sample_game_room):
        """Test removing an AI agent from a room."""
        service = GameRoomService(test_db)
        
        # First create an AI agent
        participant = await service.create_ai_agent(
            room_id=sample_game_room.id,
            personality_type="analytical_detective",
            difficulty_level=3
        )
        
        # Remove the AI agent
        await service.remove_ai_agent(sample_game_room.code, participant.id)
        
        # Verify participant is marked as left
        await test_db.refresh(participant)
        assert participant.left_at is not None


@pytest.mark.asyncio
class TestGameRoomServiceStart:
    """Test GameRoomService.start_game method for single-player mode."""
    
    async def test_start_game_with_ai_agents(self, test_db, sample_game_room):
        """Test starting a game after filling with AI agents."""
        service = GameRoomService(test_db)
        
        # Fill room with AI agents
        await service.fill_ai_players(sample_game_room)
        
        # Start the game
        room = await service.start_game(sample_game_room.code)
        
        assert room.status == "In Progress"
        assert room.started_at is not None
        
        # Verify GameState was created
        stmt = select(GameState).where(GameState.game_room_id == sample_game_room.id)
        result = await test_db.execute(stmt)
        game_state = result.scalar_one_or_none()
        
        assert game_state is not None
    
    async def test_start_game_not_enough_players(self, test_db, sample_game_room):
        """Test starting a game with not enough players fails."""
        service = GameRoomService(test_db)
        
        # Don't add any AI agents
        with pytest.raises(BadRequestError, match="at least"):
            await service.start_game(sample_game_room.code)
    
    async def test_start_game_already_started(self, test_db, sample_game_room):
        """Test starting an already started game fails."""
        service = GameRoomService(test_db)
        
        # Fill and start
        await service.fill_ai_players(sample_game_room)
        await service.start_game(sample_game_room.code)
        
        # Try to start again
        with pytest.raises(GameAlreadyStartedError):
            await service.start_game(sample_game_room.code)


@pytest.mark.asyncio
class TestGameRoomServiceDelete:
    """Test GameRoomService.delete_room method for single-player mode."""
    
    async def test_delete_waiting_room(self, test_db, sample_game_room):
        """Test deleting a waiting room."""
        service = GameRoomService(test_db)
        
        room_code = sample_game_room.code
        
        await service.delete_room(room_code)
        
        # Verify room is deleted
        with pytest.raises(NotFoundError):
            await service.get_room(room_code)
    
    async def test_delete_started_room_fails(self, test_db, sample_game_room):
        """Test deleting a started room fails."""
        service = GameRoomService(test_db)
        
        # Start the room
        await service.fill_ai_players(sample_game_room)
        await service.start_game(sample_game_room.code)
        
        # Try to delete
        with pytest.raises(BadRequestError, match="Waiting"):
            await service.delete_room(sample_game_room.code)

