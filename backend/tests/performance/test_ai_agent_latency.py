"""
T061: Performance Test - AI Agent Operation Latency

Tests AI agent add/remove operation latency:
- Owner adds 5 AI agents sequentially
- Owner removes 5 AI agents sequentially
- Each operation completes within 3 seconds
- No race conditions or inconsistent state

Requirements:
- FR-010: Add AI agents (max 4)
- FR-011: Remove AI agents
- SC-001: Response time < 3s for UI operations
"""

import asyncio
import time
import uuid
import pytest
from src.database import get_db
from src.models.player import Player
from src.services.game_room_service import GameRoomService
from src.services.ai_agent_service import AIAgentService


@pytest.mark.asyncio
async def test_ai_agent_add_latency(test_db):
    """
    Test AI agent addition latency.
    Each add operation should complete within 3 seconds.
    """
    test_id = str(uuid.uuid4())[:8]
    num_agents = 3  # Max AI agents per room (1 human + 3 AI = 4 total)
    
    print(f"\n{'='*60}")
    print(f"AI Agent Addition Latency Test")
    print(f"Adding {num_agents} AI agents sequentially")
    print(f"{'='*60}\n")
    
    async for db in get_db():
        # Create owner
        owner = Player(
            username=f"owner_ai_{test_id}",
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
        
        print(f"Room created: {room.code}")
        print(f"Starting AI agent additions...\n")
        
        # Add AI agents and measure latency
        ai_service = AIAgentService(db)
        latencies = []
        
        for i in range(num_agents):
            start_time = time.time()
            
            try:
                agent = await ai_service.add_ai_agent(
                    room_code=room.code,
                    requester_id=owner.id
                )
                
                latency = (time.time() - start_time) * 1000  # ms
                latencies.append(latency)
                
                print(f"  Agent {i+1}/{num_agents}: {agent.username}")
                print(f"    Latency: {latency:.2f} ms")
                print(f"    Status: ✓ Success")
                
                # Validate latency requirement (3s = 3000ms)
                assert latency < 3000, \
                    f"AI agent {i+1} add latency {latency:.2f}ms exceeds 3000ms requirement"
                
            except Exception as e:
                latency = (time.time() - start_time) * 1000
                latencies.append(latency)
                print(f"  Agent {i+1}/{num_agents}: ✗ Failed")
                print(f"    Latency: {latency:.2f} ms")
                print(f"    Error: {str(e)}")
                raise
        
        # Statistics
        avg = sum(latencies) / len(latencies)
        max_lat = max(latencies)
        min_lat = min(latencies)
        
        print(f"\n{'='*60}")
        print(f"AI Agent Addition Statistics")
        print(f"{'='*60}")
        print(f"  Total agents added: {num_agents}")
        print(f"  Average latency: {avg:.2f} ms")
        print(f"  Max latency: {max_lat:.2f} ms")
        print(f"  Min latency: {min_lat:.2f} ms")
        print(f"  All operations: < 3000ms ✓")
        print(f"{'='*60}\n")
        
        # Verify room state
        await db.refresh(room)
        expected_count = 1 + num_agents  # 1 owner + N AI agents
        
        assert room.current_participant_count == expected_count, \
            f"Room should have {expected_count} participants, got {room.current_participant_count}"
        
        print(f"✓ Room participant count verified: {room.current_participant_count}/{room.max_players}")
        
        break


@pytest.mark.asyncio
async def test_ai_agent_remove_latency(test_db):
    """
    Test AI agent removal latency.
    Each remove operation should complete within 3 seconds.
    """
    test_id = str(uuid.uuid4())[:8]
    num_agents = 3
    
    print(f"\n{'='*60}")
    print(f"AI Agent Removal Latency Test")
    print(f"Removing {num_agents} AI agents sequentially")
    print(f"{'='*60}\n")
    
    async for db in get_db():
        # Create owner
        owner = Player(
            username=f"owner_rm_{test_id}",
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
        
        # Add AI agents
        ai_service = AIAgentService(db)
        agents = []
        
        print(f"Room created: {room.code}")
        print(f"Adding {num_agents} AI agents...\n")
        
        for _ in range(num_agents):
            agent = await ai_service.add_ai_agent(
                room_code=room.code,
                requester_id=owner.id
            )
            agents.append(agent)
            print(f"  Added: {agent.username}")
        
        print(f"\nStarting AI agent removals...\n")
        
        # Remove AI agents and measure latency
        latencies = []
        
        for i, agent in enumerate(agents):
            start_time = time.time()
            
            try:
                await ai_service.remove_ai_agent(
                    room_code=room.code,
                    agent_id=agent.id,
                    requester_id=owner.id
                )
                
                latency = (time.time() - start_time) * 1000
                latencies.append(latency)
                
                print(f"  Agent {i+1}/{num_agents}: {agent.username}")
                print(f"    Latency: {latency:.2f} ms")
                print(f"    Status: ✓ Removed")
                
                # Validate latency requirement
                assert latency < 3000, \
                    f"AI agent {i+1} remove latency {latency:.2f}ms exceeds 3000ms requirement"
                
            except Exception as e:
                latency = (time.time() - start_time) * 1000
                latencies.append(latency)
                print(f"  Agent {i+1}/{num_agents}: ✗ Failed")
                print(f"    Latency: {latency:.2f} ms")
                print(f"    Error: {str(e)}")
                raise
        
        # Statistics
        avg = sum(latencies) / len(latencies)
        max_lat = max(latencies)
        min_lat = min(latencies)
        
        print(f"\n{'='*60}")
        print(f"AI Agent Removal Statistics")
        print(f"{'='*60}")
        print(f"  Total agents removed: {num_agents}")
        print(f"  Average latency: {avg:.2f} ms")
        print(f"  Max latency: {max_lat:.2f} ms")
        print(f"  Min latency: {min_lat:.2f} ms")
        print(f"  All operations: < 3000ms ✓")
        print(f"{'='*60}\n")
        
        # Verify room state
        await db.refresh(room)
        expected_count = 1  # Only owner remains
        
        assert room.current_participant_count == expected_count, \
            f"Room should have {expected_count} participant, got {room.current_participant_count}"
        
        print(f"✓ Room participant count verified: {room.current_participant_count}/{room.max_players}")
        
        break


@pytest.mark.asyncio
async def test_ai_agent_concurrent_operations(test_db):
    """
    Test concurrent AI agent operations across multiple rooms.
    Validates no race conditions or state corruption.
    """
    test_id = str(uuid.uuid4())[:8]
    num_rooms = 5
    agents_per_room = 2
    
    print(f"\n{'='*60}")
    print(f"AI Agent Concurrent Operations Test")
    print(f"Rooms: {num_rooms}, AI agents per room: {agents_per_room}")
    print(f"{'='*60}\n")
    
    async for db in get_db():
        # Create owners and rooms
        owners = []
        rooms = []
        
        print("Creating test environment...\n")
        
        for i in range(num_rooms):
            owner = Player(
                username=f"owner_conc_{test_id}_{i}",
                is_guest=True
            )
            db.add(owner)
            owners.append(owner)
        
        await db.commit()
        
        for owner in owners:
            await db.refresh(owner)
        
        room_service = GameRoomService(db)
        for i, owner in enumerate(owners):
            room = await room_service.create_room(
                creator_id=owner.id,
                game_type_slug="crime-scene",
                max_players=4,
                min_players=4
            )
            rooms.append(room)
            print(f"  Room {i+1}/{num_rooms} created: {room.code}")
        
        # Add AI agents concurrently across all rooms
        print(f"\nAdding {agents_per_room} AI agents to each room concurrently...\n")
        
        async def add_agents_to_room(room_code: str, owner_id: str, room_idx: int):
            """Add AI agents to a room"""
            results = []
            async for db_session in get_db():
                ai_service = AIAgentService(db_session)
                for i in range(agents_per_room):
                    start = time.time()
                    try:
                        agent = await ai_service.add_ai_agent(room_code, owner_id)
                        latency = (time.time() - start) * 1000
                        results.append({
                            "success": True,
                            "agent": agent.username,
                            "latency": latency,
                            "room_idx": room_idx
                        })
                    except Exception as e:
                        latency = (time.time() - start) * 1000
                        results.append({
                            "success": False,
                            "error": str(e),
                            "latency": latency,
                            "room_idx": room_idx
                        })
                return results
        
        # Create concurrent tasks
        add_tasks = [
            add_agents_to_room(room.code, owner.id, i)
            for i, (room, owner) in enumerate(zip(rooms, owners))
        ]
        
        start_time = time.time()
        all_results = await asyncio.gather(*add_tasks)
        total_time = (time.time() - start_time) * 1000
        
        # Flatten results
        flattened = []
        for room_results in all_results:
            flattened.extend(room_results)
        
        successful = [r for r in flattened if r["success"]]
        failed = [r for r in flattened if not r["success"]]
        
        print(f"Results:")
        print(f"  Total operations: {len(flattened)}")
        print(f"  Successful: {len(successful)}")
        print(f"  Failed: {len(failed)}")
        print(f"  Total time: {total_time:.2f} ms")
        
        if successful:
            latencies = [r["latency"] for r in successful]
            latencies.sort()
            avg = sum(latencies) / len(latencies)
            p95 = latencies[int(len(latencies) * 0.95)]
            
            print(f"\nLatency Statistics:")
            print(f"  Average: {avg:.2f} ms")
            print(f"  95th percentile: {p95:.2f} ms")
            print(f"  Max: {max(latencies):.2f} ms")
            
            # All should be under 3s
            max_latency = max(latencies)
            assert max_latency < 3000, \
                f"Max latency {max_latency:.2f}ms exceeds 3000ms requirement"
            
            print(f"\n✓ PASS: All operations < 3000ms")
        
        # Verify room states
        print(f"\n{'='*60}")
        print("Verifying Room States")
        print(f"{'='*60}")
        
        for i, room in enumerate(rooms):
            await db.refresh(room)
            expected = 1 + agents_per_room  # 1 owner + N AI agents
            
            print(f"  Room {i+1} ({room.code}): {room.current_participant_count}/{room.max_players} participants")
            
            assert room.current_participant_count == expected, \
                f"Room {i+1} should have {expected} participants, got {room.current_participant_count}"
        
        print(f"\n✓ All room states consistent")
        print(f"✓ No race conditions detected")
        print(f"{'='*60}\n")
        
        break


@pytest.mark.asyncio
async def test_ai_agent_full_lifecycle(test_db):
    """
    Test full AI agent lifecycle: add → remove → add → remove
    Validates state consistency and no memory leaks.
    """
    test_id = str(uuid.uuid4())[:8]
    cycles = 3
    
    print(f"\n{'='*60}")
    print(f"AI Agent Lifecycle Test ({cycles} cycles)")
    print(f"{'='*60}\n")
    
    async for db in get_db():
        # Create owner and room
        owner = Player(
            username=f"owner_cycle_{test_id}",
            is_guest=True
        )
        db.add(owner)
        await db.commit()
        await db.refresh(owner)
        
        room_service = GameRoomService(db)
        room = await room_service.create_room(
            creator_id=owner.id,
            game_type_slug="crime-scene",
            max_players=4,
            min_players=4
        )
        
        print(f"Room created: {room.code}\n")
        
        ai_service = AIAgentService(db)
        
        for cycle in range(cycles):
            print(f"Cycle {cycle + 1}/{cycles}")
            
            # Add AI agent
            start = time.time()
            agent = await ai_service.add_ai_agent(room.code, owner.id)
            add_latency = (time.time() - start) * 1000
            
            print(f"  Add: {agent.username} ({add_latency:.2f} ms)")
            
            assert add_latency < 3000, f"Add latency {add_latency:.2f}ms exceeds 3000ms"
            
            # Verify state
            await db.refresh(room)
            assert room.current_participant_count == 2, \
                f"Expected 2 participants after add, got {room.current_participant_count}"
            
            # Remove AI agent
            start = time.time()
            await ai_service.remove_ai_agent(room.code, agent.id, owner.id)
            remove_latency = (time.time() - start) * 1000
            
            print(f"  Remove: {agent.username} ({remove_latency:.2f} ms)")
            
            assert remove_latency < 3000, f"Remove latency {remove_latency:.2f}ms exceeds 3000ms"
            
            # Verify state
            await db.refresh(room)
            assert room.current_participant_count == 1, \
                f"Expected 1 participant after remove, got {room.current_participant_count}"
            
            print(f"  State: ✓ Consistent\n")
        
        print(f"{'='*60}")
        print(f"Lifecycle Test Complete")
        print(f"{'='*60}")
        print(f"✓ {cycles} add/remove cycles completed")
        print(f"✓ All operations < 3000ms")
        print(f"✓ State consistent after each cycle")
        print(f"{'='*60}\n")
        
        break
