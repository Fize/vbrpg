"""Unit tests for GameRoom model extensions.

Tests for Phase 2 Feature 002: owner_id, current_participant_count, ai_agent_counter.
"""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.game_room import GameRoom
from src.models.game_type import GameType
from src.models.player import Player


@pytest.mark.asyncio
class TestGameRoomModelExtensions:
    """Test GameRoom model extensions for owner tracking and counters."""

    async def test_owner_id_relationship_resolves_to_player(
        self,
        test_db: AsyncSession,
        sample_game_type: GameType,
        sample_player: Player
    ):
        """Test that owner_id relationship correctly resolves to Player entity."""
        # Create room with owner
        room = GameRoom(
            id=str(uuid.uuid4()),
            code="TEST1234",
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
        await test_db.commit()
        
        # Refresh and verify relationship
        await test_db.refresh(room)
        assert room.owner_id == sample_player.id
        assert room.owner.username == sample_player.username

    async def test_has_capacity_returns_true_when_space_available(
        self,
        test_db: AsyncSession,
        sample_game_type: GameType,
        sample_player: Player
    ):
        """Test has_capacity() returns True when room has space."""
        room = GameRoom(
            id=str(uuid.uuid4()),
            code="CAP001",
            game_type_id=sample_game_type.id,
            status="Waiting",
            max_players=6,
            min_players=3,
            created_by=sample_player.id,
            owner_id=sample_player.id,
            current_participant_count=3,
            ai_agent_counter=0,
            created_at=datetime.now(timezone.utc)
        )
        test_db.add(room)
        await test_db.commit()
        await test_db.refresh(room)
        
        assert room.has_capacity() is True

    async def test_has_capacity_returns_false_when_full(
        self,
        test_db: AsyncSession,
        sample_game_type: GameType,
        sample_player: Player
    ):
        """Test has_capacity() returns False when room is at max capacity."""
        room = GameRoom(
            id=str(uuid.uuid4()),
            code="FULL01",
            game_type_id=sample_game_type.id,
            status="Waiting",
            max_players=6,
            min_players=3,
            created_by=sample_player.id,
            owner_id=sample_player.id,
            current_participant_count=6,
            ai_agent_counter=0,
            created_at=datetime.now(timezone.utc)
        )
        test_db.add(room)
        await test_db.commit()
        await test_db.refresh(room)
        
        assert room.has_capacity() is False

    async def test_increment_ai_counter_returns_sequential_name(
        self,
        test_db: AsyncSession,
        sample_game_type: GameType,
        sample_player: Player
    ):
        """Test increment_ai_counter() returns sequential AI player names."""
        room = GameRoom(
            id=str(uuid.uuid4()),
            code="AISEQ01",
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
        await test_db.commit()
        await test_db.refresh(room)
        
        # Test sequential AI names
        name1 = room.increment_ai_counter()
        assert name1 == "AI玩家1"
        assert room.ai_agent_counter == 1
        
        name2 = room.increment_ai_counter()
        assert name2 == "AI玩家2"
        assert room.ai_agent_counter == 2
        
        name3 = room.increment_ai_counter()
        assert name3 == "AI玩家3"
        assert room.ai_agent_counter == 3
