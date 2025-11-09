"""Unit tests for GameRoom, GameRoomParticipant, and GameState models."""
import pytest
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models.game_room import GameRoom
from src.models.game_room_participant import GameRoomParticipant
from src.models.game_state import GameState


@pytest.mark.asyncio
class TestGameRoomModel:
    """Test GameRoom model."""
    
    async def test_create_game_room(self, test_db, sample_game_type, sample_player):
        """Test creating a game room."""
        room = GameRoom(
            code="ABCD1234",
            game_type_id=sample_game_type.id,
            status="Waiting",
            max_players=6,
            min_players=4,
            created_by=sample_player.id
        )
        test_db.add(room)
        await test_db.commit()
        await test_db.refresh(room)
        
        assert room.id is not None
        assert room.code == "ABCD1234"
        assert room.status == "Waiting"
        assert room.max_players == 6
        assert room.min_players == 4
        assert room.created_by == sample_player.id
    
    async def test_can_join_waiting_room(self, test_db, sample_game_room):
        """Test that players can join waiting rooms."""
        assert sample_game_room.can_join() is True
    
    async def test_cannot_join_in_progress_room(self, test_db, sample_game_room):
        """Test that players cannot join in-progress rooms."""
        sample_game_room.status = "In Progress"
        await test_db.commit()
        
        assert sample_game_room.can_join() is False
    
    async def test_cannot_join_completed_room(self, test_db, sample_game_room):
        """Test that players cannot join completed rooms."""
        sample_game_room.status = "Completed"
        await test_db.commit()
        
        assert sample_game_room.can_join() is False
    
    async def test_is_ready_to_start_with_enough_players(
        self, test_db, sample_game_room, sample_player, sample_guest_player
    ):
        """Test room is ready when min players reached."""
        # Add participants to reach min_players (4)
        for i, player in enumerate([sample_player, sample_guest_player]):
            participant = GameRoomParticipant(
                game_room_id=sample_game_room.id,
                player_id=player.id,
                is_ai_agent=False
            )
            test_db.add(participant)
        
        # Add 2 AI agents
        for i in range(2):
            participant = GameRoomParticipant(
                game_room_id=sample_game_room.id,
                player_id=None,
                is_ai_agent=True,
                ai_personality="detective"
            )
            test_db.add(participant)
        
        await test_db.commit()
        
        # Reload room with participants to avoid lazy loading issues
        result = await test_db.execute(
            select(GameRoom)
            .where(GameRoom.id == sample_game_room.id)
            .options(selectinload(GameRoom.participants))
        )
        room_with_participants = result.scalar_one()
        
        # Check if room is ready to start
        count = room_with_participants.get_active_participants_count()
        assert count >= sample_game_room.min_players
        assert room_with_participants.is_ready_to_start() is True
    
    async def test_not_ready_with_few_players(self, test_db, sample_game_room, sample_player):
        """Test room not ready with too few players."""
        # Add only 1 participant (min is 4)
        participant = GameRoomParticipant(
            game_room_id=sample_game_room.id,
            player_id=sample_player.id,
            is_ai_agent=False
        )
        test_db.add(participant)
        await test_db.commit()
        
        # Reload room with participants
        result = await test_db.execute(
            select(GameRoom)
            .where(GameRoom.id == sample_game_room.id)
            .options(selectinload(GameRoom.participants))
        )
        room_with_participants = result.scalar_one()
        
        count = room_with_participants.get_active_participants_count()
        assert room_with_participants.is_ready_to_start() is False
    
    async def test_room_status_transitions(self, test_db, sample_game_room):
        """Test room status transitions."""
        assert sample_game_room.status == "Waiting"
        
        sample_game_room.status = "In Progress"
        await test_db.commit()
        assert sample_game_room.status == "In Progress"
        
        sample_game_room.status = "Completed"
        sample_game_room.ended_at = datetime.utcnow()
        await test_db.commit()
        assert sample_game_room.status == "Completed"
        assert sample_game_room.ended_at is not None


@pytest.mark.asyncio
class TestGameRoomParticipantModel:
    """Test GameRoomParticipant model."""
    
    async def test_create_human_participant(self, test_db, sample_game_room, sample_player):
        """Test creating a human player participant."""
        participant = GameRoomParticipant(
            game_room_id=sample_game_room.id,
            player_id=sample_player.id,
            is_ai_agent=False,
        )
        test_db.add(participant)
        await test_db.commit()
        await test_db.refresh(participant)
        
        assert participant.id is not None
        assert participant.game_room_id == sample_game_room.id
        assert participant.player_id == sample_player.id
        assert participant.is_ai_agent is False
        assert participant.joined_at is not None
        assert participant.left_at is None
    
    async def test_create_ai_participant(self, test_db, sample_game_room):
        """Test creating an AI agent participant."""
        participant = GameRoomParticipant(
            game_room_id=sample_game_room.id,
            player_id=None,
            is_ai_agent=True,
            ai_personality="detective",
        )
        test_db.add(participant)
        await test_db.commit()
        await test_db.refresh(participant)
        
        assert participant.id is not None
        assert participant.player_id is None
        assert participant.is_ai_agent is True
        assert participant.ai_personality == "detective"
    
    async def test_is_active_participant(self, test_db, sample_game_room, sample_player):
        """Test active participant check."""
        participant = GameRoomParticipant(
            game_room_id=sample_game_room.id,
            player_id=sample_player.id,
            is_ai_agent=False,
        )
        test_db.add(participant)
        await test_db.commit()
        
        assert participant.is_active() is True
    
    async def test_leave_participant(self, test_db, sample_game_room, sample_player):
        """Test leaving a game room."""
        participant = GameRoomParticipant(
            game_room_id=sample_game_room.id,
            player_id=sample_player.id,
            is_ai_agent=False,
        )
        test_db.add(participant)
        await test_db.commit()
        
        participant.leave()
        await test_db.commit()
        
        assert participant.left_at is not None
        assert participant.is_active() is False
    
    async def test_replaced_by_ai(self, test_db, sample_game_room, sample_player):
        """Test participant replaced by AI."""
        participant = GameRoomParticipant(
            game_room_id=sample_game_room.id,
            player_id=sample_player.id,
            is_ai_agent=False,
        )
        test_db.add(participant)
        await test_db.commit()
        
        participant.replaced_by_ai = True
        await test_db.commit()
        
        assert participant.replaced_by_ai is True


@pytest.mark.asyncio
class TestGameStateModel:
    """Test GameState model."""
    
    async def test_create_game_state(self, test_db, sample_game_room, sample_player):
        """Test creating game state."""
        game_state = GameState(
            game_room_id=sample_game_room.id,
            current_phase="setup",
            turn_number=1,
            current_turn_player_id=sample_player.id,
            game_data='{"clues": [], "accusations": []}'
        )
        test_db.add(game_state)
        await test_db.commit()
        await test_db.refresh(game_state)
        
        assert game_state.id is not None
        assert game_state.game_room_id == sample_game_room.id
        assert game_state.current_phase == "setup"
        assert game_state.current_turn_player_id == sample_player.id
        assert game_state.turn_number == 1
        assert '"clues"' in game_state.game_data
    
    async def test_update_game_state(self, test_db, sample_game_room, sample_player):
        """Test updating game state."""
        game_state = GameState(
            game_room_id=sample_game_room.id,
            current_phase="setup",
            turn_number=1,
            current_turn_player_id=sample_player.id,
            game_data="{}"
        )
        test_db.add(game_state)
        await test_db.commit()
        
        game_state.current_phase = "investigation"
        game_state.turn_number = 2
        game_state.game_data = '{"clues": ["线索1"]}'
        await test_db.commit()
        await test_db.refresh(game_state)
        
        assert game_state.current_phase == "investigation"
        assert game_state.turn_number == 2
        assert "线索1" in game_state.game_data
