"""Pytest configuration and fixtures."""
import asyncio
import os
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from src.models.base import Base
from src.models.user import Player, PlayerProfile
from src.models.game import GameRoom, GameRoomParticipant, GameState
from src.constants import GAME_TYPES, get_game_type_by_slug


# Set test API key for AI (prefer AI_API_KEY, fallback to OPENAI_API_KEY for compatibility)
os.environ["AI_API_KEY"] = "sk-test-key-for-testing"
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "sk-test-key-for-testing")

# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Enable foreign keys for SQLite
        await conn.execute(text("PRAGMA foreign_keys=ON"))
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def test_db(test_engine):
    """Create a test database session."""
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def sample_game_type():
    """Return a sample game type from constants for testing."""
    game_type = get_game_type_by_slug("werewolf")
    return game_type


@pytest.fixture
async def sample_player(test_db: AsyncSession):
    """Create a sample player for testing."""
    player = Player(
        username="test_player_001",
        is_guest=False
    )
    test_db.add(player)
    await test_db.commit()
    await test_db.refresh(player)
    return player


@pytest.fixture
async def sample_guest_player(test_db: AsyncSession):
    """Create a sample guest player for testing."""
    player = Player(
        username="Guest_快乐_熊猫",
        is_guest=True
    )
    test_db.add(player)
    await test_db.commit()
    await test_db.refresh(player)
    return player


@pytest.fixture
async def sample_game_room(test_db: AsyncSession, sample_game_type: dict, sample_player: Player):
    """Create a sample game room for testing."""
    from src.models.game import GameRoomParticipant
    
    room = GameRoom(
        code="TEST1234",
        game_type_id=sample_game_type["slug"],
        status="Waiting",
        max_players=6,
        min_players=4,
    )
    test_db.add(room)
    await test_db.flush()  # Generate room.id
    
    # Add creator as participant
    participant = GameRoomParticipant(
        game_room_id=room.id,
        player_id=sample_player.id,
        is_ai_agent=False
    )
    test_db.add(participant)
    
    await test_db.commit()
    await test_db.refresh(room)
    return room
