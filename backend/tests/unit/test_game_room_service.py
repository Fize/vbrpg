"""Unit tests for GameRoomService."""
import pytest
from sqlalchemy import select

from src.services.game_room_service import GameRoomService
from src.models.game import GameRoom, GameRoomParticipant
from src.utils.errors import NotFoundError, BadRequestError, ConflictError, ForbiddenError


@pytest.mark.asyncio
class TestGameRoomServiceCreate:
    """Test GameRoomService.create_room method."""
    
    async def test_create_room_success(self, test_db, sample_game_type, sample_player):
        """Test successful room creation."""
        service = GameRoomService(test_db)
        
        room = await service.create_room(
            game_type_slug=sample_game_type.slug,
            creator_id=sample_player.id,
            max_players=6,
            min_players=4
        )
        
        assert room is not None
        assert room.code is not None
        assert len(room.code) == 8
        assert room.game_type_id == sample_game_type.id
        assert room.created_by == sample_player.id
        assert room.status == "Waiting"
        assert room.max_players == 6
        assert room.min_players == 4
        
        # Verify creator is added as participant
        stmt = select(GameRoomParticipant).where(
            GameRoomParticipant.game_room_id == room.id,
            GameRoomParticipant.player_id == sample_player.id
        )
        result = await test_db.execute(stmt)
        participant = result.scalar_one_or_none()
        assert participant is not None
    
    async def test_create_room_game_type_not_found(self, test_db, sample_player):
        """Test room creation fails with invalid game type."""
        service = GameRoomService(test_db)
        
        with pytest.raises(NotFoundError, match="Game type .* not found"):
            await service.create_room(
                game_type_slug="nonexistent-game",
                creator_id=sample_player.id,
                max_players=6,
                min_players=4
            )
    
    async def test_create_room_game_type_unavailable(self, test_db, sample_game_type, sample_player):
        """Test room creation fails with unavailable game type."""
        sample_game_type.is_available = False
        await test_db.commit()
        
        service = GameRoomService(test_db)
        
        with pytest.raises(BadRequestError, match="not available"):
            await service.create_room(
                game_type_slug=sample_game_type.slug,
                creator_id=sample_player.id,
                max_players=6,
                min_players=4
            )
    
    async def test_create_room_invalid_player_counts(self, test_db, sample_game_type, sample_player):
        """Test room creation fails with invalid player counts."""
        service = GameRoomService(test_db)
        
        # min_players greater than max_players (both within valid range)
        with pytest.raises(BadRequestError, match="min_players cannot be greater than max_players"):
            await service.create_room(
                game_type_slug=sample_game_type.slug,
                creator_id=sample_player.id,
                max_players=5,
                min_players=6
            )
        
        # max_players exceeds game type limit
        with pytest.raises(BadRequestError, match="max_players must be between"):
            await service.create_room(
                game_type_slug=sample_game_type.slug,
                creator_id=sample_player.id,
                max_players=10,
                min_players=4
            )
        
        # min_players below game type minimum
        with pytest.raises(BadRequestError, match="min_players must be between"):
            await service.create_room(
                game_type_slug=sample_game_type.slug,
                creator_id=sample_player.id,
                max_players=6,
                min_players=2
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
    
    async def test_list_all_rooms(self, test_db, sample_game_type, sample_player):
        """Test listing all rooms."""
        service = GameRoomService(test_db)
        
        # Create multiple rooms
        await service.create_room(sample_game_type.slug, 6, 4, sample_player.id)
        await service.create_room(sample_game_type.slug, 8, 4, sample_player.id)
        
        rooms = await service.list_rooms()
        
        assert len(rooms) >= 2
    
    async def test_list_rooms_by_status(self, test_db, sample_game_type, sample_player):
        """Test listing rooms filtered by status."""
        service = GameRoomService(test_db)
        
        room1 = await service.create_room(sample_game_type.slug, 6, 4, sample_player.id)
        room2 = await service.create_room(sample_game_type.slug, 6, 4, sample_player.id)
        
        # Change room2 to In Progress
        room2.status = "In Progress"
        await test_db.commit()
        
        waiting_rooms = await service.list_rooms(status="Waiting")
        
        assert any(r.code == room1.code for r in waiting_rooms)
        assert not any(r.code == room2.code for r in waiting_rooms)
    
    async def test_list_rooms_by_game_type(self, test_db, sample_game_type, sample_player):
        """Test listing rooms filtered by game type."""
        service = GameRoomService(test_db)
        
        room = await service.create_room(sample_game_type.slug, 6, 4, sample_player.id)
        
        rooms = await service.list_rooms(game_type_slug=sample_game_type.slug)
        
        assert any(r.code == room.code for r in rooms)
        assert all(r.game_type_id == sample_game_type.id for r in rooms)
    
    async def test_list_rooms_with_limit(self, test_db, sample_game_type, sample_player):
        """Test listing rooms with limit."""
        service = GameRoomService(test_db)
        
        # Create multiple rooms
        for _ in range(5):
            await service.create_room(sample_game_type.slug, 6, 4, sample_player.id)
        
        rooms = await service.list_rooms(limit=3)
        
        assert len(rooms) == 3


@pytest.mark.asyncio
class TestGameRoomServiceJoin:
    """Test GameRoomService.join_room method."""
    
    async def test_join_room_success(self, test_db, sample_game_room, sample_guest_player):
        """Test joining a room successfully."""
        service = GameRoomService(test_db)
        
        await service.join_room(sample_game_room.code, sample_guest_player.id)
        
        # Verify participant was added
        stmt = select(GameRoomParticipant).where(
            GameRoomParticipant.game_room_id == sample_game_room.id,
            GameRoomParticipant.player_id == sample_guest_player.id
        )
        result = await test_db.execute(stmt)
        participant = result.scalar_one_or_none()
        
        assert participant is not None
        assert participant.is_ai_agent is False
    
    async def test_join_room_already_joined(self, test_db, sample_game_room, sample_player):
        """Test joining a room twice fails."""
        service = GameRoomService(test_db)
        
        # Player is already creator (first participant)
        with pytest.raises(ConflictError, match="Already in this room"):
            await service.join_room(sample_game_room.code, sample_player.id)
    
    async def test_join_room_full(self, test_db, sample_game_room, sample_guest_player):
        """Test joining a full room fails."""
        service = GameRoomService(test_db)
        
        # Fill room to max_players (6)
        for i in range(5):  # Already has 1 creator
            participant = GameRoomParticipant(
                game_room_id=sample_game_room.id,
                player_id=None,
                is_ai_agent=True,
                ai_personality="detective",
            )
            test_db.add(participant)
        await test_db.commit()
        
        with pytest.raises(BadRequestError, match="Room is full"):
            await service.join_room(sample_game_room.code, sample_guest_player.id)
    
    async def test_join_room_in_progress(self, test_db, sample_game_room, sample_guest_player):
        """Test joining an in-progress room fails."""
        service = GameRoomService(test_db)
        
        sample_game_room.status = "In Progress"
        await test_db.commit()
        
        with pytest.raises(BadRequestError, match="cannot join"):
            await service.join_room(sample_game_room.code, sample_guest_player.id)


@pytest.mark.asyncio
class TestGameRoomServiceLeave:
    """Test GameRoomService.leave_room method."""
    
    async def test_leave_room_success(self, test_db, sample_game_room, sample_player):
        """Test leaving a room successfully."""
        service = GameRoomService(test_db)
        
        await service.leave_room(sample_game_room.code, sample_player.id)
        
        # Verify participant left
        stmt = select(GameRoomParticipant).where(
            GameRoomParticipant.game_room_id == sample_game_room.id,
            GameRoomParticipant.player_id == sample_player.id
        )
        result = await test_db.execute(stmt)
        participant = result.scalar_one()
        
        assert participant.left_at is not None
    
    async def test_leave_room_not_in_room(self, test_db, sample_game_room, sample_guest_player):
        """Test leaving a room you're not in fails."""
        service = GameRoomService(test_db)
        
        with pytest.raises(NotFoundError, match="Not in this room"):
            await service.leave_room(sample_game_room.code, sample_guest_player.id)


@pytest.mark.asyncio
class TestGameRoomServiceStart:
    """Test GameRoomService.start_game method."""
    
    async def test_start_game_with_enough_players(
        self, test_db, sample_game_room, sample_player, sample_guest_player
    ):
        """Test starting a game with enough players."""
        service = GameRoomService(test_db)
        
        # Add participants to reach min_players
        participant = GameRoomParticipant(
            game_room_id=sample_game_room.id,
            player_id=sample_guest_player.id,
            is_ai_agent=False,
        )
        test_db.add(participant)
        await test_db.commit()
        
        # Fill remaining slots with AI
        room = await service.start_game(sample_game_room.code, sample_player.id)
        
        assert room.status == "In Progress"
        
        # Check AI agents were added
        stmt = select(GameRoomParticipant).where(
            GameRoomParticipant.game_room_id == sample_game_room.id,
            GameRoomParticipant.is_ai_agent == True
        )
        result = await test_db.execute(stmt)
        ai_agents = result.scalars().all()
        
        # Should have 2 AI agents (min_players=4, we have 2 humans)
        assert len(ai_agents) >= 2
        
        # Verify GameState was created by querying directly
        from src.models.game import GameState
        stmt_state = select(GameState).where(GameState.game_room_id == sample_game_room.id)
        result_state = await test_db.execute(stmt_state)
        game_state = result_state.scalar_one_or_none()
        
        assert game_state is not None
        assert game_state.current_phase == "setup"
        assert game_state.turn_number == 1
        
        # Verify game_data contains participants
        import json
        game_data = json.loads(game_state.game_data)
        assert game_data["phase"] == "setup"
        assert game_data["round"] == 1
        assert len(game_data["participants"]) == 4  # 2 humans + 2 AI
    
    async def test_start_game_not_creator(self, test_db, sample_game_room, sample_guest_player):
        """Test starting a game by non-creator fails."""
        service = GameRoomService(test_db)
        
        with pytest.raises(ForbiddenError, match="Only room creator can start"):
            await service.start_game(sample_game_room.code, sample_guest_player.id)
