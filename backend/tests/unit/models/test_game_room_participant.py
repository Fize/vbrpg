"""Unit tests for GameRoomParticipant model extensions.

Tests for Phase 2 Feature 002: is_owner, join_timestamp.
"""
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.models.game import GameRoom, GameRoomParticipant, GameType
from src.models.user import Player


@pytest.mark.asyncio
class TestGameRoomParticipantModelExtensions:
    """Test GameRoomParticipant model extensions for ownership and timestamps."""

    async def test_is_owner_flag_identifies_owner(
        self,
        test_db: AsyncSession,
        sample_game_type: GameType,
        sample_player: Player
    ):
        """Test that is_owner flag correctly identifies the room owner."""
        # Create room
        room = GameRoom(
            id=str(uuid.uuid4()),
            code="OWN001",
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
        
        # Create owner participant
        owner_participant = GameRoomParticipant(
            id=str(uuid.uuid4()),
            game_room_id=room.id,
            player_id=sample_player.id,
            is_ai_agent=False,
            is_owner=True,
            joined_at=datetime.now(timezone.utc),
            join_timestamp=datetime.now(timezone.utc),
            replaced_by_ai=False
        )
        test_db.add(owner_participant)
        
        # Create non-owner player
        player2 = Player(username=f"player_{uuid.uuid4().hex[:8]}", is_guest=False)
        test_db.add(player2)
        await test_db.commit()
        await test_db.refresh(player2)
        
        # Create non-owner participant
        non_owner_participant = GameRoomParticipant(
            id=str(uuid.uuid4()),
            game_room_id=room.id,
            player_id=player2.id,
            is_ai_agent=False,
            is_owner=False,
            joined_at=datetime.now(timezone.utc),
            join_timestamp=datetime.now(timezone.utc),
            replaced_by_ai=False
        )
        test_db.add(non_owner_participant)
        await test_db.commit()
        
        # Verify is_owner flags
        await test_db.refresh(owner_participant)
        await test_db.refresh(non_owner_participant)
        
        assert owner_participant.is_owner is True
        assert non_owner_participant.is_owner is False

    async def test_join_timestamp_set_on_creation(
        self,
        test_db: AsyncSession,
        sample_game_type: GameType,
        sample_player: Player
    ):
        """Test that join_timestamp is set to current time on participant creation."""
        # Create room
        room = GameRoom(
            id=str(uuid.uuid4()),
            code="TIME01",
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
        
        # Create participant with explicit join_timestamp
        join_time = datetime.now(timezone.utc)
        participant = GameRoomParticipant(
            id=str(uuid.uuid4()),
            game_room_id=room.id,
            player_id=sample_player.id,
            is_ai_agent=False,
            is_owner=True,
            joined_at=join_time,
            join_timestamp=join_time,
            replaced_by_ai=False
        )
        test_db.add(participant)
        await test_db.commit()
        await test_db.refresh(participant)
        
        # Verify timestamp is set
        assert participant.join_timestamp is not None
        # Verify it's close to the join_time we set (within 1 second)
        time_diff = abs((participant.join_timestamp.replace(tzinfo=timezone.utc) - join_time).total_seconds())
        assert time_diff < 1.0

    async def test_unique_constraint_prevents_duplicate_joins(
        self,
        test_db: AsyncSession,
        sample_game_type: GameType,
        sample_player: Player
    ):
        """Test that unique constraint prevents duplicate (room_id, player_id) combinations."""
        # Create room
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
        
        # Create first participant
        participant1 = GameRoomParticipant(
            id=str(uuid.uuid4()),
            game_room_id=room.id,
            player_id=sample_player.id,
            is_ai_agent=False,
            is_owner=True,
            joined_at=datetime.now(timezone.utc),
            join_timestamp=datetime.now(timezone.utc),
            replaced_by_ai=False
        )
        test_db.add(participant1)
        await test_db.commit()
        
        # Attempt to create duplicate participant
        participant2 = GameRoomParticipant(
            id=str(uuid.uuid4()),
            game_room_id=room.id,
            player_id=sample_player.id,  # Same player, same room
            is_ai_agent=False,
            is_owner=False,
            joined_at=datetime.now(timezone.utc),
            join_timestamp=datetime.now(timezone.utc),
            replaced_by_ai=False
        )
        test_db.add(participant2)
        
        # Should raise IntegrityError due to unique constraint
        with pytest.raises(IntegrityError):
            await test_db.commit()

    async def test_query_ordering_by_join_timestamp(
        self,
        test_db: AsyncSession,
        sample_game_type: GameType,
        sample_player: Player
    ):
        """Test that querying participants ordered by join_timestamp returns correct order."""
        # Create room
        room = GameRoom(
            id=str(uuid.uuid4()),
            code="ORD001",
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
        
        # Create players
        player1 = sample_player
        player2 = Player(username=f"player2_{uuid.uuid4().hex[:8]}", is_guest=False)
        player3 = Player(username=f"player3_{uuid.uuid4().hex[:8]}", is_guest=False)
        test_db.add_all([player2, player3])
        await test_db.commit()
        
        # Create participants with different join times
        now = datetime.now(timezone.utc)
        
        participant1 = GameRoomParticipant(
            id=str(uuid.uuid4()),
            game_room_id=room.id,
            player_id=player1.id,
            is_ai_agent=False,
            is_owner=True,
            joined_at=now,
            join_timestamp=now,
            replaced_by_ai=False
        )
        
        participant2 = GameRoomParticipant(
            id=str(uuid.uuid4()),
            game_room_id=room.id,
            player_id=player2.id,
            is_ai_agent=False,
            is_owner=False,
            joined_at=now + timedelta(seconds=10),
            join_timestamp=now + timedelta(seconds=10),
            replaced_by_ai=False
        )
        
        participant3 = GameRoomParticipant(
            id=str(uuid.uuid4()),
            game_room_id=room.id,
            player_id=player3.id,
            is_ai_agent=False,
            is_owner=False,
            joined_at=now + timedelta(seconds=20),
            join_timestamp=now + timedelta(seconds=20),
            replaced_by_ai=False
        )
        
        test_db.add_all([participant1, participant2, participant3])
        await test_db.commit()
        
        # Query participants ordered by join_timestamp
        result = await test_db.execute(
            select(GameRoomParticipant)
            .where(GameRoomParticipant.game_room_id == room.id)
            .order_by(GameRoomParticipant.join_timestamp.asc())
        )
        ordered_participants = result.scalars().all()
        
        # Verify order
        assert len(ordered_participants) == 3
        assert ordered_participants[0].player_id == player1.id
        assert ordered_participants[1].player_id == player2.id
        assert ordered_participants[2].player_id == player3.id
