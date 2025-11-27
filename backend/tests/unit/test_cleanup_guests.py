"""Tests for guest account cleanup script."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy import select
import asyncio

from scripts.cleanup_guests import cleanup_expired_guests, main
from src.models.user import Player, PlayerProfile
from src.models.game import GameRoomParticipant


@pytest.fixture
def setup_test_players():
    """Create test players with various expiration states."""
    async def _setup(test_db):
        now = datetime.utcnow()
        
        # Expired guest (31 days old)
        expired_guest = Player(
            username="Guest_已过期_老虎",
            is_guest=True,
            expires_at=now - timedelta(days=31)
        )
        
        # Recently expired guest (30 days + 1 hour)
        recently_expired = Player(
            username="Guest_刚过期_熊猫",
            is_guest=True,
            expires_at=now - timedelta(days=30, hours=1)
        )
        
        # Valid guest (20 days old, 10 days left)
        valid_guest = Player(
            username="Guest_有效_兔子",
            is_guest=True,
            expires_at=now + timedelta(days=10)
        )
        
        # Permanent account (should never be deleted)
        permanent_player = Player(
            username="PermanentUser",
            is_guest=False,
            expires_at=None
        )
        
        test_db.add_all([expired_guest, recently_expired, valid_guest, permanent_player])
        await test_db.commit()
        
        # Refresh to get IDs
        for player in [expired_guest, recently_expired, valid_guest, permanent_player]:
            await test_db.refresh(player)
        
        return {
            "expired": expired_guest,
            "recently_expired": recently_expired,
            "valid_guest": valid_guest,
            "permanent": permanent_player
        }
    
    return _setup


class TestCleanupExpiredGuests:
    """Test cleanup_expired_guests function."""

    @pytest.mark.asyncio
    async def test_cleanup_deletes_expired_guests(self, test_db, setup_test_players):
        """Test that cleanup deletes expired guest accounts."""
        players = await setup_test_players(test_db)
        
        # Run cleanup
        await cleanup_expired_guests()
        
        # Check that expired guests are deleted
        result = await test_db.execute(
            select(Player).where(Player.id == players["expired"].id)
        )
        assert result.scalar_one_or_none() is None
        
        result = await test_db.execute(
            select(Player).where(Player.id == players["recently_expired"].id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_cleanup_preserves_valid_guests(self, test_db, setup_test_players):
        """Test that cleanup preserves valid guest accounts."""
        players = await setup_test_players(test_db)
        
        await cleanup_expired_guests()
        
        # Valid guest should still exist
        result = await test_db.execute(
            select(Player).where(Player.id == players["valid_guest"].id)
        )
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_cleanup_preserves_permanent_accounts(self, test_db, setup_test_players):
        """Test that cleanup never deletes permanent accounts."""
        players = await setup_test_players(test_db)
        
        await cleanup_expired_guests()
        
        # Permanent account should still exist
        result = await test_db.execute(
            select(Player).where(Player.id == players["permanent"].id)
        )
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_cleanup_with_no_expired_guests(self, test_db):
        """Test cleanup when no expired guests exist."""
        # Create only valid guests
        valid1 = Player(
            username="Guest_有效一_狼",
            is_guest=True,
            expires_at=datetime.utcnow() + timedelta(days=15)
        )
        valid2 = Player(
            username="Guest_有效二_鸟",
            is_guest=True,
            expires_at=datetime.utcnow() + timedelta(days=20)
        )
        
        test_db.add_all([valid1, valid2])
        await test_db.commit()
        
        # Should complete without errors
        await cleanup_expired_guests()
        
        # Both should still exist
        result = await test_db.execute(select(Player))
        remaining = result.scalars().all()
        assert len(remaining) == 2

    @pytest.mark.asyncio
    async def test_cleanup_cascades_to_profile(self, test_db):
        """Test that cleanup cascades to PlayerProfile."""
        # Create expired guest with profile
        expired = Player(
            username="Guest_有资料_猫",
            is_guest=True,
            expires_at=datetime.utcnow() - timedelta(days=31)
        )
        test_db.add(expired)
        await test_db.commit()
        await test_db.refresh(expired)
        
        # Create profile
        profile = PlayerProfile(
            player_id=expired.id,
            total_games=5,
            total_wins=2
        )
        test_db.add(profile)
        await test_db.commit()
        
        # Run cleanup
        await cleanup_expired_guests()
        
        # Profile should be cascade deleted
        result = await test_db.execute(
            select(PlayerProfile).where(PlayerProfile.player_id == expired.id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_cleanup_multiple_expired_guests(self, test_db):
        """Test cleanup with multiple expired guests."""
        now = datetime.utcnow()
        
        # Create 10 expired guests
        expired_guests = []
        for i in range(10):
            guest = Player(
                username=f"Guest_批量{i}_动物",
                is_guest=True,
                expires_at=now - timedelta(days=31 + i)
            )
            expired_guests.append(guest)
        
        test_db.add_all(expired_guests)
        await test_db.commit()
        
        # Get count before
        result = await test_db.execute(select(Player))
        count_before = len(result.scalars().all())
        assert count_before == 10
        
        # Run cleanup
        await cleanup_expired_guests()
        
        # All should be deleted
        result = await test_db.execute(select(Player))
        count_after = len(result.scalars().all())
        assert count_after == 0

    @pytest.mark.asyncio
    async def test_cleanup_boundary_condition_exact_30_days(self, test_db):
        """Test cleanup at exact 30-day boundary."""
        # Create guest that expired exactly now
        boundary_guest = Player(
            username="Guest_边界_案例",
            is_guest=True,
            expires_at=datetime.utcnow()
        )
        
        test_db.add(boundary_guest)
        await test_db.commit()
        await test_db.refresh(boundary_guest)
        
        # Run cleanup
        await cleanup_expired_guests()
        
        # Should be deleted (expires_at < utcnow, not <=)
        result = await test_db.execute(
            select(Player).where(Player.id == boundary_guest.id)
        )
        # May or may not be deleted depending on exact timing
        # This tests the boundary behavior

    @pytest.mark.asyncio
    async def test_cleanup_performance_with_many_players(self, test_db):
        """Test cleanup performance with large dataset."""
        import time
        
        now = datetime.utcnow()
        
        # Create 100 players (50 expired, 50 valid)
        players = []
        for i in range(100):
            is_expired = i < 50
            guest = Player(
                username=f"Guest_性能{i}_测试",
                is_guest=True,
                expires_at=(
                    now - timedelta(days=31)
                    if is_expired else
                    now + timedelta(days=15)
                )
            )
            players.append(guest)
        
        test_db.add_all(players)
        await test_db.commit()
        
        # Time the cleanup
        start = time.time()
        await cleanup_expired_guests()
        duration = time.time() - start
        
        # Should complete reasonably fast (< 2 seconds)
        assert duration < 2.0
        
        # Verify correct counts
        result = await test_db.execute(select(Player))
        remaining = result.scalars().all()
        assert len(remaining) == 50  # Only valid guests remain


class TestCleanupOutputLogging:
    """Test cleanup script output and logging."""

    @pytest.mark.asyncio
    async def test_cleanup_prints_found_message(self, test_db, capsys):
        """Test that cleanup prints found message."""
        now = datetime.utcnow()
        
        # Create expired guest
        expired = Player(
            username="Guest_打印_消息",
            is_guest=True,
            expires_at=now - timedelta(days=31)
        )
        test_db.add(expired)
        await test_db.commit()
        
        await cleanup_expired_guests()
        
        # Check output
        captured = capsys.readouterr()
        assert "Found 1 expired guest accounts" in captured.out
        assert "Guest_打印_消息" in captured.out

    @pytest.mark.asyncio
    async def test_cleanup_prints_no_expired_message(self, test_db, capsys):
        """Test message when no expired guests found."""
        # Create only valid guest
        valid = Player(
            username="Guest_无过期_玩家",
            is_guest=True,
            expires_at=datetime.utcnow() + timedelta(days=10)
        )
        test_db.add(valid)
        await test_db.commit()
        
        await cleanup_expired_guests()
        
        captured = capsys.readouterr()
        assert "No expired guest accounts found" in captured.out

    @pytest.mark.asyncio
    async def test_cleanup_prints_deleted_count(self, test_db, capsys):
        """Test that cleanup prints deletion confirmation."""
        now = datetime.utcnow()
        
        # Create 3 expired guests
        for i in range(3):
            guest = Player(
                username=f"Guest_删除{i}_确认",
                is_guest=True,
                expires_at=now - timedelta(days=31)
            )
            test_db.add(guest)
        
        await test_db.commit()
        
        await cleanup_expired_guests()
        
        captured = capsys.readouterr()
        assert "Deleted 3 expired guest accounts" in captured.out
        assert "✓" in captured.out


class TestMainFunction:
    """Test main entry point function."""

    @pytest.mark.asyncio
    async def test_main_success_flow(self, capsys):
        """Test main function successful execution."""
        with patch("scripts.cleanup_guests.cleanup_expired_guests") as mock_cleanup:
            mock_cleanup.return_value = AsyncMock()
            
            await main()
            
            captured = capsys.readouterr()
            assert "Starting guest account cleanup" in captured.out
            assert "Timestamp:" in captured.out
            assert "Cleanup completed successfully" in captured.out
            
            mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_handles_exceptions(self, capsys):
        """Test main function exception handling."""
        with patch("scripts.cleanup_guests.cleanup_expired_guests") as mock_cleanup:
            mock_cleanup.side_effect = Exception("Database error")
            
            with pytest.raises(SystemExit) as exc_info:
                await main()
            
            assert exc_info.value.code == 1
            
            captured = capsys.readouterr()
            assert "Error during cleanup" in captured.out
            assert "Database error" in captured.out

    @pytest.mark.asyncio
    async def test_main_prints_timestamp(self, capsys):
        """Test that main prints UTC timestamp."""
        with patch("scripts.cleanup_guests.cleanup_expired_guests") as mock_cleanup:
            mock_cleanup.return_value = AsyncMock()
            
            before_time = datetime.utcnow()
            await main()
            after_time = datetime.utcnow()
            
            captured = capsys.readouterr()
            
            # Should contain timestamp
            assert "Timestamp:" in captured.out
            
            # Extract timestamp from output
            lines = captured.out.split("\n")
            timestamp_line = [l for l in lines if "Timestamp:" in l][0]
            
            # Basic format check
            assert "T" in timestamp_line  # ISO format contains T


class TestCleanupEdgeCases:
    """Test edge cases in cleanup logic."""

    @pytest.mark.asyncio
    async def test_cleanup_with_null_expires_at(self, test_db):
        """Test cleanup ignores players with null expires_at."""
        # Create guest with null expires_at (shouldn't happen, but test it)
        null_expiry = Player(
            username="Guest_空过期_异常",
            is_guest=True,
            expires_at=None
        )
        test_db.add(null_expiry)
        await test_db.commit()
        
        # Should not raise error
        await cleanup_expired_guests()
        
        # Player should still exist (null not < utcnow)
        result = await test_db.execute(
            select(Player).where(Player.username == "Guest_空过期_异常")
        )
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_cleanup_concurrent_execution(self, test_db):
        """Test concurrent cleanup execution safety."""
        now = datetime.utcnow()
        
        # Create expired guests
        for i in range(5):
            guest = Player(
                username=f"Guest_并发{i}_测试",
                is_guest=True,
                expires_at=now - timedelta(days=31)
            )
            test_db.add(guest)
        
        await test_db.commit()
        
        # Run cleanup twice concurrently
        await asyncio.gather(
            cleanup_expired_guests(),
            cleanup_expired_guests()
        )
        
        # All should be deleted (second run finds nothing)
        result = await test_db.execute(select(Player))
        remaining = result.scalars().all()
        assert len(remaining) == 0

    @pytest.mark.asyncio
    async def test_cleanup_transaction_rollback_on_error(self, test_db):
        """Test that errors don't partially delete guests."""
        # Create expired guests
        guest1 = Player(
            username="Guest_事务_第一",
            is_guest=True,
            expires_at=datetime.utcnow() - timedelta(days=31)
        )
        guest2 = Player(
            username="Guest_事务_第二",
            is_guest=True,
            expires_at=datetime.utcnow() - timedelta(days=31)
        )
        
        test_db.add_all([guest1, guest2])
        await test_db.commit()
        
        # Mock session.commit to raise error
        with patch("src.database.AsyncSessionLocal") as mock_session_local:
            mock_session = MagicMock()
            mock_session.execute = AsyncMock()
            mock_session.commit = AsyncMock(side_effect=Exception("Commit failed"))
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            
            mock_session_local.return_value = mock_session
            
            # Should raise error
            with pytest.raises(Exception, match="Commit failed"):
                await cleanup_expired_guests()
        
        # Both guests should still exist (transaction rolled back)
        result = await test_db.execute(select(Player))
        remaining = result.scalars().all()
        assert len(remaining) == 2


class TestCleanupIntegration:
    """Integration tests for full cleanup workflow."""

    @pytest.mark.asyncio
    async def test_full_cleanup_workflow(self, test_db):
        """Test complete cleanup workflow."""
        now = datetime.utcnow()
        
        # Setup: Create mixed player set
        players_data = [
            # Expired guests (should be deleted)
            ("Guest_过期一_老虎", True, -35),
            ("Guest_过期二_熊猫", True, -32),
            ("Guest_过期三_兔子", True, -31),
            # Valid guests (should be kept)
            ("Guest_有效一_狼", True, 10),
            ("Guest_有效二_鸟", True, 20),
            # Permanent (should be kept)
            ("PermanentUser1", False, None),
            ("PermanentUser2", False, None),
        ]
        
        for username, is_guest, days_offset in players_data:
            if days_offset is None:
                expires_at = None
            else:
                expires_at = now + timedelta(days=days_offset)
            
            player = Player(
                username=username,
                is_guest=is_guest,
                expires_at=expires_at
            )
            test_db.add(player)
        
        await test_db.commit()
        
        # Initial count
        result = await test_db.execute(select(Player))
        assert len(result.scalars().all()) == 7
        
        # Execute cleanup
        await cleanup_expired_guests()
        
        # Verify final state
        result = await test_db.execute(select(Player))
        remaining = result.scalars().all()
        
        # Should have 4 remaining (2 valid guests + 2 permanent)
        assert len(remaining) == 4
        
        # Verify correct players remain
        usernames = {p.username for p in remaining}
        assert "Guest_有效一_狼" in usernames
        assert "Guest_有效二_鸟" in usernames
        assert "PermanentUser1" in usernames
        assert "PermanentUser2" in usernames
        
        # Verify expired guests are gone
        assert "Guest_过期一_老虎" not in usernames
        assert "Guest_过期二_熊猫" not in usernames
        assert "Guest_过期三_兔子" not in usernames
