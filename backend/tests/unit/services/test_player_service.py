"""Tests for PlayerService."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.player_service import PlayerService
from src.models.user import Player, PlayerProfile
from src.utils.errors import BadRequestError, NotFoundError


class TestPlayerService:
    """Test PlayerService methods."""

    @pytest.mark.asyncio
    async def test_create_guest(self, test_db: AsyncSession):
        """Test creating guest account."""
        service = PlayerService(test_db)
        
        # Create guest
        player = await service.create_guest()
        
        # Verify player created
        assert player is not None
        assert player.username.startswith("Guest_")
        assert player.is_guest is True
        assert player.expires_at is not None
        
        # Verify expires in ~30 days
        expires_delta = player.expires_at - datetime.utcnow()
        assert 29 <= expires_delta.days <= 31
        
        # Verify profile created
        profile = await service.get_profile(player.id)
        assert profile is not None
        assert profile[1].total_games == 0
        assert profile[1].total_wins == 0

    @pytest.mark.asyncio
    async def test_create_multiple_guests_unique_usernames(self, test_db: AsyncSession):
        """Test creating multiple guests generates unique usernames."""
        service = PlayerService(test_db)
        
        # Create multiple guests
        guests = []
        for _ in range(5):
            guest = await service.create_guest()
            guests.append(guest)
        
        # Verify all usernames are unique
        usernames = [g.username for g in guests]
        assert len(usernames) == len(set(usernames))

    @pytest.mark.asyncio
    async def test_upgrade_to_permanent(self, test_db: AsyncSession):
        """Test upgrading guest to permanent account."""
        service = PlayerService(test_db)
        
        # Create guest
        guest = await service.create_guest()
        guest_id = guest.id
        
        # Upgrade
        new_username = "PermanentPlayer"
        upgraded = await service.upgrade_to_permanent(guest_id, new_username)
        
        # Verify upgrade
        assert upgraded.username == new_username
        assert upgraded.is_guest is False
        assert upgraded.expires_at is None

    @pytest.mark.asyncio
    async def test_upgrade_invalid_username(self, test_db: AsyncSession):
        """Test upgrade rejects invalid usernames."""
        service = PlayerService(test_db)
        
        # Create guest
        guest = await service.create_guest()
        
        # Test too short
        with pytest.raises(BadRequestError, match="3 characters"):
            await service.upgrade_to_permanent(guest.id, "ab")
        
        # Test too long
        with pytest.raises(BadRequestError, match="20 characters"):
            await service.upgrade_to_permanent(guest.id, "a" * 21)
        
        # Test Guest_ prefix
        with pytest.raises(BadRequestError, match="Guest_"):
            await service.upgrade_to_permanent(guest.id, "Guest_Something")

    @pytest.mark.asyncio
    async def test_get_profile(self, test_db: AsyncSession):
        """Test getting player profile."""
        service = PlayerService(test_db)
        
        # Create guest
        guest = await service.create_guest()
        
        # Get profile
        player, profile = await service.get_profile(guest.id)
        
        # Verify
        assert player.id == guest.id
        assert profile.player_id == guest.id
        assert profile.total_games == 0

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, test_db: AsyncSession):
        """Test getting profile for non-existent player."""
        service = PlayerService(test_db)
        
        with pytest.raises(NotFoundError):
            await service.get_profile("non-existent-id")

    @pytest.mark.asyncio
    async def test_get_stats(self, test_db: AsyncSession):
        """Test getting player statistics."""
        service = PlayerService(test_db)
        
        # Create player
        guest = await service.create_guest()
        
        # Get stats (should return zero stats for new player)
        stats = await service.get_stats(guest.id)
        
        # Verify
        assert stats["total_games"] == 0
        assert stats["wins"] == 0
        assert stats["win_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_update_last_active(self, test_db: AsyncSession):
        """Test updating last active timestamp."""
        service = PlayerService(test_db)
        
        # Create guest
        guest = await service.create_guest()
        original_time = guest.last_active
        
        # Wait a bit and update
        import asyncio
        await asyncio.sleep(0.1)
        
        await service.update_last_active(guest.id)
        
        # Refresh and verify
        await test_db.refresh(guest)
        assert guest.last_active > original_time
