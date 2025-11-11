# Implementation Plan: Multiplayer Room Join & AI Agent Management

**Branch**: `002-room-join-management` | **Date**: 2025-11-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-room-join-management/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement multiplayer room joining functionality and AI agent management controls for game lobbies. Players can join existing game rooms using 6-character room codes, see other participants in real-time, and wait together before game start. Room owners gain manual control over AI agent slots, allowing them to add or remove AI players to balance games for the number of human participants. All lobby changes (joins, leaves, AI additions/removals) are synchronized in real-time across all clients within 1 second. The system handles edge cases including concurrent joins, ownership transfer when owners leave, and disconnection/reconnection scenarios.

## Technical Context

**Language/Version**: Python 3.11+ (backend), JavaScript ES2022+ (frontend)
**Primary Dependencies**: 
- Backend: FastAPI 0.109+ (web framework), python-socketio 5.11+ (WebSocket with Socket.IO protocol), SQLAlchemy 2.0+ (async ORM)
- Frontend: Vue 3 (UI framework), Element-Plus (UI components), socket.io-client (WebSocket client), Pinia (state management)
**Storage**: SQLite 3.35+ with WAL mode (existing database, add new columns/tables)
**Testing**: pytest + pytest-asyncio (backend unit/integration), Vitest (frontend unit), Playwright (E2E)
**Target Platform**: Web browsers (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+), Linux/Docker server deployment
**Project Type**: Web application (separate backend + frontend)
**Performance Goals**: 
- Room join operations complete within 5 seconds (95th percentile)
- Real-time lobby updates delivered within 1 second (95th percentile)
- AI agent add/remove actions complete within 3 seconds
- Support 50 concurrent game rooms with simultaneous join/leave activity
**Constraints**: 
- Must maintain backward compatibility with existing room creation flow
- Reuse existing WebSocket infrastructure (no new connection protocols)
- Room codes remain 6-character alphanumeric (existing system)
- Database changes must be migration-safe (Alembic)
- No disruption to games already in progress
**Scale/Scope**: 
- Extends existing 50 concurrent rooms capacity (no increase needed)
- Supports up to 8 players per room (game type dependent)
- Real-time updates for all participants in affected rooms only
- AI agent management exclusive to room owners

**All technical decisions leverage existing infrastructure. No new technology required.**

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Test-First Development ✅ COMPLIANT

**Status**: Will follow TDD cycle for all components
- Unit tests for new models (GameRoomParticipant extensions, ownership logic)
- Integration tests for join/leave API endpoints and WebSocket events
- Contract tests for lobby update event schemas
- E2E tests for complete user journeys (join room, manage AI agents, real-time updates)

**Plan**: Tests written in Phase 2, approved before implementation begins

### Principle II: Component Isolation & Service Boundaries ✅ COMPLIANT

**Status**: Maintains existing backend/frontend separation
- Backend: New API endpoints + WebSocket event handlers
- Frontend: New Vue components for join UI + AI management controls
- No new services introduced; extends existing GameRoomService
- Clear contract boundaries via OpenAPI (REST) and AsyncAPI (WebSocket)

### Principle III: API Contracts & Type Safety ✅ COMPLIANT

**Status**: All new endpoints and events will be contract-defined
- REST API: POST /api/v1/rooms/{code}/join, DELETE /api/v1/rooms/{code}/participants/{player_id}
- WebSocket events: player_joined, player_left, ai_agent_added, ai_agent_removed, ownership_transferred
- Request/response schemas with Pydantic validation
- TypeScript types generated for frontend from OpenAPI spec
- Contract tests verify both sides

**Deliverable**: contracts/ directory with OpenAPI and AsyncAPI specs

### Principle IV: Real-Time State Synchronization ✅ COMPLIANT

**Status**: Extends existing WebSocket infrastructure for lobby state
- Backend maintains authoritative lobby state in database
- All lobby changes broadcast immediately to room participants
- 1-second update delivery target (per performance goals)
- Server-side timestamp ordering for conflict resolution
- Reconnection uses existing 5-minute window pattern

**Note**: This feature directly supports constitutional requirement for real-time sync

### Principle V: AI Integration & Graceful Degradation ⚠️ MODIFIED SCOPE

**Status**: AI agent creation simplified (no LLM calls during add/remove)
- AI agents added to lobby don't require LLM initialization
- LLM integration deferred to game start (existing behavior)
- Room owner add/remove is instant (<3 seconds target)
- No new AI failure modes introduced by this feature

**Clarification**: This feature manages AI placeholders in lobby; LLM integration remains in game phase

### Performance & Reliability Standards ✅ COMPLIANT

**Targets**:
- ✅ Concurrent capacity: No change to 50 rooms limit
- ✅ State sync latency: 1 second for lobby updates (within constitutional requirement)
- ✅ Availability: No impact on 99% uptime target

### Quality Gates ✅ COMPLIANT

**Pre-Implementation**:
- ✅ Specification complete with acceptance scenarios
- ✅ This constitution check completed
- ⏳ Contracts to be defined in Phase 1

**Implementation**:
- ⏳ Test-first enforcement (Phase 2)
- ⏳ Coverage maintenance target: 53%+
- ⏳ Linting with Ruff (Python) and ESLint (JavaScript)

**Post-Implementation**:
- ⏳ Integration validation in staging
- ⏳ Load testing for concurrent joins
- ⏳ Contract documentation updated

**GATE STATUS**: ✅ **PASS** - All constitutional principles satisfied, no violations to justify

## Project Structure

### Documentation (this feature)

```text
specs/002-room-join-management/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── api-endpoints.yaml      # OpenAPI spec for new REST endpoints
│   └── websocket-events.yaml   # AsyncAPI spec for lobby events
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   ├── game_room.py             # MODIFY: Add owner_id, participant_count
│   │   └── game_room_participant.py # MODIFY: Add is_owner, join_timestamp
│   ├── services/
│   │   ├── game_room_service.py     # MODIFY: Add join_room, leave_room, manage_ai_agents
│   │   └── player_service.py        # EXTEND: Add ownership transfer logic
│   ├── api/
│   │   └── rooms.py                 # NEW: POST /{code}/join, DELETE /{code}/participants/{id}
│   ├── websocket/
│   │   ├── handlers.py              # MODIFY: Add lobby event handlers
│   │   └── events.py                # NEW: Define player_joined, player_left, ai_agent_added, etc.
│   └── utils/
│       └── room_validation.py       # NEW: Concurrent join validation, duplicate detection
├── tests/
│   ├── unit/
│   │   ├── test_game_room_models.py        # EXTEND: Ownership transfer, participant tracking
│   │   ├── test_game_room_service.py       # EXTEND: Join/leave/AI management logic
│   │   └── test_room_validation.py         # NEW: Concurrent join, duplicate detection
│   ├── integration/
│   │   ├── test_rooms_api.py               # EXTEND: New join/leave endpoints
│   │   └── test_lobby_websocket.py         # NEW: Real-time lobby update events
│   └── contract/
│       └── test_lobby_contracts.py         # NEW: Verify API/WebSocket contract compliance
└── alembic/
    └── versions/
        └── XXXX_add_lobby_management.py    # NEW: DB migration for owner_id, timestamps

frontend/
├── src/
│   ├── components/
│   │   ├── JoinRoomDialog.vue       # NEW: Room code input, join button
│   │   ├── LobbyParticipantList.vue # NEW: Display players + AI agents with indicators
│   │   ├── AIAgentControls.vue      # NEW: Add/remove AI buttons (owner only)
│   │   └── OwnerIndicator.vue       # NEW: Crown icon for room owner
│   ├── views/
│   │   └── GameRoomLobby.vue        # MODIFY: Integrate new components, WebSocket listeners
│   ├── services/
│   │   ├── roomApi.ts               # NEW: joinRoom(), leaveRoom() API calls
│   │   └── lobbySocket.ts           # NEW: Subscribe to lobby events, emit actions
│   ├── stores/
│   │   └── lobby.ts                 # NEW: Pinia store for lobby state management
│   └── types/
│       └── lobby.ts                 # NEW: TypeScript types for participants, events
└── tests/
    ├── unit/
    │   ├── JoinRoomDialog.spec.ts   # NEW: Join dialog component tests
    │   ├── AIAgentControls.spec.ts  # NEW: AI management component tests
    │   └── lobby.store.spec.ts      # NEW: Lobby state management tests
    └── e2e/
        └── lobby-management.spec.ts # NEW: End-to-end join/AI management flows
```

**Structure Decision**: Web application (existing backend + frontend). This feature extends existing GameRoom functionality without introducing new top-level services or modules. All changes integrate into established directory structure following constitutional component isolation principles.

## Complexity Tracking

**No violations to justify** - All constitutional principles satisfied without exceptions.

This feature extends existing infrastructure without introducing new architectural complexity:
- Reuses existing GameRoom and Player models (extends with new columns)
- Leverages established WebSocket infrastructure (python-socketio)
- Follows existing API patterns (FastAPI + Pydantic validation)
- Maintains test-first approach demonstrated in feature 001
- No new external services or dependencies required


| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
