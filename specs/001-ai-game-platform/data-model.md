# Data Model: AI-Powered Tabletop Game Platform

**Date**: 2025-11-08
**Database**: SQLite 3.35+
**ORM**: SQLAlchemy (async with aiosqlite)

## Entity Relationship Overview

```
Player (1) ──── (N) GameRoomParticipant (N) ──── (1) GameRoom
   │                                                   │
   │                                                   │
   │                                              (1) GameType
   │
   │
(1) PlayerProfile
   │
   │
(N) GameSession (historical record)
```

---

## Core Entities

### 1. Player

Represents both guest and registered players.

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique player identifier |
| username | VARCHAR(50) | NOT NULL, UNIQUE | Display name (auto-generated for guests) |
| is_guest | BOOLEAN | NOT NULL, DEFAULT TRUE | Guest vs permanent account |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Account creation time |
| last_active | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last activity timestamp |
| expires_at | TIMESTAMP | NULL | Guest account expiration (30 days) |

**Validation Rules**:
- Username: 2-50 characters, alphanumeric + underscore + Chinese characters
- Guest usernames: Auto-generated format `Guest_形容词_动物` (e.g., `Guest_快乐_熊猫`)
- expires_at: NULL for permanent accounts, NOW() + 30 days for guests

**State Transitions**:
- Guest → Permanent: upgrade_to_permanent(username) → sets is_guest=FALSE, expires_at=NULL

**Indexes**:
- PRIMARY KEY (id)
- UNIQUE (username)
- INDEX (is_guest, expires_at) -- for cleanup job
- INDEX (last_active) -- for activity tracking

---

### 2. GameRoom

Represents an active or completed game session container.

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique room identifier |
| code | VARCHAR(8) | NOT NULL, UNIQUE | Shareable room code (e.g., "ABCD1234") |
| game_type_id | UUID | FK → GameType.id | Type of game (Crime Scene) |
| status | ENUM | NOT NULL | Waiting, In Progress, Completed |
| max_players | INTEGER | NOT NULL, CHECK (4-8) | Maximum player count |
| min_players | INTEGER | NOT NULL, CHECK (4-8) | Minimum to start |
| created_by | UUID | FK → Player.id | Room creator |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Room creation time |
| started_at | TIMESTAMP | NULL | Game start time |
| completed_at | TIMESTAMP | NULL | Game end time |

**Validation Rules**:
- code: 8 alphanumeric characters, uppercase
- status: One of ['Waiting', 'In Progress', 'Completed']
- max_players >= min_players
- Waiting rooms accept joins; others reject

**State Transitions**:
```
Waiting → In Progress: When start_game() called (min_players met)
In Progress → Completed: When game_over() called (win condition met)
```

**Lifecycle**:
1. Created in 'Waiting' status
2. Players join until min_players reached
3. AI agents fill remaining slots if needed
4. Transitions to 'In Progress'
5. Game plays out
6. Transitions to 'Completed'
7. Room archived after inactivity

**Indexes**:
- PRIMARY KEY (id)
- UNIQUE (code)
- INDEX (status, created_at) -- for room listing
- INDEX (game_type_id) -- for filtering by game

---

### 3. GameRoomParticipant

Join table linking players and AI agents to game rooms.

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique participation record |
| game_room_id | UUID | FK → GameRoom.id | Associated game room |
| player_id | UUID | FK → Player.id, NULL | Human player (NULL for AI) |
| is_ai_agent | BOOLEAN | NOT NULL, DEFAULT FALSE | AI vs human |
| ai_personality | VARCHAR(50) | NULL | AI personality type if AI agent |
| joined_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Join timestamp |
| left_at | TIMESTAMP | NULL | Disconnect/leave timestamp |
| replaced_by_ai | BOOLEAN | DEFAULT FALSE | Was replaced by AI after disconnect |

**Validation Rules**:
- Either player_id IS NOT NULL OR is_ai_agent = TRUE
- ai_personality required when is_ai_agent = TRUE

**Business Logic**:
- Human disconnects: left_at set, 5-minute grace period
- After 5 minutes: replaced_by_ai = TRUE, new AI participant created
- AI agents: player_id = NULL, is_ai_agent = TRUE

**Indexes**:
- PRIMARY KEY (id)
- INDEX (game_room_id, left_at) -- for active participants
- INDEX (player_id) -- for player's game history

---

### 4. GameType

Game catalog (Crime Scene, future games).

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique game type identifier |
| name | VARCHAR(100) | NOT NULL, UNIQUE | Game name (e.g., "犯罪现场") |
| slug | VARCHAR(50) | NOT NULL, UNIQUE | URL-friendly name |
| description | TEXT | NOT NULL | Game description |
| rules_summary | TEXT | NOT NULL | Brief rules overview |
| min_players | INTEGER | NOT NULL | Minimum players required |
| max_players | INTEGER | NOT NULL | Maximum players allowed |
| avg_duration_minutes | INTEGER | NOT NULL | Estimated play time |
| is_available | BOOLEAN | NOT NULL, DEFAULT FALSE | Is game playable? |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Record creation |

**Validation Rules**:
- slug: lowercase, alphanumeric + hyphens
- min_players <= max_players
- Only Crime Scene has is_available = TRUE initially

**Static Data** (seed):
```sql
INSERT INTO game_types (name, slug, min_players, max_players, avg_duration_minutes, is_available)
VALUES ('犯罪现场', 'crime-scene', 4, 8, 60, TRUE);
```

**Indexes**:
- PRIMARY KEY (id)
- UNIQUE (name)
- UNIQUE (slug)
- INDEX (is_available) -- for game library filtering

---

### 5. GameState

Current state of an in-progress game (separate from GameRoom for size).

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique state identifier |
| game_room_id | UUID | FK → GameRoom.id, UNIQUE | One state per room |
| current_phase | VARCHAR(50) | NOT NULL | Game phase (Setup, Investigation, etc.) |
| current_turn_player_id | UUID | FK → Player.id, NULL | Current turn player (NULL for AI) |
| turn_number | INTEGER | NOT NULL, DEFAULT 1 | Turn counter |
| game_data | JSONB | NOT NULL | Game-specific state |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last state update |

**Validation Rules**:
- current_phase: Game-specific enum (CrimeScene: Setup, Investigation, Accusation, Resolution)
- game_data structure validated by game engine

**Game Data Structure** (Crime Scene example):
```json
{
  "phase": "Investigation",
  "locations": [...],
  "evidence": [...],
  "player_hands": {
    "player_id": ["card1", "card2"]
  },
  "clues_revealed": [...],
  "accusations_made": [],
  "winner": null
}
```

**Note**: SQLite stores JSON as TEXT. Use SQLAlchemy's JSON type for automatic serialization.

**Indexes**:
- PRIMARY KEY (id)
- UNIQUE (game_room_id)
- INDEX (updated_at) -- for stale state cleanup

---

### 6. GameSession

Historical record of completed games.

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique session identifier |
| game_room_id | UUID | FK → GameRoom.id | Associated game room |
| game_type_id | UUID | FK → GameType.id | Game type played |
| started_at | TIMESTAMP | NOT NULL | Game start time |
| completed_at | TIMESTAMP | NOT NULL | Game end time |
| winner_id | UUID | FK → Player.id, NULL | Winning player (NULL for tie) |
| duration_minutes | INTEGER | NOT NULL | Actual play time |
| participants_count | INTEGER | NOT NULL | Total players (human + AI) |
| ai_agents_count | INTEGER | NOT NULL | Number of AI agents |
| final_state | JSONB | NOT NULL | Game ending state |

**Validation Rules**:
- completed_at > started_at
- duration_minutes >= 0
- participants_count = players + ai_agents_count

**Business Logic**:
- Created when GameRoom transitions to 'Completed'
- Used for player statistics and analytics
- Includes snapshot of final game state for review

**Indexes**:
- PRIMARY KEY (id)
- INDEX (game_type_id, completed_at) -- for game history
- INDEX (winner_id) -- for player stats
- INDEX (started_at) -- for analytics queries

---

### 7. PlayerProfile

Extended player information and statistics.

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| player_id | UUID | PK, FK → Player.id | One profile per player |
| total_games | INTEGER | NOT NULL, DEFAULT 0 | Games played count |
| total_wins | INTEGER | NOT NULL, DEFAULT 0 | Games won count |
| favorite_game_id | UUID | FK → GameType.id, NULL | Most played game |
| ui_preferences | JSONB | NULL | UI settings (theme, notifications) |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last profile update |

**Validation Rules**:
- total_wins <= total_games
- ui_preferences structure: `{"theme": "light|dark", "notifications": true|false}`

**Computed Fields**:
- win_rate: (total_wins / total_games) * 100

**Business Logic**:
- Created automatically when player upgrades from guest
- Updated after each completed game
- Used for player profile display

**Indexes**:
- PRIMARY KEY (player_id)
- INDEX (total_games DESC) -- for leaderboards (future)

---

## Data Lifecycle Management

### Guest Account Cleanup

**Job**: Daily cron job to purge expired guest accounts

```sql
DELETE FROM players 
WHERE is_guest = TRUE 
  AND expires_at < NOW();
```

**Impact**: Cascades to related records via foreign keys

---

### Game Room Archival

**Job**: Hourly job to clean up old completed rooms

```sql
UPDATE game_rooms 
SET status = 'Archived' 
WHERE status = 'Completed' 
  AND completed_at < NOW() - INTERVAL '7 days';
```

**Retention**: Keep completed games for 7 days before archival

---

## Database Migrations

**Tool**: Alembic (SQLAlchemy migration tool)

**Migration Strategy**:
1. Initial schema creation
2. Seed data (GameType for Crime Scene)
3. Version all schema changes
4. Rollback support for failed deployments

**SQLite Considerations**:
- ALTER TABLE limitations: Some operations require table recreation
- Alembic handles this automatically via batch operations
- Always backup database file before major migrations

**Example Migration**:
```bash
# Create migration
alembic revision -m "create initial schema"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1

# Backup database before migration
cp vbrpg.db vbrpg.db.backup
```

---

## Performance Considerations

### Indexing Strategy
- Primary keys: All tables use UUID (stored as TEXT in SQLite)
- Foreign keys: All FKs indexed
- Query patterns: Index commonly filtered/sorted columns
- Composite indexes: For multi-column WHERE clauses

### SQLite Optimization
- Enable WAL mode: `PRAGMA journal_mode=WAL` for concurrent reads
- Increase cache size: `PRAGMA cache_size=-64000` (64MB)
- Enable foreign keys: `PRAGMA foreign_keys=ON`
- Use connection pooling via SQLAlchemy

### Application-Level Caching
- In-memory cache for active GameRoom and GameState
- Python LRU cache for game library (rarely changes)
- No external cache server needed for MVP scale

### Performance Limits
- SQLite handles 50 concurrent game sessions easily
- WAL mode: Multiple readers + one writer
- Consider PostgreSQL if scale exceeds 1000 concurrent users

---

## Data Integrity Constraints

### Foreign Key Cascade Rules

```sql
-- Prevent orphaned game rooms
ALTER TABLE game_rooms 
ADD CONSTRAINT fk_created_by 
FOREIGN KEY (created_by) 
REFERENCES players(id) 
ON DELETE SET NULL;

-- Clean up participants when room deleted
ALTER TABLE game_room_participants 
ADD CONSTRAINT fk_game_room 
FOREIGN KEY (game_room_id) 
REFERENCES game_rooms(id) 
ON DELETE CASCADE;

-- Preserve game sessions even if room deleted
ALTER TABLE game_sessions 
ADD CONSTRAINT fk_game_room 
FOREIGN KEY (game_room_id) 
REFERENCES game_rooms(id) 
ON DELETE SET NULL;
```

### Check Constraints

```sql
-- Ensure valid player counts
ALTER TABLE game_rooms 
ADD CONSTRAINT chk_player_counts 
CHECK (min_players <= max_players AND min_players >= 4 AND max_players <= 8);

-- Ensure valid timestamps
ALTER TABLE game_sessions 
ADD CONSTRAINT chk_session_times 
CHECK (completed_at > started_at);

-- Ensure valid stats
ALTER TABLE player_profiles 
ADD CONSTRAINT chk_win_rate 
CHECK (total_wins <= total_games);
```

---

## SQLAlchemy Models Preview

```python
# models/player.py
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from uuid import uuid4

class Player(Base):
    __tablename__ = "players"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String(50), unique=True)
    is_guest: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    profile: Mapped["PlayerProfile"] = relationship(back_populates="player", uselist=False)
    game_participations: Mapped[list["GameRoomParticipant"]] = relationship(back_populates="player")

# models/game_room.py
class GameRoom(Base):
    __tablename__ = "game_rooms"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    code: Mapped[str] = mapped_column(String(8), unique=True)
    game_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("game_types.id"))
    status: Mapped[str] = mapped_column(String(20))  # Enum stored as TEXT
    # ... other fields
    
    # Relationships
    game_type: Mapped["GameType"] = relationship()
    participants: Mapped[list["GameRoomParticipant"]] = relationship(back_populates="game_room")
    game_state: Mapped["GameState" | None] = relationship(back_populates="game_room", uselist=False)
```

**SQLite-specific notes**:
- UUID stored as String(36) instead of native UUID type
- ENUM stored as String with application-level validation
- JSON stored as TEXT, automatically serialized by SQLAlchemy
- DateTime stored as TEXT in ISO format

---

## Summary

**Total Entities**: 7 core entities
**Relationships**: 6 foreign key relationships
**Indexes**: 20+ strategic indexes
**Validation**: Check constraints + application-level validation
**Lifecycle**: Automated cleanup for guest accounts and archived rooms

**Next Step**: Define API contracts based on this data model.
