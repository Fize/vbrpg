# Research: Multiplayer Room Join & AI Agent Management

**Feature**: 002-room-join-management  
**Date**: 2025-11-09  
**Status**: Complete

## Overview

This document captures technical decisions and patterns researched for implementing multiplayer room joining and AI agent management in game lobbies. All decisions leverage existing VBRPG platform infrastructure (FastAPI, python-socketio, Vue 3, SQLite) without introducing new technologies.

## Research Areas

### 1. Concurrent Join Conflict Resolution

**Decision**: Server-side timestamp-based ordering with optimistic locking

**Rationale**:
- SQLite transaction isolation prevents race conditions on slot allocation
- Server-side timestamps provide authoritative ordering (no client clock trust issues)
- Optimistic approach minimizes latency - accept request, validate in transaction, rollback if conflict
- Aligns with existing pattern used for room creation

**Implementation Pattern**:
```python
async def join_room(room_code: str, player_id: str) -> JoinResult:
    async with db.begin():  # Transaction ensures atomicity
        room = await db.get_room_for_update(room_code)  # Row-level lock
        if room.current_count >= room.max_capacity:
            raise RoomFullError()
        await db.add_participant(room_id, player_id, timestamp=datetime.utcnow())
        room.current_count += 1
        # Commit releases lock
    await broadcast_player_joined(room_code, player_id)
```

**Alternatives Considered**:
- Distributed lock (Redis): Over-engineered for SQLite single-writer model
- Queue system: Adds complexity, doesn't improve UX for edge case
- Client-side retry: Acceptable fallback after server rejects

**References**:
- SQLite isolation levels: https://www.sqlite.org/isolation.html
- Existing room creation logic: `backend/src/services/game_room_service.py`

---

### 2. Room Ownership Transfer Logic

**Decision**: Automatic transfer to earliest-joined human player based on `join_timestamp`

**Rationale**:
- Simple deterministic rule - no ambiguity or voting complexity
- `join_timestamp` already tracked for participants (clarification confirmed)
- Owner flag stored in `game_room_participants.is_owner` (indexed for fast lookups)
- Room dissolution when only AI remains prevents orphaned rooms

**Implementation Pattern**:
```python
async def transfer_ownership(room_id: int, leaving_owner_id: str):
    # Get next human player ordered by join_timestamp ASC
    next_owner = await db.query(GameRoomParticipant).filter(
        room_id=room_id,
        participant_type='human',
        player_id != leaving_owner_id
    ).order_by(join_timestamp.asc()).first()
    
    if next_owner:
        await db.update(next_owner, is_owner=True)
        await broadcast_ownership_transferred(room_id, next_owner.player_id)
    else:
        # Only AI agents remain
        await dissolve_room(room_id)
```

**Alternatives Considered**:
- Random selection: Non-deterministic, confusing for users
- Manual designation: Requires extra UI flow, delays transfer
- Preserve original owner: Prevents room from continuing after owner leaves

**Edge Cases Handled**:
- Owner leaves before game starts: Transfer to next human
- Owner leaves during game: Out of scope (game already in progress)
- All humans leave: Room dissolved immediately

---

### 3. AI Agent Naming Strategy

**Decision**: Sequential auto-generated names per room ("AI玩家1", "AI玩家2", etc.)

**Rationale**:
- Simple implementation - counter maintained in room state
- Consistent with clarification decision (session 2025-11-09)
- Names reset per room (avoid global collision concerns)
- i18n-ready pattern (prefix localizable, number universal)

**Implementation Pattern**:
```python
def generate_ai_name(room: GameRoom) -> str:
    room.ai_agent_counter += 1  # Atomic increment
    return f"AI玩家{room.ai_agent_counter}"
```

**Database Addition**:
```sql
ALTER TABLE game_rooms ADD COLUMN ai_agent_counter INTEGER DEFAULT 0;
```

**Alternatives Considered**:
- Custom naming by owner: Added complexity, scope creep
- Random names from pool: Risk of duplicates, harder to track
- Role-based naming: Game-specific, reduces flexibility

**i18n Notes**:
- Frontend can localize prefix: "AI玩家" (Chinese), "AI Player" (English), "AI ジョーヤー" (Japanese)
- Number stays universal: 1, 2, 3...

---

### 4. WebSocket Lobby Event Schema

**Decision**: Extend existing Socket.IO event pattern with typed lobby events

**Rationale**:
- Reuses established `python-socketio` infrastructure
- Room-based broadcasting already implemented for game events
- Event payload validation with Pydantic ensures type safety
- Aligns with Constitution Principle III (API Contracts)

**Event Definitions**:

```yaml
# AsyncAPI 2.6.0 specification
events:
  player_joined:
    payload:
      room_code: string
      player:
        id: string
        name: string
        avatar_url: string | null
        is_owner: boolean
      timestamp: datetime
  
  player_left:
    payload:
      room_code: string
      player_id: string
      timestamp: datetime
  
  ai_agent_added:
    payload:
      room_code: string
      ai_agent:
        id: string  # Generated UUID
        name: string  # e.g., "AI玩家1"
        participant_type: "ai"
      added_by: string  # Owner player_id
      timestamp: datetime
  
  ai_agent_removed:
    payload:
      room_code: string
      ai_agent_id: string
      removed_by: string  # Owner player_id
      timestamp: datetime
  
  ownership_transferred:
    payload:
      room_code: string
      previous_owner_id: string
      new_owner_id: string
      reason: "owner_left" | "manual_transfer"
      timestamp: datetime
```

**Broadcasting Pattern**:
```python
await sio.emit(
    'player_joined',
    payload,
    room=f"lobby:{room_code}"  # Only participants in this lobby
)
```

**Frontend Handling**:
```typescript
socket.on('player_joined', (data) => {
    lobbyStore.addParticipant(data.player)
    toast.success(`${data.player.name} joined the room`)
})
```

**Alternatives Considered**:
- REST polling: High latency, poor UX for real-time updates
- Server-Sent Events: One-way only, no client-to-server actions
- gRPC streaming: Over-engineered, adds new dependency

**Performance Notes**:
- Event payloads kept minimal (<500 bytes)
- Broadcast only to room participants (not global)
- Debouncing not needed (user actions are discrete, not continuous)

---

### 5. Disconnection Handling Strategy

**Decision**: Immediate slot release with rejoin capability (no state preservation)

**Rationale**:
- Aligns with clarification decision (session 2025-11-09)
- Simple implementation - no timer management or grace period tracking
- Rejoining treated as new join request (reduces state complexity)
- Room code provides easy rejoin path if slots available

**Implementation Pattern**:
```python
@sio.on('disconnect')
async def handle_disconnect(sid):
    player_id = session_map[sid]
    rooms = await get_active_rooms_for_player(player_id)
    for room in rooms:
        if room.status == 'Waiting':
            await leave_room(room.code, player_id)
            await broadcast_player_left(room.code, player_id)
    del session_map[sid]
```

**Rejoin Flow**:
1. Player disconnects → `disconnect` event fired → slot released → `player_left` broadcast
2. Player reconnects → opens app → enters room code → join request processed
3. If slots available → rejoin succeeds (treated as new participant)
4. If room full → error displayed

**Alternatives Considered**:
- 5-minute grace period: Adds complexity, holds slots unnecessarily
- State preservation: Requires session storage, conflicts with stateless rejoin
- Permanent slot reservation: Would prevent other players from joining

**Edge Case**: 
- Player disconnects/reconnects rapidly → Each rejoin is independent, no special handling needed
- Multiple tabs same user → Duplicate detection (FR-012) prevents multiple slots

---

### 6. Database Schema Modifications

**Decision**: Extend existing tables with minimal new columns, add indexes for performance

**Rationale**:
- Leverages existing `game_rooms` and `game_room_participants` tables
- Alembic migration ensures safe schema evolution
- Indexes on high-query columns (owner lookup, timestamp sorting)

**Migration Script** (`alembic/versions/XXXX_add_lobby_management.py`):

```python
def upgrade():
    # Add owner tracking to game_rooms
    op.add_column('game_rooms', 
        sa.Column('owner_id', sa.String(36), nullable=True))
    op.add_column('game_rooms',
        sa.Column('ai_agent_counter', sa.Integer, default=0))
    
    # Add participant metadata
    op.add_column('game_room_participants',
        sa.Column('is_owner', sa.Boolean, default=False))
    op.add_column('game_room_participants',
        sa.Column('join_timestamp', sa.DateTime, default=datetime.utcnow))
    
    # Indexes for fast queries
    op.create_index('idx_room_owner', 'game_rooms', ['owner_id'])
    op.create_index('idx_participant_room_time', 'game_room_participants', 
                    ['room_id', 'join_timestamp'])
    
    # Backfill existing rooms (set creator as owner)
    op.execute("""
        UPDATE game_rooms 
        SET owner_id = (
            SELECT player_id FROM game_room_participants 
            WHERE room_id = game_rooms.id 
            ORDER BY created_at ASC LIMIT 1
        )
        WHERE owner_id IS NULL
    """)
    
def downgrade():
    op.drop_index('idx_participant_room_time')
    op.drop_index('idx_room_owner')
    op.drop_column('game_room_participants', 'join_timestamp')
    op.drop_column('game_room_participants', 'is_owner')
    op.drop_column('game_rooms', 'ai_agent_counter')
    op.drop_column('game_rooms', 'owner_id')
```

**Performance Considerations**:
- `owner_id` indexed for fast permission checks
- `join_timestamp` indexed for ownership transfer queries
- Composite index on `(room_id, join_timestamp)` for ordered participant lists

---

### 7. Frontend State Management

**Decision**: New Pinia store (`lobby.ts`) for lobby-specific state with WebSocket integration

**Rationale**:
- Separates lobby concerns from game state (existing `game.ts` store)
- Reactive updates trigger UI changes automatically
- Centralized WebSocket event handling
- Aligns with Vue 3 + Pinia architecture pattern

**Store Structure**:
```typescript
// stores/lobby.ts
export const useLobbyStore = defineStore('lobby', {
  state: () => ({
    currentRoom: null as GameRoom | null,
    participants: [] as Participant[],
    isOwner: false,
    isJoining: false,
  }),
  
  actions: {
    async joinRoom(roomCode: string) {
      this.isJoining = true
      try {
        const response = await roomApi.joinRoom(roomCode)
        this.currentRoom = response.room
        this.participants = response.participants
        this.isOwner = response.is_owner
        lobbySocket.subscribe(roomCode)  // Start listening to events
      } finally {
        this.isJoining = false
      }
    },
    
    handlePlayerJoined(payload: PlayerJoinedEvent) {
      this.participants.push(payload.player)
    },
    
    handleOwnershipTransferred(payload: OwnershipTransferredEvent) {
      this.isOwner = (payload.new_owner_id === currentPlayerId)
      // Update participant list owner flags
    },
  },
})
```

**Alternatives Considered**:
- Extend game store: Creates tight coupling, harder to test
- Component-local state: Loses reactivity across components, duplicate logic
- Vuex: Deprecated in favor of Pinia for Vue 3

---

## Summary of Decisions

| Area | Decision | Key Benefit |
|------|----------|-------------|
| Concurrent Joins | SQLite transactions + timestamp ordering | Race-condition safe, simple |
| Ownership Transfer | Earliest-joined human player | Deterministic, no user input needed |
| AI Naming | Sequential per room ("AI玩家N") | Simple, i18n-ready |
| Real-time Events | Socket.IO room broadcasting | Reuses existing infrastructure |
| Disconnection | Immediate release, rejoin allowed | Simple, no grace period complexity |
| Database | Extend existing tables + indexes | Migration-safe, performant queries |
| Frontend State | Dedicated Pinia lobby store | Separation of concerns, reactive |

## Open Questions

**None** - All technical decisions finalized based on existing infrastructure and clarified requirements.

## References

- Existing codebase: `backend/src/services/game_room_service.py`
- SQLite concurrency: https://www.sqlite.org/wal.html
- python-socketio rooms: https://python-socketio.readthedocs.io/en/latest/server.html#rooms
- Pinia stores: https://pinia.vuejs.org/core-concepts/
- Constitutional principles: `.specify/memory/constitution.md`
