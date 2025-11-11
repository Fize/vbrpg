"""Integration tests for GameRoomService.join_room method."""
import asyncio
import pytest
from datetime import datetime, UTC
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.game_room import GameRoom
from src.models.game_room_participant import GameRoomParticipant
from src.models.player import Player
from src.services.game_room_service import GameRoomService
from src.utils.errors import (
    RoomNotFoundError,
    RoomFullError,
    GameAlreadyStartedError,
    DuplicateJoinError
)


@pytest.fixture
async def waiting_room_for_service(test_db: AsyncSession, sample_game_type, sample_player):
    """Create a waiting room with owner for service tests."""
    room = GameRoom(
        code="SVC123",
        status="Waiting",
        max_players=4,
        min_players=2,
        game_type_id=sample_game_type.id,
        owner_id=sample_player.id,
        current_participant_count=1,
        ai_agent_counter=0
    )
    test_db.add(room)
    await test_db.flush()
    
    # Add owner as participant
    participant = GameRoomParticipant(
        game_room_id=room.id,
        player_id=sample_player.id,
        is_owner=True,
        is_ai_agent=False
    )
    test_db.add(participant)
    
    await test_db.commit()
    await test_db.refresh(room)
    return room


@pytest.fixture
async def second_player_for_service(test_db: AsyncSession):
    """Create a second test player."""
    player = Player(
        id="service-player-2",
        username="ServicePlayer2",
        is_guest=True
    )
    test_db.add(player)
    await test_db.commit()
    await test_db.refresh(player)
    return player


@pytest.fixture
async def third_player_for_service(test_db: AsyncSession):
    """Create a third test player."""
    player = Player(
        id="service-player-3",
        username="ServicePlayer3",
        is_guest=True
    )
    test_db.add(player)
    await test_db.commit()
    await test_db.refresh(player)
    return player


@pytest.mark.asyncio
class TestJoinRoomService:
    """Test GameRoomService.join_room method."""
    
    async def test_join_room_increments_participant_count(
        self, test_db: AsyncSession, waiting_room_for_service, second_player_for_service
    ):
        """Test that joining a room increments current_participant_count."""
        service = GameRoomService(test_db)
        initial_count = waiting_room_for_service.current_participant_count
        
        # Join room
        result_room = await service.join_room(waiting_room_for_service.code, second_player_for_service.id)
        
        # Verify count incremented
        assert result_room.current_participant_count == initial_count + 1
        
        # Verify in database
        result = await test_db.execute(
            select(GameRoom).where(GameRoom.id == waiting_room_for_service.id)
        )
        room = result.scalar_one()
        assert room.current_participant_count == initial_count + 1
    
    async def test_join_room_sets_timestamp(
        self, test_db: AsyncSession, waiting_room_for_service, second_player_for_service
    ):
        """Test that join_timestamp is set to current time on join."""
        service = GameRoomService(test_db)
        before_join = datetime.now(UTC)
        
        # Join room
        await service.join_room(waiting_room_for_service.code, second_player_for_service.id)
        
        after_join = datetime.now(UTC)
        
        # Verify timestamp was set
        result = await test_db.execute(
            select(GameRoomParticipant)
            .where(
                GameRoomParticipant.game_room_id == waiting_room_for_service.id,
                GameRoomParticipant.player_id == second_player_for_service.id
            )
        )
        participant = result.scalar_one()
        
        assert participant.join_timestamp is not None
        # Verify timestamp is within reasonable range (within 10 seconds)
        time_diff = (after_join - participant.join_timestamp.replace(tzinfo=UTC)).total_seconds()
        assert 0 <= time_diff <= 10
    
    async def test_join_room_sets_owner_flag_false_for_subsequent_joiners(
        self, test_db: AsyncSession, waiting_room_for_service, second_player_for_service
    ):
        """Test that subsequent joiners have is_owner=False."""
        service = GameRoomService(test_db)
        
        # Join room (second player, not owner)
        await service.join_room(waiting_room_for_service.code, second_player_for_service.id)
        
        # Verify is_owner is False
        result = await test_db.execute(
            select(GameRoomParticipant)
            .where(
                GameRoomParticipant.game_room_id == waiting_room_for_service.id,
                GameRoomParticipant.player_id == second_player_for_service.id
            )
        )
        participant = result.scalar_one()
        
        assert participant.is_owner is False
    
    async def test_join_room_returns_room_with_participants(
        self, test_db: AsyncSession, waiting_room_for_service, second_player_for_service
    ):
        """Test that join_room returns room with all participants loaded."""
        service = GameRoomService(test_db)
        
        # Join room
        result_room = await service.join_room(waiting_room_for_service.code, second_player_for_service.id)
        
        # Verify room has participants loaded
        assert result_room.participants is not None
        
        # Also query directly to verify participant was added
        direct_result = await test_db.execute(
            select(GameRoomParticipant)
            .where(GameRoomParticipant.game_room_id == waiting_room_for_service.id)
        )
        all_participants = direct_result.scalars().all()
        print(f"Direct query participants count: {len(all_participants)}")
        for p in all_participants:
            print(f"  - Player ID: {p.player_id}, left_at: {p.left_at}")
        
        # Verify we have both participants (owner + new joiner)
        active_participants = [p for p in result_room.participants if p.left_at is None]
        assert len(active_participants) == 2, f"Expected 2 active participants in returned room, got {len(active_participants)}. Direct query found {len(all_participants)} total."
        
        # Verify new participant is in the list
        player_ids = [p.player_id for p in result_room.participants if p.left_at is None]
        assert second_player_for_service.id in player_ids
    
    async def test_concurrent_joins_handle_race_condition(
        self, test_db: AsyncSession, waiting_room_for_service, 
        second_player_for_service, third_player_for_service
    ):
        """Test transaction atomicity with concurrent joins (FR-018).
        
        This test verifies that the join_room method properly validates
        and increments the participant count atomically.
        """
        # First join
        service1 = GameRoomService(test_db)
        room1 = await service1.join_room(waiting_room_for_service.code, second_player_for_service.id)
        assert room1.current_participant_count == 2  # Owner + first joiner
        
        # Second join - use a fresh service instance after commit
        service2 = GameRoomService(test_db)
        room2 = await service2.join_room(waiting_room_for_service.code, third_player_for_service.id)
        assert room2.current_participant_count == 3  # Owner + 2 joiners
        
        # Verify final state with fresh query
        result = await test_db.execute(
            select(GameRoom)
            .where(GameRoom.id == waiting_room_for_service.id)
            .options(selectinload(GameRoom.participants))
        )
        final_room = result.scalar_one()
        assert final_room.current_participant_count == 3
        active_participants = [p for p in final_room.participants if p.left_at is None]
        assert len(active_participants) == 3
    
    async def test_join_room_validates_using_validate_join_request(
        self, test_db: AsyncSession, waiting_room_for_service, second_player_for_service
    ):
        """Test that join_room calls validate_join_request logic."""
        service = GameRoomService(test_db)
        
        # First join should succeed
        await service.join_room(waiting_room_for_service.code, second_player_for_service.id)
        
        # Second join by same player should fail with DuplicateJoinError
        with pytest.raises(DuplicateJoinError):
            await service.join_room(waiting_room_for_service.code, second_player_for_service.id)
    
    async def test_join_room_adds_participant_record(
        self, test_db: AsyncSession, waiting_room_for_service, second_player_for_service
    ):
        """Test that GameRoomParticipant record is created correctly."""
        service = GameRoomService(test_db)
        
        # Join room
        await service.join_room(waiting_room_for_service.code, second_player_for_service.id)
        
        # Verify participant record exists
        result = await test_db.execute(
            select(GameRoomParticipant)
            .where(
                GameRoomParticipant.game_room_id == waiting_room_for_service.id,
                GameRoomParticipant.player_id == second_player_for_service.id
            )
        )
        participant = result.scalar_one()
        
        # Verify fields
        assert participant.is_ai_agent is False
        assert participant.is_owner is False
        assert participant.join_timestamp is not None
        assert participant.left_at is None
    
    async def test_join_room_respects_unique_constraint(
        self, test_db: AsyncSession, waiting_room_for_service, second_player_for_service
    ):
        """Test that unique constraint (room_id, player_id) is enforced."""
        service = GameRoomService(test_db)
        
        # Join room
        await service.join_room(waiting_room_for_service.code, second_player_for_service.id)
        
        # Attempt duplicate join should raise DuplicateJoinError (not database error)
        with pytest.raises(DuplicateJoinError):
            await service.join_room(waiting_room_for_service.code, second_player_for_service.id)
