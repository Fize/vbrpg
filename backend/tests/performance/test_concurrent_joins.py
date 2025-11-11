"""
T059: Performance Test - Concurrent Room Joins

Tests concurrent join behavior:
- 10 players simultaneously attempt to join same room
- Only max_players (4) succeed, rest get 409 errors
- Database consistency maintained (no duplicate participants)
- Join latency < 5 seconds 95th percentile

Requirements:
- FR-018: Race condition handling
- SC-001: Join latency < 5s (95th percentile)
"""

import asyncio
import time
import uuid
import pytest
from sqlalchemy import select
from src.database import get_db
from src.models.game_room import GameRoom
from src.models.game_room_participant import GameRoomParticipant
from src.models.player import Player
from src.services.game_room_service import GameRoomService
from src.services.player_service import PlayerService


@pytest.mark.asyncio
async def test_concurrent_joins_race_condition(test_db):
    """
    Test that concurrent joins are handled correctly with race conditions.
    Only max_players should succeed, rest should get errors.
    """
    test_id = str(uuid.uuid4())[:8]  # Unique ID for this test run
    
    # Create a test room with max 4 players
    async for db in get_db():
        # Create owner
        owner = Player(
            username=f"owner_test_{test_id}",
            is_guest=True
        )
        db.add(owner)
        await db.commit()
        await db.refresh(owner)
        
        # Create room
        room_service = GameRoomService(db)
        room = await room_service.create_room(
            creator_id=owner.id,
            game_type_slug="crime-scene",
            max_players=4,
            min_players=4
        )
        
        room_code = room.code
        
        # Create 10 test players
        players = []
        for i in range(10):
            player = Player(
                username=f"test_concurrent_{test_id}_{i+1}",
                is_guest=True
            )
            db.add(player)
            players.append(player)
        
        await db.commit()
        
        for player in players:
            await db.refresh(player)
        
        print(f"\nRoom created: {room_code} with max 4 players")
        print(f"Current participants: 1 (owner)")
        print(f"Attempting 10 concurrent joins...")
        
        # Create tasks for concurrent joins
        join_tasks = []
        latencies = []
        
        async def join_room_timed(player_id: str, room_code: str):
            """Join room and record latency"""
            start_time = time.time()
            try:
                async for db_session in get_db():
                    service = GameRoomService(db_session)
                    await service.join_room(room_code, player_id)
                    latency = (time.time() - start_time) * 1000  # ms
                    return {"success": True, "latency": latency, "player_id": player_id}
            except Exception as e:
                latency = (time.time() - start_time) * 1000
                return {"success": False, "latency": latency, "player_id": player_id, "error": str(e)}
        
        # Launch all joins concurrently
        join_tasks = [join_room_timed(player.id, room_code) for player in players]
        results = await asyncio.gather(*join_tasks, return_exceptions=True)
        
        # Analyze results
        successful = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed = [r for r in results if isinstance(r, dict) and not r.get("success")]
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        print(f"\nResults:")
        print(f"  Successful joins: {len(successful)}")
        print(f"  Failed joins: {len(failed)}")
        print(f"  Exceptions: {len(exceptions)}")
        
        # Extract latencies
        all_latencies = [r["latency"] for r in results if isinstance(r, dict)]
        all_latencies.sort()
        
        if all_latencies:
            avg_latency = sum(all_latencies) / len(all_latencies)
            p95_latency = all_latencies[int(len(all_latencies) * 0.95)] if len(all_latencies) > 1 else all_latencies[0]
            
            print(f"\nLatency Statistics:")
            print(f"  Average: {avg_latency:.2f} ms")
            print(f"  95th percentile: {p95_latency:.2f} ms")
            print(f"  Max: {max(all_latencies):.2f} ms")
            print(f"  Min: {min(all_latencies):.2f} ms")
        
        # Verify: Only 3 additional players should succeed (1 owner + 3 = 4 total)
        assert len(successful) == 3, f"Expected exactly 3 successful joins, got {len(successful)}"
        
        # Verify: 7 should fail (10 - 3 successful)
        assert len(failed) >= 7, f"Expected at least 7 failed joins, got {len(failed)}"
        
        # Verify: Failed joins should have "Room is full" error
        for fail in failed:
            error_msg = fail.get("error", "")
            assert "full" in error_msg.lower() or "满" in error_msg, \
                f"Expected 'full' error, got: {error_msg}"
        
        # Verify database consistency
        stmt = select(GameRoomParticipant).where(
            GameRoomParticipant.room_id == room.id
        )
        result = await db.execute(stmt)
        participants = result.scalars().all()
        
        print(f"\nDatabase consistency check:")
        print(f"  Total participants in DB: {len(participants)}")
        
        # Should have exactly 4 participants (1 owner + 3 joined)
        assert len(participants) == 4, f"Expected 4 participants in DB, got {len(participants)}"
        
        # Verify no duplicates
        participant_ids = [p.player_id for p in participants]
        assert len(participant_ids) == len(set(participant_ids)), "Duplicate participants found!"
        
        # Verify room participant count
        await db.refresh(room)
        assert room.current_participant_count == 4, \
            f"Room count should be 4, got {room.current_participant_count}"
        
        # Verify latency requirement: 95th percentile < 5 seconds
        if all_latencies:
            assert p95_latency < 5000, \
                f"95th percentile latency {p95_latency:.2f}ms exceeds 5000ms requirement"
        
        print("\n✓ Concurrent join test passed:")
        print("  ✓ Correct number of successful joins (3)")
        print("  ✓ Correct number of failed joins (7)")
        print("  ✓ Database consistency maintained")
        print("  ✓ No duplicate participants")
        print("  ✓ Latency < 5s (95th percentile)")
        
        break


@pytest.mark.asyncio
async def test_concurrent_joins_across_multiple_rooms(test_db):
    """
    Test concurrent joins across multiple rooms to verify isolation.
    """
    test_id = str(uuid.uuid4())[:8]
    
    async for db in get_db():
        # Create 3 rooms with different owners
        rooms = []
        owners = []
        
        for i in range(3):
            owner = Player(
                username=f"owner_multi_{test_id}_{i+1}",
                is_guest=True
            )
            db.add(owner)
            owners.append(owner)
        
        await db.commit()
        
        for owner in owners:
            await db.refresh(owner)
        
        room_service = GameRoomService(db)
        
        for owner in owners:
            room = await room_service.create_room(
                creator_id=owner.id,
                game_type_slug="crime-scene",
                max_players=4,
                min_players=4
            )
            rooms.append(room)
        
        print(f"\nCreated {len(rooms)} rooms")
        
        # Create 9 players (3 per room)
        players = []
        for i in range(9):
            player = Player(
                username=f"test_multi_{test_id}_{i+1}",
                is_guest=True
            )
            db.add(player)
            players.append(player)
        
        await db.commit()
        
        for player in players:
            await db.refresh(player)
        
        # Assign players to rooms (3 per room)
        join_tasks = []
        
        for i, player in enumerate(players):
            room_idx = i // 3  # 0-2 -> room 0, 3-5 -> room 1, 6-8 -> room 2
            room_code = rooms[room_idx].code
            
            async def join_specific_room(p_id, r_code):
                try:
                    async for db_session in get_db():
                        service = GameRoomService(db_session)
                        await service.join_room(r_code, p_id)
                        return {"success": True, "room": r_code}
                except Exception as e:
                    return {"success": False, "error": str(e)}
            
            join_tasks.append(join_specific_room(player.id, room_code))
        
        # Execute all joins concurrently
        results = await asyncio.gather(*join_tasks)
        
        successful = [r for r in results if r.get("success")]
        print(f"\nSuccessful joins: {len(successful)}/9")
        
        # Verify all joins succeeded
        assert len(successful) == 9, "All joins should succeed (3 per room)"
        
        # Verify each room has exactly 4 participants (1 owner + 3 joined)
        for i, room in enumerate(rooms):
            await db.refresh(room)
            assert room.current_participant_count == 4, \
                f"Room {i+1} should have 4 participants, got {room.current_participant_count}"
        
        print("✓ Concurrent joins across multiple rooms successful")
        print("  ✓ All 9 joins succeeded")
        print("  ✓ Each room has correct participant count (4)")
        
        break


@pytest.mark.asyncio
async def test_join_latency_under_load(test_db):
    """
    Benchmark join latency with sequential joins to establish baseline.
    """
    test_id = str(uuid.uuid4())[:8]
    
    async for db in get_db():
        # Create owner and room
        owner = Player(
            username=f"owner_latency_{test_id}",
            is_guest=True
        )
        db.add(owner)
        await db.commit()
        await db.refresh(owner)
        
        room_service = GameRoomService(db)
        room = await room_service.create_room(
            creator_id=owner.id,
            game_type_slug="crime-scene",
            max_players=8,  # Allow more players for this test (within crime-scene limits)
            min_players=4
        )
        
        # Create 20 players
        players = []
        for i in range(20):
            player = Player(
                username=f"test_latency_{test_id}_{i+1}",
                is_guest=True
            )
            db.add(player)
            players.append(player)
        
        await db.commit()
        
        for player in players:
            await db.refresh(player)
        
        print(f"\nTesting join latency with sequential joins...")
        
        latencies = []
        
        for player in players[:7]:  # Only join 7 (room capacity is 8 with owner)
            start_time = time.time()
            
            try:
                await room_service.join_room(room.code, player.id)
                latency = (time.time() - start_time) * 1000
                latencies.append(latency)
            except Exception as e:
                print(f"Error joining: {e}")
                break
        
        if latencies:
            latencies.sort()
            
            avg_latency = sum(latencies) / len(latencies)
            p50_latency = latencies[len(latencies) // 2]
            p95_latency = latencies[int(len(latencies) * 0.95)]
            p99_latency = latencies[int(len(latencies) * 0.99)] if len(latencies) > 10 else latencies[-1]
            
            print(f"\nLatency Benchmark (sequential joins):")
            print(f"  Average: {avg_latency:.2f} ms")
            print(f"  50th percentile: {p50_latency:.2f} ms")
            print(f"  95th percentile: {p95_latency:.2f} ms")
            print(f"  99th percentile: {p99_latency:.2f} ms")
            print(f"  Max: {max(latencies):.2f} ms")
            
            # Verify SC-001: Join latency < 5 seconds (95th percentile)
            assert p95_latency < 5000, \
                f"95th percentile latency {p95_latency:.2f}ms exceeds 5000ms"
            
            print("\n✓ Latency requirement met (SC-001)")
        
        break
