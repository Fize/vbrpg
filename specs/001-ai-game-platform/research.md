# Research Findings: AI-Powered Tabletop Game Platform

**Date**: 2025-11-08
**Purpose**: Resolve technical uncertainties identified in Technical Context

## 1. WebSocket Library Selection (Backend)

**Decision**: Use `python-socketio` with FastAPI integration

**Rationale**:
- Native FastAPI integration via `python-socketio[asyncio]`
- Socket.IO protocol provides automatic reconnection handling (critical for 5-minute reconnection window requirement)
- Room/namespace support ideal for game room isolation
- Fallback transport options (long-polling) for problematic networks
- Large community and extensive documentation
- Built-in event-based architecture fits game state broadcasting

**Alternatives Considered**:
- `websockets`: Lower-level, requires manual reconnection logic, no room abstraction
- `fastapi-websocket-pubsub`: Adds pub/sub complexity unnecessary for direct room broadcasting

**Implementation Notes**:
- Use Socket.IO rooms to map to game rooms
- Leverage automatic reconnection for the 5-minute window requirement
- Event names: `game_state_update`, `player_action`, `ai_turn`, `game_error`

---

## 2. WebSocket Client Library (Frontend)

**Decision**: Use `socket.io-client` (official Socket.IO JavaScript client)

**Rationale**:
- Official client for Socket.IO server compatibility
- Automatic reconnection with exponential backoff
- Event-based API matches backend pattern
- TypeScript support for type safety
- Handles connection state management
- ~50KB gzipped (acceptable for game application)

**Alternatives Considered**:
- Native WebSocket API: No automatic reconnection, manual room management
- `ws`: Node.js only, not browser-compatible

**Implementation Notes**:
- Configure reconnection attempts within 5-minute window
- Handle connection state in Pinia store
- Display connection status to users

---

## 3. Database Selection

**Decision**: SQLite 3.35+

**Rationale**:
- Zero-configuration embedded database (no separate server process)
- Perfect for MVP with 200 concurrent users and 50 game sessions
- ACID compliance for game state consistency
- JSON1 extension for flexible game state storage (Crime Scene specific data)
- Excellent Python ecosystem support (SQLAlchemy with aiosqlite)
- Simple deployment (single file database)
- WAL mode for improved concurrent write performance
- Built-in full-text search capabilities
- No additional infrastructure required

**Alternatives Considered**:
- PostgreSQL: Overkill for initial scale, requires separate database server
- MongoDB: Unnecessary complexity, weaker consistency guarantees for game state
- Redis: Fast but not suitable as primary store, better as cache (not needed for MVP)

**Implementation Notes**:
- Use SQLAlchemy ORM with async support (aiosqlite)
- Enable WAL mode: `PRAGMA journal_mode=WAL` for concurrent access
- JSON columns for game-specific state (flexible for future games)
- Single database file: `vbrpg.db` in data directory
- Backup strategy: Simple file copy or SQLite backup API

**Schema Highlights**:
- players: id, username, is_guest, created_at, last_active
- game_rooms: id, code, status (enum), game_type, max_players, created_at
- game_sessions: id, room_id, start_time, end_time, winner_id, game_data (JSON)
- player_stats: player_id, games_played, games_won, favorite_game

**Performance Considerations**:
- WAL mode allows multiple concurrent readers with one writer
- Sufficient for 50 concurrent game sessions
- In-memory caching at application level (no Redis needed)
- Connection pooling via SQLAlchemy

**Migration Path** (if needed in future):
- SQLAlchemy abstractions make it easy to migrate to PostgreSQL
- Export/import tools readily available
- Consider migration if scale exceeds 1000 concurrent users

---

## 4. End-to-End Testing Framework

**Decision**: Playwright

**Rationale**:
- Official Microsoft support, active development
- Multi-browser testing (Chromium, Firefox, WebKit)
- Auto-waiting reduces flakiness
- Network interception for mocking LLM responses
- Video/screenshot capture for debugging
- WebSocket support for real-time testing
- Better WebSocket debugging than Cypress
- TypeScript-first design

**Alternatives Considered**:
- Cypress: Limited multi-browser support, weaker WebSocket testing
- Selenium: Older architecture, more setup complexity

**Implementation Notes**:
- Test critical paths: game creation, joining, AI agent behavior, reconnection
- Mock LLM service for deterministic tests
- Use fixtures for common game states
- Parallel test execution for faster CI

---

## 5. LLM Integration Architecture

**Decision**: LangChain with OpenAI API (with adapter pattern for flexibility)

**Rationale**:
- LangChain provides:
  - Prompt templates for character roles
  - Memory management for conversation context
  - Chain abstractions for multi-step reasoning
  - Retry and error handling utilities
- OpenAI API for initial implementation (GPT-4 or GPT-3.5-turbo)
- Adapter pattern allows switching providers without code changes
- Streaming responses for progressive AI decisions

**Alternatives Considered**:
- Direct API calls: Requires manual prompt management and retry logic
- Anthropic Claude: Similar capabilities, but less ecosystem support
- Local models (Ollama): Deployment complexity, lower quality for conversational gameplay

**Implementation Notes**:
```python
# Adapter pattern
class LLMProvider(ABC):
    @abstractmethod
    async def generate_response(self, prompt: str, context: dict) -> str:
        pass

class OpenAIProvider(LLMProvider):
    # OpenAI implementation with LangChain
    
class AnthropicProvider(LLMProvider):
    # Future: Claude implementation
```

**Failure Handling** (per spec clarification):
- Timeout: 2 minutes max wait
- On failure: Pause game, notify players, terminate if unresolved
- Log all LLM interactions for debugging

---

## 6. Real-Time State Synchronization Strategy

**Decision**: Event-driven state broadcasts with optimistic updates

**Rationale**:
- Server as single source of truth (SSOT)
- Client optimistic updates for perceived responsiveness
- Server validates all actions before broadcasting
- Conflict resolution: server state always wins

**Architecture**:
```
Player Action → Client optimistic update → Server validation → Broadcast to all → Client reconciliation
```

**State Synchronization Events**:
- `player_joined`: New player enters room
- `player_left`: Player disconnects
- `game_started`: Transition to In Progress
- `turn_changed`: Next player/AI turn
- `game_action`: Player makes move
- `ai_thinking`: AI agent processing (show spinner)
- `ai_action`: AI agent completed move
- `game_ended`: Game completed

**Implementation Notes**:
- Use Socket.IO rooms for efficient broadcasting
- Include state version/timestamp for conflict detection
- Delta updates where possible (not full state)
- Compress large state objects (game board)

---

## 7. Guest Account Implementation

**Decision**: UUID-based guest identifiers with HTTP-only cookies

**Rationale**:
- UUID v4 for guest player IDs (collision-resistant)
- HTTP-only, Secure, SameSite cookies for session management
- No password for guests (frictionless entry)
- Simple upgrade path: guest_id → permanent account
- 30-day TTL on guest data (automated cleanup job)

**Implementation Notes**:
```python
# Guest creation
guest_id = uuid.uuid4()
guest_username = f"Guest_{random_adjective}_{random_animal}"

# Upgrade flow
def upgrade_guest_to_permanent(guest_id: UUID, username: str):
    # Transfer game history, stats
    # Mark account as permanent
    # Remove expiration
```

**Security Considerations** (minimal per spec):
- Basic input validation on guest usernames
- Rate limiting on guest account creation (prevent spam)
- No sensitive data stored for guests

---

## 8. Crime Scene Game Rules Engine

**Decision**: Rule-based state machine with game-specific modules

**Rationale**:
- State machine pattern for game flow (phases, turns)
- Modular design for future game additions
- Validation layer for all moves
- Pluggable AI agent decision-making

**Architecture**:
```python
class GameEngine(ABC):
    @abstractmethod
    def validate_action(self, action: Action, state: GameState) -> bool
    
    @abstractmethod
    def apply_action(self, action: Action, state: GameState) -> GameState
    
    @abstractmethod
    def get_valid_actions(self, state: GameState, player: Player) -> List[Action]

class CrimeSceneEngine(GameEngine):
    # Crime Scene specific rules
```

**Game State Components**:
- Phase: Setup, Investigation, Accusation, Resolution
- Turn: Current player/AI
- Players: Roles, hand, position
- Board: Locations, evidence, clues
- History: Move log for replay/debugging

---

## 9. Performance Optimization Strategy

**Decision**: Application-level caching with in-memory storage (no external cache)

**Rationale**:
- Python dictionary or LRU cache for active game room states
- Sufficient for MVP scale (50 concurrent sessions)
- No additional infrastructure complexity
- SQLite with WAL mode handles concurrent reads efficiently
- Reduces deployment dependencies

**Implementation Notes**:
- Use Python `functools.lru_cache` for read-heavy data (game library)
- In-memory dict for active game states with TTL cleanup
- SQLite for persistent storage with good read performance
- Connection pooling via SQLAlchemy

**Caching Strategy**:
```python
from functools import lru_cache
from datetime import datetime, timedelta

# Cache game library (rarely changes)
@lru_cache(maxsize=128)
async def get_game_types():
    return await db.query(GameType).all()

# In-memory active game states
class GameStateCache:
    def __init__(self, ttl_seconds=3600):
        self._cache = {}  # room_id -> (state, timestamp)
        self._ttl = timedelta(seconds=ttl_seconds)
    
    def get(self, room_id):
        if room_id in self._cache:
            state, timestamp = self._cache[room_id]
            if datetime.utcnow() - timestamp < self._ttl:
                return state
            del self._cache[room_id]
        return None
    
    def set(self, room_id, state):
        self._cache[room_id] = (state, datetime.utcnow())
```

**Monitoring** (per spec - basic logging):
- Response time tracking
- In-memory cache hit rates
- WebSocket connection counts
- LLM API latency
- SQLite query performance via SQLAlchemy logging

**Future Optimization** (if needed):
- Add Redis only if scale exceeds 500 concurrent sessions
- Consider read replicas if needed (SQLite limitations)

---

## 10. Deployment Strategy

**Decision**: Simple single-server deployment with optional Docker

**Rationale**:
- SQLite embedded database simplifies deployment (no separate DB server)
- Single binary deployment option
- Docker optional for consistency (not required)
- Minimal infrastructure for MVP

**Deployment Options**:

### Option A: Direct Deployment (Simplest)
```bash
# Backend runs as systemd service
# Frontend served via Nginx
# SQLite database in /var/lib/vbrpg/vbrpg.db
```

### Option B: Docker (Optional)
```yaml
services:
  backend:
    # FastAPI + Socket.IO server
    volumes:
      - ./data:/app/data  # SQLite database
  frontend:
    # Nginx serving Vue build
```

**Deployment Notes**:
- Environment variables for LLM API keys
- SQLite database file persistence via volume mount
- Nginx reverse proxy for frontend + backend + WebSocket
- Automated database migrations (Alembic)
- Simple backup: copy SQLite file

**Backup Strategy**:
```bash
# Simple file-based backup
sqlite3 vbrpg.db ".backup 'backup.db'"

# Or use file copy while app running (WAL mode safe)
cp vbrpg.db vbrpg.db.backup
```

---

## Summary of Technical Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| Backend Language | Python 3.11+ | FastAPI + LangChain ecosystem |
| Backend Framework | FastAPI | Async support, WebSocket, auto-docs |
| Real-time Comm | python-socketio | Socket.IO with reconnection |
| Frontend Framework | Vue 3 | Reactive, composition API, ecosystem |
| UI Library | Element-Plus | Chinese language support, rich components |
| Frontend Client | socket.io-client | Official Socket.IO client |
| Database | SQLite 3.35+ | Embedded, zero-config, sufficient for scale |
| ORM | SQLAlchemy (async) | Type safety, migrations, aiosqlite |
| Cache | In-memory (Python) | No external dependencies, simple |
| LLM Integration | LangChain + OpenAI | Prompt management, flexibility |
| Testing (Backend) | pytest + pytest-asyncio | Async test support |
| Testing (Frontend) | Vitest | Vite integration, fast |
| E2E Testing | Playwright | Multi-browser, WebSocket support |
| Deployment | Direct/Docker | Simple, minimal infrastructure |

**All NEEDS CLARIFICATION items resolved. Ready for Phase 1: Design & Contracts.**
