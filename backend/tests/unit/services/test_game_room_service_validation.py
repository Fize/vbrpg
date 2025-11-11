"""Unit tests for GameRoomService join validation logic.

Tests for Phase 2 Feature 002: Room join validation.
"""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.game_room import GameRoom
from src.models.game_room_participant import GameRoomParticipant
from src.models.game_type import GameType
from src.models.player import Player
from src.services.game_room_service import GameRoomService
from src.utils.errors import (
    RoomNotFoundError,
    RoomFullError,
    GameAlreadyStartedError,
    DuplicateJoinError
)


@pytest.mark.asyncio
class TestGameRoomServiceValidation:
    """Test GameRoomService join validation logic."""

    async def test_validate_join_rejects_nonexistent_room(
        self,
        test_db: AsyncSession,
        sample_player: Player
    ):
        """Test that validate_join_request rejects non-existent room codes."""
        service = GameRoomService(test_db)
        
        with pytest.raises(RoomNotFoundError) as exc_info:
            await service.validate_join_request("INVALID", sample_player.id)
        
        assert "not found" in str(exc_info.value).lower()

    async def test_validate_join_rejects_full_room(
        self,
        test_db: AsyncSession,
        sample_game_type: GameType,
        sample_player: Player
    ):
        """Test that validate_join_request rejects full rooms (SC-006)."""
        # Create full room
        room = GameRoom(
            id=str(uuid.uuid4()),
            code="FULL01",
            game_type_id=sample_game_type.id,
            status="Waiting",
            max_players=3,
            min_players=2,
            created_by=sample_player.id,
            owner_id=sample_player.id,
            current_participant_count=3,  # At capacity
            ai_agent_counter=0,
            created_at=datetime.now(timezone.utc)
        )
        test_db.add(room)
        await test_db.commit()
        
        # Create new player trying to join
        new_player = Player(username=f"new_{uuid.uuid4().hex[:8]}", is_guest=False)
        test_db.add(new_player)
        await test_db.commit()
        
        service = GameRoomService(test_db)
        
        with pytest.raises(RoomFullError) as exc_info:
            await service.validate_join_request(room.code, new_player.id)
        
        assert "full" in str(exc_info.value).lower()

    async def test_validate_join_rejects_in_progress_game(
        self,
        test_db: AsyncSession,
        sample_game_type: GameType,
        sample_player: Player
    ):
        """Test that validate_join_request rejects games already in progress (FR-004)."""
        # Create in-progress room
        room = GameRoom(
            id=str(uuid.uuid4()),
            code="PROG01",
            game_type_id=sample_game_type.id,
            status="In Progress",  # Game started
            max_players=6,
            min_players=3,
            created_by=sample_player.id,
            owner_id=sample_player.id,
            current_participant_count=4,
            ai_agent_counter=0,
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc)
        )
        test_db.add(room)
        await test_db.commit()
        
        # Create new player trying to join
        new_player = Player(username=f"new_{uuid.uuid4().hex[:8]}", is_guest=False)
        test_db.add(new_player)
        await test_db.commit()
        
        service = GameRoomService(test_db)
        
        with pytest.raises(GameAlreadyStartedError) as exc_info:
            await service.validate_join_request(room.code, new_player.id)
        
        assert "started" in str(exc_info.value).lower() or "in progress" in str(exc_info.value).lower()

    async def test_validate_join_rejects_duplicate_join(
        self,
        test_db: AsyncSession,
        sample_game_type: GameType,
        sample_player: Player
    ):
        """Test that validate_join_request rejects duplicate joins (FR-012)."""
        # Create room with player already in it
        room = GameRoom(
            id=str(uuid.uuid4()),
            code="DUP001",
            game_type_id=sample_game_type.id,
            status="Waiting",
            max_players=6,
            min_players=3,
            created_by=sample_player.id,
            owner_id=sample_player.id,
            current_participant_count=1,
            ai_agent_counter=0,
            created_at=datetime.now(timezone.utc)
        )
        test_db.add(room)
        
        # Add participant
        participant = GameRoomParticipant(
            id=str(uuid.uuid4()),
            game_room_id=room.id,
            player_id=sample_player.id,
            is_ai_agent=False,
            is_owner=True,
            joined_at=datetime.now(timezone.utc),
            join_timestamp=datetime.now(timezone.utc),
            replaced_by_ai=False
        )
        test_db.add(participant)
        await test_db.commit()
        
        service = GameRoomService(test_db)
        
        # Try to join again
        with pytest.raises(DuplicateJoinError) as exc_info:
            await service.validate_join_request(room.code, sample_player.id)
        
        assert "already" in str(exc_info.value).lower()

    async def test_validate_join_accepts_valid_request(
        self,
        test_db: AsyncSession,
        sample_game_type: GameType,
        sample_player: Player
    ):
        """Test that validate_join_request accepts valid join requests."""
        # Create room with space
        owner = Player(username=f"owner_{uuid.uuid4().hex[:8]}", is_guest=False)
        test_db.add(owner)
        await test_db.commit()
        
        room = GameRoom(
            id=str(uuid.uuid4()),
            code="VALID1",
            game_type_id=sample_game_type.id,
            status="Waiting",
            max_players=6,
            min_players=3,
            created_by=owner.id,
            owner_id=owner.id,
            current_participant_count=1,
            ai_agent_counter=0,
            created_at=datetime.now(timezone.utc)
        )
        test_db.add(room)
        
        # Add owner participant
        owner_participant = GameRoomParticipant(
            id=str(uuid.uuid4()),
            game_room_id=room.id,
            player_id=owner.id,
            is_ai_agent=False,
            is_owner=True,
            joined_at=datetime.now(timezone.utc),
            join_timestamp=datetime.now(timezone.utc),
            replaced_by_ai=False
        )
        test_db.add(owner_participant)
        await test_db.commit()
        
        service = GameRoomService(test_db)
        
        # Should not raise any exception
        result = await service.validate_join_request(room.code, sample_player.id)
        assert result is True or result is None  # Depends on implementation
