"""Unit tests for GameRoomService AI agent creation.

Tests for Phase 2 Feature 002: AI agent management.
"""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.game import GameRoom, GameType
from src.models.user import Player
from src.services.game_room_service import GameRoomService


@pytest.mark.asyncio
class TestGameRoomServiceAI:
    """Test GameRoomService AI agent creation logic."""

    async def test_create_ai_agent_generates_sequential_names(
        self,
        test_db: AsyncSession,
        sample_game_type: GameType,
        sample_player: Player
    ):
        """Test that create_ai_agent generates sequential AI names (FR-007)."""
        # Create room
        room = GameRoom(
            id=str(uuid.uuid4()),
            code="AISEQ1",
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
        
        service = GameRoomService(test_db)
        
        # Create first AI agent
        player1 = await service.create_ai_agent(room.id)
        assert player1.username == "AI玩家1"
        
        # Refresh room to see updated counter
        await test_db.refresh(room)
        assert room.ai_agent_counter == 1
        
        # Create second AI agent
        player2 = await service.create_ai_agent(room.id)
        assert player2.username == "AI玩家2"
        
        await test_db.refresh(room)
        assert room.ai_agent_counter == 2
        
        # Create third AI agent
        player3 = await service.create_ai_agent(room.id)
        assert player3.username == "AI玩家3"
        
        await test_db.refresh(room)
        assert room.ai_agent_counter == 3

    async def test_create_ai_agent_creates_player_with_ai_type(
        self,
        test_db: AsyncSession,
        sample_game_type: GameType,
        sample_player: Player
    ):
        """Test that create_ai_agent creates Player with is_guest=True (AI marker)."""
        # Create room
        room = GameRoom(
            id=str(uuid.uuid4()),
            code="AITYPE",
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
        
        service = GameRoomService(test_db)
        
        # Create AI agent
        ai_player = await service.create_ai_agent(room.id)
        
        # Verify it's marked as AI (using is_guest as marker since no player_type field)
        assert ai_player.username.startswith("AI玩家")
        # AI players should be created with is_guest=True for auto-cleanup
        assert ai_player.is_guest is True

    async def test_create_ai_agent_adds_participant_with_ai_flag(
        self,
        test_db: AsyncSession,
        sample_game_type: GameType,
        sample_player: Player
    ):
        """Test that create_ai_agent adds GameRoomParticipant with is_ai_agent=True."""
        # Create room
        room = GameRoom(
            id=str(uuid.uuid4()),
            code="AIPART",
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
        
        service = GameRoomService(test_db)
        
        # Create AI agent
        ai_player = await service.create_ai_agent(room.id)
        
        # Reload room with participants
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        result = await test_db.execute(
            select(GameRoom)
            .where(GameRoom.id == room.id)
            .options(selectinload(GameRoom.participants))
        )
        room = result.scalar_one()
        
        # Find the AI participant
        ai_participant = None
        for p in room.participants:
            if p.player_id == ai_player.id:
                ai_participant = p
                break
        
        assert ai_participant is not None
        assert ai_participant.is_ai_agent is True
        assert ai_participant.is_owner is False

    async def test_create_ai_agent_increments_counter(
        self,
        test_db: AsyncSession,
        sample_game_type: GameType,
        sample_player: Player
    ):
        """Test that create_ai_agent increments room.ai_agent_counter."""
        # Create room
        room = GameRoom(
            id=str(uuid.uuid4()),
            code="AICNT",
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
        
        service = GameRoomService(test_db)
        
        # Initial counter
        assert room.ai_agent_counter == 0
        
        # Create AI agents and verify counter increments
        await service.create_ai_agent(room.id)
        await test_db.refresh(room)
        assert room.ai_agent_counter == 1
        
        await service.create_ai_agent(room.id)
        await test_db.refresh(room)
        assert room.ai_agent_counter == 2
        
        await service.create_ai_agent(room.id)
        await test_db.refresh(room)
        assert room.ai_agent_counter == 3

    async def test_create_ai_agent_returns_player_object(
        self,
        test_db: AsyncSession,
        sample_game_type: GameType,
        sample_player: Player
    ):
        """Test that create_ai_agent returns a properly created Player object."""
        # Create room
        room = GameRoom(
            id=str(uuid.uuid4()),
            code="AIRET",
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
        
        service = GameRoomService(test_db)
        
        # Create AI agent
        ai_player = await service.create_ai_agent(room.id)
        
        # Verify return value
        assert ai_player is not None
        assert isinstance(ai_player, Player)
        assert ai_player.id is not None
        assert ai_player.username == "AI玩家1"
        assert ai_player.is_guest is True
