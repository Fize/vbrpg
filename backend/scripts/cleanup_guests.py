"""Cleanup expired guest accounts.

This script should be run periodically (e.g., via cron) to delete expired guest accounts.
Guest accounts expire 30 days after creation if not upgraded to permanent.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Ensure we're running from backend directory
backend_dir = Path(__file__).parent.parent
os.chdir(backend_dir)

# Add backend directory to path
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, delete

from src.database import AsyncSessionLocal
from src.models.user import Player


async def cleanup_expired_guests():
    """Delete expired guest accounts and their related data.
    
    Cascading deletes will handle:
    - PlayerProfile
    - GameRoomParticipant records
    - Related game data
    """
    async with AsyncSessionLocal() as session:
        # Find expired guest accounts
        result = await session.execute(
            select(Player).where(
                Player.is_guest == True,
                Player.expires_at < datetime.utcnow()
            )
        )
        expired_guests = result.scalars().all()
        
        if not expired_guests:
            print("No expired guest accounts found.")
            return
        
        print(f"Found {len(expired_guests)} expired guest accounts:")
        for player in expired_guests:
            print(f"  - {player.username} (ID: {player.id}, expired: {player.expires_at})")
        
        # Delete expired guests (cascading deletes will clean up related data)
        await session.execute(
            delete(Player).where(
                Player.is_guest == True,
                Player.expires_at < datetime.utcnow()
            )
        )
        
        await session.commit()
        print(f"✓ Deleted {len(expired_guests)} expired guest accounts")


async def main():
    """Run cleanup process."""
    print("Starting guest account cleanup...")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print()
    
    try:
        await cleanup_expired_guests()
        print()
        print("Cleanup completed successfully!")
    
    except Exception as e:
        print(f"Error during cleanup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
