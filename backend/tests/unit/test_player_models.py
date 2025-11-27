"""Unit tests for Player and PlayerProfile models."""
import pytest
from datetime import datetime, timedelta
from src.models.user import Player, PlayerProfile



@pytest.mark.asyncio
class TestPlayerModel:
    """Test Player model."""
    
    async def test_create_permanent_player(self, test_db):
        """Test creating a permanent player."""
        player = Player(
            username="permanent_user",
            is_guest=False
        )
        test_db.add(player)
        await test_db.commit()
        await test_db.refresh(player)
        
        assert player.id is not None
        assert player.username == "permanent_user"
        assert player.is_guest is False
        assert player.expires_at is None
        assert player.created_at is not None
    
    async def test_create_guest_player(self, test_db):
        """Test creating a guest player with expiration."""
        player = Player(
            username="Guest_临时_用户",
            is_guest=True
        )
        test_db.add(player)
        await test_db.commit()
        await test_db.refresh(player)
        
        assert player.id is not None
        assert player.is_guest is True
        assert player.expires_at is not None
        # Should expire in ~30 days
        delta = player.expires_at - datetime.utcnow()
        assert 29 <= delta.days <= 31
    
    async def test_is_expired_not_guest(self, test_db, sample_player):
        """Test that permanent players never expire."""
        assert sample_player.is_expired() is False
    
    async def test_is_expired_guest_not_expired(self, test_db, sample_guest_player):
        """Test that recent guest players are not expired."""
        assert sample_guest_player.is_expired() is False
    
    async def test_is_expired_guest_expired(self, test_db):
        """Test that old guest players are expired."""
        player = Player(
            username="Guest_过期_用户",
            is_guest=True
        )
        # Set expiration in the past
        player.expires_at = datetime.utcnow() - timedelta(days=1)
        test_db.add(player)
        await test_db.commit()
        await test_db.refresh(player)
        
        assert player.is_expired() is True


@pytest.mark.asyncio
class TestPlayerProfileModel:
    """Test PlayerProfile model."""
    
    async def test_create_profile(self, test_db, sample_player):
        """Test creating a player profile."""
        profile = PlayerProfile(
            player_id=sample_player.id,
            total_games=10,
            total_wins=5
        )
        test_db.add(profile)
        await test_db.commit()
        await test_db.refresh(profile)
        
        assert profile.player_id == sample_player.id
        assert profile.total_games == 10
        assert profile.total_wins == 5
        assert profile.updated_at is not None
    
    async def test_win_rate_calculation(self, test_db, sample_player):
        """Test win rate calculation."""
        profile = PlayerProfile(
            player_id=sample_player.id,
            total_games=10,
            total_wins=3
        )
        test_db.add(profile)
        await test_db.commit()
        await test_db.refresh(profile)
        
        assert profile.win_rate == 30.0
    
    async def test_win_rate_zero_games(self, test_db, sample_player):
        """Test win rate with zero games played."""
        profile = PlayerProfile(
            player_id=sample_player.id,
            total_games=0,
            total_wins=0
        )
        test_db.add(profile)
        await test_db.commit()
        await test_db.refresh(profile)
        
        assert profile.win_rate == 0.0
    
    async def test_win_rate_perfect(self, test_db, sample_player):
        """Test win rate with all wins."""
        profile = PlayerProfile(
            player_id=sample_player.id,
            total_games=5,
            total_wins=5
        )
        test_db.add(profile)
        await test_db.commit()
        await test_db.refresh(profile)
        
        assert profile.win_rate == 100.0
    
    async def test_preferences_default(self, test_db, sample_player):
        """Test default preferences."""
        profile = PlayerProfile(
            player_id=sample_player.id
        )
        test_db.add(profile)
        await test_db.commit()
        await test_db.refresh(profile)
        
        assert profile.ui_preferences is None
        assert profile.total_games == 0
        assert profile.total_wins == 0
