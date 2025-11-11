"""Test fixtures for room scenarios.

Provides pre-configured room setups for testing multiplayer join and AI agent management.
"""
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.game_room import GameRoom
from src.models.game_room_participant import GameRoomParticipant
from src.models.player import Player


@pytest_asyncio.fixture
async def room_with_owner(db_session: AsyncSession) -> AsyncGenerator[dict, None]:
    """Create a room with a single human player as owner.
    
    Returns:
        dict with keys: room (GameRoom), owner (Player)
    """
    # Create owner player
    owner = Player(
        id=str(uuid.uuid4()),
        username=f"owner_{uuid.uuid4().hex[:8]}",
        email=f"owner_{uuid.uuid4().hex[:8]}@test.com"
    )
    db_session.add(owner)
    
    # Create room
    room = GameRoom(
        id=str(uuid.uuid4()),
        code=f"TEST{uuid.uuid4().hex[:4].upper()}",
        game_type_id=str(uuid.uuid4()),
        status="waiting",
        max_players=6,
        min_players=3,
        owner_id=owner.id,
        created_by=owner.id,
        current_participant_count=1,
        ai_agent_counter=0,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(room)
    
    # Create participant entry for owner
    participant = GameRoomParticipant(
        id=str(uuid.uuid4()),
        game_room_id=room.id,
        player_id=owner.id,
        is_ai_agent=False,
        is_owner=True,
        joined_at=datetime.now(timezone.utc),
        join_timestamp=datetime.now(timezone.utc),
        replaced_by_ai=False
    )
    db_session.add(participant)
    
    await db_session.commit()
    await db_session.refresh(room)
    await db_session.refresh(owner)
    
    yield {"room": room, "owner": owner}
    
    # Cleanup handled by db_session fixture rollback


@pytest_asyncio.fixture
async def room_with_multiple_humans(db_session: AsyncSession) -> AsyncGenerator[dict, None]:
    """Create a room with owner and 2 non-owner human players.
    
    Returns:
        dict with keys: room (GameRoom), owner (Player), players (list[Player])
    """
    # Create owner
    owner = Player(
        id=str(uuid.uuid4()),
        username=f"owner_{uuid.uuid4().hex[:8]}",
        email=f"owner_{uuid.uuid4().hex[:8]}@test.com"
    )
    db_session.add(owner)
    
    # Create 2 additional players
    players = []
    for i in range(2):
        player = Player(
            id=str(uuid.uuid4()),
            username=f"player{i}_{uuid.uuid4().hex[:8]}",
            email=f"player{i}_{uuid.uuid4().hex[:8]}@test.com"
        )
        db_session.add(player)
        players.append(player)
    
    # Create room
    room = GameRoom(
        id=str(uuid.uuid4()),
        code=f"MULT{uuid.uuid4().hex[:4].upper()}",
        game_type_id=str(uuid.uuid4()),
        status="waiting",
        max_players=6,
        min_players=3,
        owner_id=owner.id,
        created_by=owner.id,
        current_participant_count=3,
        ai_agent_counter=0,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(room)
    
    # Create participant entries
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
    db_session.add(owner_participant)
    
    for player in players:
        participant = GameRoomParticipant(
            id=str(uuid.uuid4()),
            game_room_id=room.id,
            player_id=player.id,
            is_ai_agent=False,
            is_owner=False,
            joined_at=datetime.now(timezone.utc),
            join_timestamp=datetime.now(timezone.utc),
            replaced_by_ai=False
        )
        db_session.add(participant)
    
    await db_session.commit()
    await db_session.refresh(room)
    await db_session.refresh(owner)
    for player in players:
        await db_session.refresh(player)
    
    yield {"room": room, "owner": owner, "players": players}


@pytest_asyncio.fixture
async def room_with_ai_agents(db_session: AsyncSession) -> AsyncGenerator[dict, None]:
    """Create a room with owner and 2 AI agents.
    
    Returns:
        dict with keys: room (GameRoom), owner (Player), ai_agents (list[GameRoomParticipant])
    """
    # Create owner
    owner = Player(
        id=str(uuid.uuid4()),
        username=f"owner_{uuid.uuid4().hex[:8]}",
        email=f"owner_{uuid.uuid4().hex[:8]}@test.com"
    )
    db_session.add(owner)
    
    # Create room
    room = GameRoom(
        id=str(uuid.uuid4()),
        code=f"AIAG{uuid.uuid4().hex[:4].upper()}",
        game_type_id=str(uuid.uuid4()),
        status="waiting",
        max_players=6,
        min_players=3,
        owner_id=owner.id,
        created_by=owner.id,
        current_participant_count=3,
        ai_agent_counter=2,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(room)
    
    # Create owner participant
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
    db_session.add(owner_participant)
    
    # Create 2 AI agent participants
    ai_agents = []
    for i in range(2):
        ai_participant = GameRoomParticipant(
            id=str(uuid.uuid4()),
            game_room_id=room.id,
            player_id=None,  # AI agents don't have player_id
            is_ai_agent=True,
            ai_personality="strategic" if i == 0 else "analytical",
            is_owner=False,
            joined_at=datetime.now(timezone.utc),
            join_timestamp=datetime.now(timezone.utc),
            replaced_by_ai=False
        )
        db_session.add(ai_participant)
        ai_agents.append(ai_participant)
    
    await db_session.commit()
    await db_session.refresh(room)
    await db_session.refresh(owner)
    for agent in ai_agents:
        await db_session.refresh(agent)
    
    yield {"room": room, "owner": owner, "ai_agents": ai_agents}


@pytest_asyncio.fixture
async def room_at_capacity(db_session: AsyncSession) -> AsyncGenerator[dict, None]:
    """Create a room at max capacity (max_players participants).
    
    Returns:
        dict with keys: room (GameRoom), owner (Player), players (list[Player])
    """
    max_players = 6
    
    # Create owner
    owner = Player(
        id=str(uuid.uuid4()),
        username=f"owner_{uuid.uuid4().hex[:8]}",
        email=f"owner_{uuid.uuid4().hex[:8]}@test.com"
    )
    db_session.add(owner)
    
    # Create additional players (max_players - 1)
    players = []
    for i in range(max_players - 1):
        player = Player(
            id=str(uuid.uuid4()),
            username=f"player{i}_{uuid.uuid4().hex[:8]}",
            email=f"player{i}_{uuid.uuid4().hex[:8]}@test.com"
        )
        db_session.add(player)
        players.append(player)
    
    # Create room at capacity
    room = GameRoom(
        id=str(uuid.uuid4()),
        code=f"FULL{uuid.uuid4().hex[:4].upper()}",
        game_type_id=str(uuid.uuid4()),
        status="waiting",
        max_players=max_players,
        min_players=3,
        owner_id=owner.id,
        created_by=owner.id,
        current_participant_count=max_players,
        ai_agent_counter=0,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(room)
    
    # Create owner participant
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
    db_session.add(owner_participant)
    
    # Create participant entries for all players
    for player in players:
        participant = GameRoomParticipant(
            id=str(uuid.uuid4()),
            game_room_id=room.id,
            player_id=player.id,
            is_ai_agent=False,
            is_owner=False,
            joined_at=datetime.now(timezone.utc),
            join_timestamp=datetime.now(timezone.utc),
            replaced_by_ai=False
        )
        db_session.add(participant)
    
    await db_session.commit()
    await db_session.refresh(room)
    await db_session.refresh(owner)
    for player in players:
        await db_session.refresh(player)
    
    yield {"room": room, "owner": owner, "players": players}
