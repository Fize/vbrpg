# Implementation Plan: Frontend Missing Features Implementation

**Branch**: `003-frontend-missing-features` | **Date**: 2025-11-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-frontend-missing-features/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement 6 missing frontend features to achieve parity with backend APIs: user registration and profile management, room list filtering, game action submission, turn timeout warnings, enhanced WebSocket event handling, and complete crime scene game logic. The implementation follows test-first development principles with Vue 3 composition API, Element Plus UI components, and real-time state synchronization via Socket.IO.

## Technical Context

**Language/Version**: JavaScript ES2022+, Vue 3.4+  
**Primary Dependencies**: Vue 3, Vite 5, Element Plus 2.5, Socket.IO Client 4.6, Axios 1.6  
**Storage**: LocalStorage for authentication state, Pinia for application state  
**Testing**: Vitest 1.1 (unit tests), Playwright 1.40 (E2E tests)  
**Target Platform**: Modern browsers (Chrome 120+, Firefox 121+, Safari 17+)  
**Project Type**: Web application (frontend only, backend APIs already implemented)  
**Performance Goals**: <100ms UI response time, <1s WebSocket state sync (p95), 60fps animations  
**Constraints**: Real-time synchronization required, AI actions within 10s, reconnection within 5min  
**Scale/Scope**: 6 user stories, 49 functional requirements, 11 UI components to create/modify

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Test-First Development (NON-NEGOTIABLE)

✅ **PASS** - Feature spec includes 6 user stories with 34 acceptance scenarios providing testable requirements. Plan will generate unit tests (Vitest) before component implementation and E2E tests (Playwright) before user flows. All frontend changes will follow Red-Green-Refactor cycle.

### II. Component Isolation & Service Boundaries

✅ **PASS** - Frontend communicates exclusively through documented backend APIs (REST: `/api/v1/*`, WebSocket: Socket.IO events). No direct database access. Backend service boundaries already established. Frontend components will be modular Vue 3 components with clear single responsibilities.

### III. API Contracts & Type Safety

✅ **PASS** - Backend APIs already documented with OpenAPI specifications. WebSocket events documented in backend code. Frontend will use TypeScript interfaces matching backend contracts. Contract tests (MSW for REST mocking, Socket.IO mock server for WebSocket) will validate compliance.

### IV. Real-Time State Synchronization

✅ **PASS** - Backend maintains authoritative game state. Frontend implements optimistic UI updates with server reconciliation. Reconnection recovery handled by full state snapshot on `reconnect` event. WebSocket event handlers ensure 1s update delivery (p95). Pinia stores manage client-side state with WebSocket sync.

### V. AI Integration & Graceful Degradation

✅ **PASS** - Frontend handles AI timeout scenarios via `ai_timeout` WebSocket event. UI displays loading states during AI thinking. LLM failures communicated to users via error messages. AI actions treated identically to human actions in UI. No blocking dependencies on AI service availability.

### Performance & Reliability Standards

✅ **PASS** - Performance goals aligned with constitution:
- UI response time <100ms (UI target) vs <1s state sync (constitution)
- WebSocket sync <1s p95 (matches constitution)
- AI response handled within 10s timeout (matches constitution)
- Reconnection grace period: frontend implements 5min window (matches constitution)

### Development Workflow & Quality Gates

✅ **PASS** - Vitest + Playwright testing stack ensures:
- Unit tests for services, stores, composables before implementation
- Component tests before Vue component creation
- E2E tests for acceptance scenarios before integration
- ESLint for code quality enforcement

**Result**: ✅ All constitutional gates passed. Proceeding to Phase 0 research.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Documentation (this feature)

```text
specs/003-frontend-missing-features/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── api-rest.yaml    # OpenAPI for REST endpoints
│   └── api-websocket.yaml # AsyncAPI for Socket.IO events
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── components/      # Vue components
│   │   ├── game/        # Game-specific components (CrimeSceneBoard, ActionPanel, ClueList)
│   │   ├── profile/     # User profile components (ProfileCard, ProfileEditor)
│   │   ├── room/        # Room components (RoomList, RoomFilter, RoomCard)
│   │   └── common/      # Shared components (TurnTimer, LoadingState, ErrorMessage)
│   ├── composables/     # Vue composition functions
│   │   ├── useAuth.js
│   │   ├── useWebSocket.js
│   │   ├── useGameState.js
│   │   └── useTurnTimer.js
│   ├── services/        # API clients
│   │   ├── api.js       # Axios REST client
│   │   └── websocket.js # Socket.IO client
│   ├── stores/          # Pinia state management
│   │   ├── auth.js
│   │   ├── game.js
│   │   ├── room.js
│   │   └── profile.js
│   ├── views/           # Page components
│   │   ├── RegisterView.vue
│   │   ├── ProfileView.vue
│   │   ├── RoomListView.vue
│   │   └── GameView.vue
│   └── types/           # TypeScript interfaces
│       ├── player.ts
│       ├── room.ts
│       ├── game.ts
│       └── websocket.ts
└── tests/
    ├── unit/            # Vitest unit tests
    │   ├── composables/
    │   ├── services/
    │   └── stores/
    ├── component/       # Vitest component tests
    │   └── components/
    └── e2e/             # Playwright E2E tests
        ├── registration.spec.js
        ├── profile.spec.js
        ├── room-filtering.spec.js
        ├── game-actions.spec.js
        └── game-flow.spec.js
```

**Structure Decision**: Web application structure with frontend-only implementation. Backend APIs (`backend/src/api/`) already exist and are stable. Frontend follows Vue 3 composition API with feature-based organization (game/, profile/, room/). Pinia stores centralize state management. Tests organized by testing level (unit/component/e2e) following constitution's test-first principle.

## Complexity Tracking

**No constitutional violations** - All complexity justified within existing architecture:
- Frontend-backend separation already established (2-project architecture)
- Pinia state management standard for Vue 3 applications
- WebSocket for real-time features (required by constitution §IV)
- Test-first workflow enforced at all levels

No additional complexity layers introduced.

---

## Planning Summary

### Phase 0: Research ✅ COMPLETE

**Output**: `research.md` (6 technical decisions documented)

**Key Decisions**:
1. **State Management**: Composable-First Architecture (Pinia stores + composables + components)
2. **WebSocket Handling**: Event-Action Mapping Pattern with full state snapshot on reconnect
3. **Form Validation**: Element Plus declarative validation with composable utilities
4. **Game UI Architecture**: Feature-based component tree (5-7 components, 60fps optimizations)
5. **Testing Strategy**: Three-layer pyramid (Unit: Vitest, Integration: Mock WebSocket, E2E: Playwright)
6. **Type Safety**: JSDoc annotations (no TypeScript migration, zero cost)

**Rationale**: All decisions align with existing codebase patterns (auth store, lobby store, WebSocket service) and constitutional principles (test-first, component isolation, real-time sync).

---

### Phase 1: Design Artifacts ✅ COMPLETE

**Outputs**:
- `data-model.md` - 9 entities with fields, relationships, validation rules, data flows
- `contracts/api-rest.yaml` - OpenAPI 3.1.0 for 5 REST endpoints
- `contracts/api-websocket.yaml` - AsyncAPI 3.0.0 for 15 WebSocket events
- `quickstart.md` - 15-minute developer onboarding guide with test-first workflow

**Data Models Defined**:
| Entity | Purpose | Frontend Store |
|--------|---------|---------------|
| RegisteredPlayer | Full account with stats | authStore.currentPlayer |
| PublicProfile | Sanitized profile view | profileStore |
| RoomFilter | Room list query params | roomStore.filters |
| GameAction | Player action submission | gameStore.pendingAction |
| TurnTimer | Countdown with warnings | gameStore.turnTimer |
| ClueItem | Evidence in game | gameStore.clues |
| Suspect | NPC characters | gameStore.suspects |
| Investigation | Player progress | gameStore.myInvestigation |
| Accusation | Crime solution attempt | gameStore.accusations |

**API Contracts**:
- REST: 5 endpoints (register, profile, rooms list, rooms leave, current player)
- WebSocket: 15 events (lobby, game state, turn, actions, AI, reconnection)

---

### Phase 2: Implementation Tasks

**Note**: Task breakdown (`tasks.md`) will be generated by `/speckit.tasks` command per workflow specification.

**Recommended Task Sequencing** (based on priority):

#### Sprint 1: Foundation (P1 - User Registration)
- Tasks for FR-001 to FR-008 (user account management)
- Deliverable: Users can register and view profiles
- Estimated: 2-3 days

#### Sprint 2: Core Gameplay (P1 - Game Actions + Crime Scene Logic)
- Tasks for FR-016 to FR-024 (game action submission)
- Tasks for FR-038 to FR-049 (crime scene game logic)
- Deliverable: Playable crime scene game end-to-end
- Estimated: 5-7 days

#### Sprint 3: Enhancements (P2 - Room Filtering + Turn Warnings)
- Tasks for FR-009 to FR-015 (room list filtering)
- Tasks for FR-025 to FR-029 (turn timeout warnings)
- Deliverable: Improved UX for room discovery and turn management
- Estimated: 2-3 days

#### Sprint 4: Robustness (P3 - WebSocket Enhancement)
- Tasks for FR-030 to FR-037 (WebSocket event handling)
- Deliverable: Rock-solid real-time synchronization
- Estimated: 2-3 days

**Total Estimated Duration**: 11-16 days (2-3 weeks for experienced Vue developer)

---

## Implementation Readiness Checklist

### ✅ Planning Phase Complete
- [x] Technical context defined (languages, dependencies, platform)
- [x] Constitution check passed (all 5 principles validated)
- [x] Research completed (6 technical unknowns resolved)
- [x] Data models documented (9 entities with validation rules)
- [x] API contracts generated (OpenAPI + AsyncAPI specifications)
- [x] Quickstart guide created (15-minute developer onboarding)

### ✅ Pre-Implementation Preparation
- [x] Backend APIs verified (all 5 REST endpoints exist)
- [x] WebSocket events confirmed (15 events documented in backend)
- [x] Test infrastructure ready (Vitest + Playwright configured)
- [x] Development environment validated (Node 18+, pnpm 8+)

### 🔲 Pending: Task Breakdown
- [ ] Generate `tasks.md` with concrete implementation tasks (via `/speckit.tasks`)
- [ ] Assign estimates (T-shirt sizing or hours per task)
- [ ] Identify task dependencies and critical path
- [ ] Define acceptance criteria per task

### 🔲 Pending: Implementation Start
- [ ] Create feature branch (if not already on `003-frontend-missing-features`)
- [ ] Set up task tracking (GitHub Issues, Jira, or similar)
- [ ] Begin Sprint 1 (User Registration) with test-first approach

---

## Next Steps

**For AI Agent / Developer**:
1. Run `/speckit.tasks` command to generate `tasks.md` with implementation breakdown
2. Review all Phase 0-1 artifacts (research.md, data-model.md, contracts/)
3. Study quickstart.md for development workflow and test-first examples
4. Begin implementation starting with highest priority tasks (P1)

**Workflow Reminder**:
```bash
# For each task:
1. Write failing test (RED)
2. Implement minimum code to pass (GREEN)
3. Refactor while maintaining tests (REFACTOR)
4. Commit with descriptive message
5. Move to next task
```

**Documentation References**:
- Feature Spec: `specs/003-frontend-missing-features/spec.md` (49 functional requirements)
- Implementation Plan: This file (technical strategy and design artifacts)
- Research Decisions: `research.md` (technical Q&A with rationale)
- Data Models: `data-model.md` (entity definitions and data flows)
- REST API: `contracts/api-rest.yaml` (OpenAPI 3.1.0)
- WebSocket API: `contracts/api-websocket.yaml` (AsyncAPI 3.0.0)
- Quickstart: `quickstart.md` (developer onboarding guide)

---

**Plan Status**: ✅ COMPLETE - Ready for task generation (`/speckit.tasks`)  
**Last Updated**: 2025-11-12  
**Next Command**: `/speckit.tasks` to create implementation task breakdown
