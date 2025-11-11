"""Integration tests for GameRoomService.leave_room method."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.game_room import GameRoom
from src.models.game_room_participant import GameRoomParticipant
from src.models.player import Player
from src.services.game_room_service import GameRoomService
from src.utils.errors import GameAlreadyStartedError, NotFoundError


@pytest.fixture
async def service(test_db: AsyncSession):
    """Create GameRoomService instance."""
    return GameRoomService(test_db)


@pytest.fixture
async def room_with_participants(test_db: AsyncSession, sample_game_type):
    """Create room with owner and two other players."""
    # Create players
    owner = Player(id="leave-owner", username="LeaveOwner", is_guest=True)
    player2 = Player(id="leave-p2", username="LeaveP2", is_guest=True)
    player3 = Player(id="leave-p3", username="LeaveP3", is_guest=True)
    test_db.add_all([owner, player2, player3])
    
    # Create room
    room = GameRoom(
        code="LEAVESVC",
        status="Waiting",
        max_players=4,
        min_players=2,
        game_type_id=sample_game_type.id,
        owner_id=owner.id,
        current_participant_count=3,
        ai_agent_counter=0
    )
    test_db.add(room)
    await test_db.flush()
    
    # Add participants
    for player_id, is_owner in [(owner.id, True), (player2.id, False), (player3.id, False)]:
        participant = GameRoomParticipant(
            game_room_id=room.id,
            player_id=player_id,
            is_owner=is_owner,
            is_ai_agent=False
        )
        test_db.add(participant)
    
    await test_db.commit()
    await test_db.refresh(room)
    return room, owner, player2, player3


@pytest.mark.asyncio
class TestLeaveRoomService:
    """Test leave_room service method."""
    
    async def test_leave_room_removes_participant_record(
        self, service, room_with_participants
    ):
        """Test participant record is marked as left (soft delete via left_at timestamp)."""
        room, owner, player2, _ = room_with_participants
        
        await service.leave_room(room.code, player2.id)
        
        # Verify participant has left_at set
        result = await service.db.execute(
            select(GameRoomParticipant).where(
                GameRoomParticipant.game_room_id == room.id,
                GameRoomParticipant.player_id == player2.id
            )
        )
        participant = result.scalar_one()
        assert participant.left_at is not None, "Participant should have left_at timestamp"
    
    async def test_leave_room_decrements_participant_count(
        self, service, room_with_participants
    ):
        """Test current_participant_count is decremented."""
        room, owner, player2, _ = room_with_participants
        initial_count = room.current_participant_count
        
        await service.leave_room(room.code, player2.id)
        
        # Reload room
        result = await service.db.execute(
            select(GameRoom).where(GameRoom.code == room.code)
        )
        updated_room = result.scalar_one()
        assert updated_room.current_participant_count == initial_count - 1
    
    async def test_non_owner_leave_does_not_transfer_ownership(
        self, service, room_with_participants
    ):
        """Test non-owner leaving doesn't change ownership."""
        room, owner, player2, _ = room_with_participants
        
        await service.leave_room(room.code, player2.id)
        
        # Verify owner unchanged
        result = await service.db.execute(
            select(GameRoom).where(GameRoom.code == room.code)
        )
        updated_room = result.scalar_one()
        assert updated_room.owner_id == owner.id
    
    async def test_owner_leave_transfers_ownership_to_next_human(
        self, service, room_with_participants
    ):
        """Test owner leaving transfers ownership to oldest human participant (FR-014)."""
        room, owner, player2, player3 = room_with_participants
        
        await service.leave_room(room.code, owner.id)
        
        # Verify ownership transferred
        result = await service.db.execute(
            select(GameRoom).where(GameRoom.code == room.code)
        )
        updated_room = result.scalar_one()
        # Should transfer to player2 (oldest remaining human)
        assert updated_room.owner_id == player2.id
        
        # Verify participant records updated
        result = await service.db.execute(
            select(GameRoomParticipant).where(
                GameRoomParticipant.game_room_id == room.id,
                GameRoomParticipant.player_id == player2.id
            )
        )
        new_owner_participant = result.scalar_one()
        assert new_owner_participant.is_owner is True
    
    async def test_owner_leave_with_only_ai_dissolves_room(
        self, test_db, service, sample_game_type
    ):
        """Test owner leaving AI-only room dissolves it (FR-014)."""
        # Create owner and AI agent
        owner = Player(id="ai-owner", username="AIOwner", is_guest=True)
        ai_player = Player(id="ai-player", username="AI_Agent_1", is_guest=False)
        test_db.add_all([owner, ai_player])
        
        # Create room
        room = GameRoom(
            code="AIONLY",
            status="Waiting",
            max_players=4,
            min_players=2,
            game_type_id=sample_game_type.id,
            owner_id=owner.id,
            current_participant_count=2,
            ai_agent_counter=1
        )
        test_db.add(room)
        await test_db.flush()
        
        # Add participants
        owner_participant = GameRoomParticipant(
            game_room_id=room.id,
            player_id=owner.id,
            is_owner=True,
            is_ai_agent=False
        )
        ai_participant = GameRoomParticipant(
            game_room_id=room.id,
            player_id=ai_player.id,
            is_owner=False,
            is_ai_agent=True
        )
        test_db.add_all([owner_participant, ai_participant])
        await test_db.commit()
        await test_db.refresh(room)
        
        await service.leave_room(room.code, owner.id)
        
        # Room should be dissolved (status = Dissolved or deleted)
        result = await service.db.execute(
            select(GameRoom).where(GameRoom.code == room.code)
        )
        dissolved_room = result.scalar_one_or_none()
        
        # Either room deleted or marked as Dissolved
        if dissolved_room:
            assert dissolved_room.status == "Dissolved", "AI-only room should be dissolved"
        else:
            # Room was deleted - also acceptable
            pass
    
    async def test_leave_nonexistent_room_raises_error(
        self, service
    ):
        """Test leaving nonexistent room raises NotFoundError."""
        with pytest.raises(NotFoundError, match="not found"):
            await service.leave_room("NOEXIST", "any-player")
    
    async def test_leave_when_not_participant_raises_error(
        self, service, room_with_participants, test_db
    ):
        """Test leaving when not in room raises NotFoundError."""
        room, *_ = room_with_participants
        
        # Create non-participant player
        outsider = Player(id="outsider", username="Outsider", is_guest=True)
        test_db.add(outsider)
        await test_db.commit()
        
        with pytest.raises(NotFoundError, match="Not in this room"):
            await service.leave_room(room.code, outsider.id)
    
    async def test_leave_in_progress_game_raises_error(
        self, test_db, service, sample_game_type
    ):
        """Test leaving in-progress game raises GameAlreadyStartedError."""
        # Create player and room
        player = Player(id="in-prog-p", username="InProgPlayer", is_guest=True)
        test_db.add(player)
        
        room = GameRoom(
            code="INPROG",
            status="InProgress",
            max_players=4,
            min_players=2,
            game_type_id=sample_game_type.id,
            owner_id=player.id,
            current_participant_count=1,
            ai_agent_counter=0
        )
        test_db.add(room)
        await test_db.flush()
        
        participant = GameRoomParticipant(
            game_room_id=room.id,
            player_id=player.id,
            is_owner=True,
            is_ai_agent=False
        )
        test_db.add(participant)
        await test_db.commit()
        
        with pytest.raises(GameAlreadyStartedError, match="Cannot leave"):
            await service.leave_room(room.code, player.id)
