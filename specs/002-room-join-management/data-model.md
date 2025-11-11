# Data Model: Multiplayer Room Join & AI Agent Management

**Feature**: 002-room-join-management  
**Date**: 2025-11-09  
**Status**: Complete

## Overview

This document defines the data model extensions required for multiplayer room joining and AI agent management. All changes extend existing entities (`GameRoom`, `GameRoomParticipant`, `Player`) without introducing new top-level models.

---

## Entity: GameRoom (Extended)

**Purpose**: Represents a game room/lobby where players gather before starting a game

**Existing Attributes** (from 001-ai-game-platform):
- `id`: Integer (Primary Key)
- `code`: String(6) (Unique, indexed)
- `game_type_id`: Integer (Foreign Key → GameType)
- `status`: Enum('Waiting', 'In Progress', 'Completed')
- `max_players`: Integer
- `created_at`: DateTime
- `started_at`: DateTime (nullable)
- `completed_at`: DateTime (nullable)

**New Attributes**:
- `owner_id`: String(36) (Foreign Key → Player.id, indexed)
  - The player who created the room and has administrative privileges
  - Transfers to next participant when owner leaves
  - Nullable during migration (backfilled from first participant)
  
- `current_participant_count`: Integer (Default: 0)
  - Cached count of active participants (humans + AI)
  - Updated on join/leave operations
  - Used for capacity checks without expensive COUNT queries
  
- `ai_agent_counter`: Integer (Default: 0)
  - Sequential counter for AI agent naming within this room
  - Increments when AI agents added: "AI玩家1", "AI玩家2", etc.
  - Resets per room (not global)

**Relationships**:
- `owner` → Player (many-to-one via owner_id)
- `participants` → List[GameRoomParticipant] (one-to-many)
- `game_type` → GameType (many-to-one, existing)

**Validation Rules**:
- `code`: Must be 6 alphanumeric characters, uppercase
- `current_participant_count` ≤ `max_players` (enforced in service layer)
- `owner_id` must reference an active participant when room status is 'Waiting'
- `ai_agent_counter` ≥ 0

**State Transitions**:
```
Waiting → In Progress: When owner clicks "Start Game" (existing)
In Progress → Completed: When game ends (existing)
Waiting → Deleted: When room dissolved (owner leaves + only AI remain)
```

**Indexes**:
- `idx_room_code`: Unique index on `code` (existing)
- `idx_room_owner`: Index on `owner_id` (NEW) - for permission checks
- `idx_room_status`: Index on `status` (existing) - for listing active rooms

**Database Schema** (SQLAlchemy):
```python
class GameRoom(Base):
    __tablename__ = 'game_rooms'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(6), unique=True, nullable=False, index=True)
    game_type_id = Column(Integer, ForeignKey('game_types.id'), nullable=False)
    status = Column(Enum('Waiting', 'In Progress', 'Completed'), default='Waiting')
    max_players = Column(Integer, nullable=False)
    
    # NEW attributes
    owner_id = Column(String(36), ForeignKey('players.id'), nullable=True, index=True)
    current_participant_count = Column(Integer, default=0)
    ai_agent_counter = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    owner = relationship('Player', foreign_keys=[owner_id])
    participants = relationship('GameRoomParticipant', back_populates='room', cascade='all, delete-orphan')
    game_type = relationship('GameType')
```

---

## Entity: GameRoomParticipant (Extended)

**Purpose**: Junction table linking players (human or AI) to game rooms

**Existing Attributes** (from 001-ai-game-platform):
- `id`: Integer (Primary Key)
- `room_id`: Integer (Foreign Key → GameRoom.id)
- `player_id`: String(36) (Foreign Key → Player.id)
- `participant_type`: Enum('human', 'ai')
- `created_at`: DateTime

**New Attributes**:
- `is_owner`: Boolean (Default: False, indexed)
  - Indicates if this participant is the current room owner
  - Exactly one participant per room should have `is_owner=True` in 'Waiting' status
  - Updated when ownership transfers
  
- `join_timestamp`: DateTime (Default: utcnow(), indexed)
  - Tracks when participant joined the room
  - Used for ownership transfer ordering (earliest-joined becomes next owner)
  - Used for participant list display ordering

**Relationships**:
- `room` → GameRoom (many-to-one via room_id)
- `player` → Player (many-to-one via player_id)

**Validation Rules**:
- Unique constraint: `(room_id, player_id)` - player can't join same room twice
- `is_owner=True` count per room_id must be 0 or 1
- `participant_type` must be 'human' or 'ai'
- For `participant_type='human'`: player_id must reference real Player with guest/registered account
- For `participant_type='ai'`: player_id references generated AI Player record

**Constraints**:
```sql
UNIQUE (room_id, player_id)
CHECK (participant_type IN ('human', 'ai'))
```

**Indexes**:
- `idx_participant_room`: Index on `room_id` (existing) - for room participant queries
- `idx_participant_owner`: Index on `(room_id, is_owner)` (NEW) - for fast owner lookup
- `idx_participant_join_time`: Composite index on `(room_id, join_timestamp)` (NEW) - for ordered queries

**Database Schema** (SQLAlchemy):
```python
class GameRoomParticipant(Base):
    __tablename__ = 'game_room_participants'
    __table_args__ = (
        UniqueConstraint('room_id', 'player_id'),
        Index('idx_participant_room', 'room_id'),
        Index('idx_participant_owner', 'room_id', 'is_owner'),
        Index('idx_participant_join_time', 'room_id', 'join_timestamp'),
    )
    
    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey('game_rooms.id'), nullable=False)
    player_id = Column(String(36), ForeignKey('players.id'), nullable=False)
    participant_type = Column(Enum('human', 'ai'), nullable=False)
    
    # NEW attributes
    is_owner = Column(Boolean, default=False)
    join_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    room = relationship('GameRoom', back_populates='participants')
    player = relationship('Player')
```

**Business Logic**:
- When participant joins: `join_timestamp = now()`, `is_owner = (room.owner_id == player_id)`
- When owner leaves: Transfer `is_owner=True` to earliest `join_timestamp` where `participant_type='human'`
- When participant disconnects: Remove record, decrement `room.current_participant_count`

---

## Entity: Player (No Changes)

**Purpose**: Represents a player (human or AI agent) in the system

**Existing Attributes** (from 001-ai-game-platform):
- `id`: String(36) (Primary Key, UUID)
- `name`: String(50)
- `player_type`: Enum('guest', 'registered', 'ai')
- `avatar_url`: String(255) (nullable)
- `created_at`: DateTime

**Usage for AI Agents**:
- AI agents added to lobby create Player records with `player_type='ai'`
- AI agent naming: `name` field populated with "AI玩家{counter}" pattern
- No authentication credentials needed for AI players
- AI players can participate identically to human players in game logic

---

## Event Payloads (WebSocket)

### PlayerJoinedEvent

```typescript
interface PlayerJoinedEvent {
  room_code: string;
  player: {
    id: string;           // Player.id
    name: string;         // Player.name
    avatar_url: string | null;
    participant_type: 'human' | 'ai';
    is_owner: boolean;
    join_timestamp: string;  // ISO 8601
  };
  timestamp: string;      // Server time, ISO 8601
}
```

### PlayerLeftEvent

```typescript
interface PlayerLeftEvent {
  room_code: string;
  player_id: string;
  timestamp: string;
}
```

### AIAgentAddedEvent

```typescript
interface AIAgentAddedEvent {
  room_code: string;
  ai_agent: {
    id: string;           // Generated Player.id
    name: string;         // e.g., "AI玩家1"
    participant_type: 'ai';
    is_owner: false;
    join_timestamp: string;
  };
  added_by: string;       // Owner player_id
  timestamp: string;
}
```

### AIAgentRemovedEvent

```typescript
interface AIAgentRemovedEvent {
  room_code: string;
  ai_agent_id: string;
  removed_by: string;     // Owner player_id
  timestamp: string;
}
```

### OwnershipTransferredEvent

```typescript
interface OwnershipTransferredEvent {
  room_code: string;
  previous_owner_id: string;
  new_owner_id: string;
  new_owner_name: string;
  reason: 'owner_left' | 'manual_transfer';
  timestamp: string;
}
```

---

## Data Flow Examples

### Example 1: Player Joins Room

**Input**: POST /api/v1/rooms/{code}/join with `player_id`

**Database Changes**:
1. Validate room exists, status='Waiting', not full
2. Create `GameRoomParticipant` record:
   ```python
   participant = GameRoomParticipant(
       room_id=room.id,
       player_id=player_id,
       participant_type='human',
       is_owner=False,
       join_timestamp=datetime.utcnow()
   )
   ```
3. Increment `room.current_participant_count`
4. Commit transaction

**WebSocket Broadcast**:
```python
await sio.emit('player_joined', PlayerJoinedEvent(...), room=f"lobby:{code}")
```

**Result**: Player appears in lobby, all participants notified

---

### Example 2: Owner Leaves, Ownership Transfers

**Input**: DELETE /api/v1/rooms/{code}/participants/{owner_id}

**Database Changes**:
1. Find departing owner participant
2. Query next human participant:
   ```sql
   SELECT * FROM game_room_participants
   WHERE room_id = ? AND participant_type = 'human' AND player_id != ?
   ORDER BY join_timestamp ASC
   LIMIT 1
   ```
3. If found:
   - Set departing owner `is_owner=False`
   - Set next owner `is_owner=True`
   - Update `room.owner_id = next_owner.player_id`
4. If not found (only AI remain):
   - Delete room and all participants (CASCADE)
5. Delete departing owner participant
6. Decrement `room.current_participant_count`

**WebSocket Broadcasts**:
```python
await sio.emit('player_left', PlayerLeftEvent(...), room=f"lobby:{code}")
if next_owner:
    await sio.emit('ownership_transferred', OwnershipTransferredEvent(...), room=f"lobby:{code}")
else:
    await sio.emit('room_dissolved', {...}, room=f"lobby:{code}")
```

---

### Example 3: Owner Adds AI Agent

**Input**: POST /api/v1/rooms/{code}/ai-agents (authenticated as owner)

**Database Changes**:
1. Verify requester is owner (`room.owner_id == player_id`)
2. Check room not full (`current_participant_count < max_players`)
3. Increment `room.ai_agent_counter`
4. Create AI Player:
   ```python
   ai_player = Player(
       id=str(uuid.uuid4()),
       name=f"AI玩家{room.ai_agent_counter}",
       player_type='ai'
   )
   ```
5. Create AI participant:
   ```python
   participant = GameRoomParticipant(
       room_id=room.id,
       player_id=ai_player.id,
       participant_type='ai',
       is_owner=False,
       join_timestamp=datetime.utcnow()
   )
   ```
6. Increment `room.current_participant_count`

**WebSocket Broadcast**:
```python
await sio.emit('ai_agent_added', AIAgentAddedEvent(...), room=f"lobby:{code}")
```

---

## Migration Checklist

- [ ] Create Alembic migration script
- [ ] Add `owner_id`, `current_participant_count`, `ai_agent_counter` to `game_rooms`
- [ ] Add `is_owner`, `join_timestamp` to `game_room_participants`
- [ ] Create indexes: `idx_room_owner`, `idx_participant_owner`, `idx_participant_join_time`
- [ ] Backfill `owner_id` from existing rooms (first participant)
- [ ] Backfill `current_participant_count` from COUNT queries
- [ ] Add unique constraint `(room_id, player_id)` if not exists
- [ ] Test migration on staging database
- [ ] Verify rollback script works

---

## Summary

### New Columns: 5
- `game_rooms.owner_id`
- `game_rooms.current_participant_count`
- `game_rooms.ai_agent_counter`
- `game_room_participants.is_owner`
- `game_room_participants.join_timestamp`

### New Indexes: 3
- `idx_room_owner` on `game_rooms(owner_id)`
- `idx_participant_owner` on `game_room_participants(room_id, is_owner)`
- `idx_participant_join_time` on `game_room_participants(room_id, join_timestamp)`

### New Constraints: 1
- UNIQUE `(room_id, player_id)` on `game_room_participants`

### Event Schemas: 5
- PlayerJoinedEvent
- PlayerLeftEvent
- AIAgentAddedEvent
- AIAgentRemovedEvent
- OwnershipTransferredEvent

All changes are backward-compatible via migration with backfill logic.
