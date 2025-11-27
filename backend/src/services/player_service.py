"""Player service for managing player accounts and profiles."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.player import Player
from src.models.player_profile import PlayerProfile
from src.utils.errors import BadRequestError, NotFoundError
from src.utils.username_generator import generate_unique_guest_username, is_guest_username


class PlayerService:
    """Service for player account management."""

    def __init__(self, db: AsyncSession):
        """Initialize player service.
        
        Args:
            db: Database session
        """
        self.db = db

    async def create_guest(self) -> Player:
        """Create a new guest player account.
        
        Returns:
            The created guest player
        """
        # Get existing usernames to ensure uniqueness
        result = await self.db.execute(
            select(Player.username).where(Player.username.like("Guest_%"))
        )
        existing_usernames = {row[0] for row in result.all()}

        # Generate unique username
        username = generate_unique_guest_username(existing_usernames)

        # Create guest player
        player = Player(
            username=username,
            is_guest=True
        )

        self.db.add(player)
        await self.db.flush()

        # Create player profile
        profile = PlayerProfile(player_id=player.id)
        self.db.add(profile)

        await self.db.commit()
        await self.db.refresh(player)

        return player

    async def upgrade_to_permanent(
        self,
        player_id: str,
        new_username: str
    ) -> Player:
        """Upgrade a guest account to permanent.
        
        Args:
            player_id: Guest player ID
            new_username: Desired permanent username
            
        Returns:
            The upgraded player
            
        Raises:
            NotFoundError: If player not found
            BadRequestError: If player is not a guest or username is invalid
        """
        # Get player
        player = await self.db.get(Player, player_id)
        if not player:
            raise NotFoundError(f"Player {player_id} not found")

        # Check if player is guest
        if not player.is_guest:
            raise BadRequestError("Player is already a permanent account")

        # Validate new username
        if not new_username or len(new_username) < 3:
            raise BadRequestError("Username must be at least 3 characters")

        if len(new_username) > 20:
            raise BadRequestError("Username must be at most 20 characters")

        if is_guest_username(new_username):
            raise BadRequestError("Cannot use Guest_ prefix for permanent accounts")

        # Check username availability
        result = await self.db.execute(
            select(Player).where(
                Player.username == new_username,
                Player.id != player_id
            )
        )
        if result.scalar_one_or_none():
            raise BadRequestError(f"Username '{new_username}' is already taken")

        # Upgrade account
        player.username = new_username
        player.is_guest = False
        player.expires_at = None  # Remove expiration

        await self.db.commit()
        await self.db.refresh(player)

        return player

    async def get_profile(self, player_id: str) -> tuple[Player, PlayerProfile]:
        """Get player profile information.
        
        Args:
            player_id: Player ID
            
        Returns:
            Tuple of (Player, PlayerProfile)
            
        Raises:
            NotFoundError: If player not found
        """
        player = await self.db.get(Player, player_id)
        if not player:
            raise NotFoundError(f"Player {player_id} not found")

        # Get or create profile
        result = await self.db.execute(
            select(PlayerProfile).where(PlayerProfile.player_id == player_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            profile = PlayerProfile(player_id=player_id)
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)

        return player, profile

    async def get_stats(self, player_id: str) -> dict:
        """Get player game statistics.
        
        Args:
            player_id: Player ID
            
        Returns:
            Dictionary with statistics
            
        Raises:
            NotFoundError: If player not found
        """
        player, profile = await self.get_profile(player_id)

        # Get wins (from profile)
        wins = profile.total_wins

        # Get total games from profile
        total_games = profile.total_games

        # Calculate win rate
        win_rate = (wins / total_games * 100) if total_games > 0 else 0

        return {
            "player_id": player_id,
            "username": player.username,
            "is_guest": player.is_guest,
            "total_games": total_games,
            "wins": wins,
            "win_rate": round(win_rate, 2),
            "favorite_game": profile.favorite_game_id,
            "play_time_minutes": 0,  # TODO: Calculate from game sessions
            "total_play_time_minutes": 0,  # TODO: Calculate from game sessions
            "created_at": player.created_at.isoformat(),
            "last_active": player.last_active.isoformat() if player.last_active else None,
            "last_active_at": player.last_active.isoformat() if player.last_active else None
        }

    async def update_last_active(self, player_id: str):
        """Update player's last active timestamp.
        
        Args:
            player_id: Player ID
        """
        player = await self.db.get(Player, player_id)

        if player:
            player.last_active = datetime.utcnow()
            await self.db.commit()
