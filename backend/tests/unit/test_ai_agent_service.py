"""Tests for AI Agent service."""
import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.services.ai_service import AIAgentService, AI_PERSONALITIES
from src.models.game import GameRoom, GameRoomParticipant


@pytest.mark.asyncio
class TestAIAgentService:
    """Test AI Agent service operations."""
    
    async def test_fill_empty_slots_basic(
        self, test_db, sample_game_room, sample_player
    ):
        """Test filling empty slots with AI agents."""
        service = AIAgentService(test_db)
        
        # Reload room with participants relationship
        await test_db.refresh(sample_game_room, ['participants'])
        
        # Room has 1 player, min_players=4, should add 3 AI agents
        assert sample_game_room.get_active_participants_count() == 1
        assert sample_game_room.min_players == 4
        
        ai_participants = await service.fill_empty_slots(sample_game_room)
        
        # Should create 3 AI agents
        assert len(ai_participants) == 3
        
        # Verify all are AI agents
        for participant in ai_participants:
            assert participant.is_ai_agent is True
            assert participant.player_id is None
            assert participant.ai_personality in AI_PERSONALITIES
        
        # Verify personalities are different (cycling through list)
        personalities = [p.ai_personality for p in ai_participants]
        assert personalities[0] == AI_PERSONALITIES[0]
        assert personalities[1] == AI_PERSONALITIES[1]
        assert personalities[2] == AI_PERSONALITIES[2]
    
    async def test_fill_empty_slots_no_need(
        self, test_db, sample_game_room, sample_player, sample_guest_player
    ):
        """Test fill when room already has enough players."""
        service = AIAgentService(test_db)
        
        # Add more participants to reach min_players
        for i in range(3):
            participant = GameRoomParticipant(
                game_room_id=sample_game_room.id,
                player_id=sample_guest_player.id if i == 0 else None,
                is_ai_agent=i > 0,
                ai_personality=AI_PERSONALITIES[i] if i > 0 else None
            )
            test_db.add(participant)
        await test_db.commit()
        await test_db.refresh(sample_game_room, ['participants'])
        
        # Now room has 4 players (1 original + 1 guest + 2 AI)
        assert sample_game_room.get_active_participants_count() == 4
        
        ai_participants = await service.fill_empty_slots(sample_game_room)
        
        # Should not create any AI agents
        assert len(ai_participants) == 0
    
    async def test_fill_empty_slots_personality_cycling(
        self, test_db, sample_game_type, sample_player
    ):
        """Test personality cycling when filling many slots."""
        # Create a room with high min_players to test personality cycling
        room = GameRoom(
            code="CYCLE123",
            game_type_id=sample_game_type.id,
            status="Waiting",
            max_players=10,
            min_players=9,  # Need 8 AI agents
            created_by=sample_player.id
        )
        test_db.add(room)
        await test_db.flush()
        
        # Add creator as participant
        creator_participant = GameRoomParticipant(
            game_room_id=room.id,
            player_id=sample_player.id,
            is_ai_agent=False
        )
        test_db.add(creator_participant)
        await test_db.commit()
        
        # Reload with relationships
        stmt = select(GameRoom).where(GameRoom.code == "CYCLE123").options(
            selectinload(GameRoom.participants)
        )
        result = await test_db.execute(stmt)
        room = result.scalar_one()
        
        service = AIAgentService(test_db)
        ai_participants = await service.fill_empty_slots(room)
        
        # Should create 8 AI agents
        assert len(ai_participants) == 8
        
        # Verify personality cycling (6 personalities, should cycle twice)
        personalities = [p.ai_personality for p in ai_participants]
        assert personalities[0] == AI_PERSONALITIES[0]
        assert personalities[5] == AI_PERSONALITIES[5]
        assert personalities[6] == AI_PERSONALITIES[0]  # Cycles back
        assert personalities[7] == AI_PERSONALITIES[1]
    
    async def test_fill_empty_slots_persists_to_db(
        self, test_db, sample_game_room
    ):
        """Test that AI participants are actually saved to database."""
        # Reload with participants
        await test_db.refresh(sample_game_room, ['participants'])
        
        service = AIAgentService(test_db)
        
        initial_count = sample_game_room.get_active_participants_count()
        await service.fill_empty_slots(sample_game_room)
        
        # Query database to verify persistence
        stmt = select(GameRoomParticipant).where(
            GameRoomParticipant.game_room_id == sample_game_room.id,
            GameRoomParticipant.is_ai_agent == True
        )
        result = await test_db.execute(stmt)
        ai_agents = result.scalars().all()
        
        expected_count = sample_game_room.min_players - initial_count
        assert len(ai_agents) == expected_count
    
    async def test_replace_disconnected_player(
        self, test_db, sample_game_room, sample_guest_player
    ):
        """Test replacing a disconnected player with AI."""
        service = AIAgentService(test_db)
        
        # Add a guest participant and mark as left
        guest_participant = GameRoomParticipant(
            game_room_id=sample_game_room.id,
            player_id=sample_guest_player.id,
            is_ai_agent=False
        )
        test_db.add(guest_participant)
        await test_db.commit()
        
        # Mark player as left
        guest_participant.leave()
        await test_db.commit()
        await test_db.refresh(sample_game_room, ['participants'])
        
        # Replace with AI
        ai_participant = await service.replace_disconnected_player(
            sample_game_room, 
            sample_guest_player.id
        )
        
        # Verify AI was created
        assert ai_participant.is_ai_agent is True
        assert ai_participant.player_id is None
        assert ai_participant.ai_personality in AI_PERSONALITIES
        
        # Verify original participant is marked as replaced
        await test_db.refresh(guest_participant)
        assert guest_participant.replaced_by_ai is True
    
    async def test_replace_disconnected_player_not_found(
        self, test_db, sample_game_room
    ):
        """Test replacing a player that doesn't exist."""
        service = AIAgentService(test_db)
        
        # Reload with participants
        await test_db.refresh(sample_game_room, ['participants'])
        
        # Try to replace non-existent player
        ai_participant = await service.replace_disconnected_player(
            sample_game_room, 
            "nonexistent-player-id"
        )
        
        # Should still create AI agent (graceful handling)
        assert ai_participant.is_ai_agent is True
        assert ai_participant.player_id is None
    
    async def test_ai_personality_types_defined(self):
        """Test that AI personalities are properly defined."""
        # Verify all personalities are strings
        for personality in AI_PERSONALITIES:
            assert isinstance(personality, str)
            assert len(personality) > 0
        
        # Verify we have expected personalities
        assert "analytical_detective" in AI_PERSONALITIES
        assert "intuitive_investigator" in AI_PERSONALITIES
        assert "cautious_observer" in AI_PERSONALITIES
        assert "bold_risk_taker" in AI_PERSONALITIES
        assert "strategic_thinker" in AI_PERSONALITIES
        assert "empathetic_listener" in AI_PERSONALITIES
        
        # Verify we have 6 personalities
        assert len(AI_PERSONALITIES) == 6
