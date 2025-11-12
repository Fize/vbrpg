# Implementation Tasks: Frontend Missing Features

**Feature**: Frontend Missing Features Implementation  
**Branch**: `003-frontend-missing-features`  
**Generated**: 2025-11-12  
**Total Tasks**: 87 tasks across 7 phases

## Task Overview

| Phase | User Story | Task Count | Estimated Time |
|-------|-----------|------------|----------------|
| Phase 1 | Setup | 8 | 0.5 days |
| Phase 2 | Foundational | 6 | 0.5 days |
| Phase 3 | US1: User Registration (P1) | 18 | 2-3 days |
| Phase 4 | US3: Game Actions (P1) | 16 | 2-3 days |
| Phase 5 | US6: Crime Scene Logic (P1) | 20 | 3-4 days |
| Phase 6 | US2: Room Filtering (P2) | 10 | 1-2 days |
| Phase 7 | US4: Turn Warnings (P2) | 9 | 1 day |
| **Total** | **6 user stories** | **87** | **10-14 days** |

**Note**: US5 (WebSocket Enhancement, P3) tasks are distributed across other stories as they are cross-cutting concerns.

---

## Phase 1: Setup

**Goal**: Initialize project structure and development environment

**Independent Test**: Development server starts, linting passes, basic test infrastructure works

### Tasks

- [ ] T001 Verify Node.js 18+ and pnpm 8+ installed per quickstart.md requirements
- [ ] T002 Install frontend dependencies via `pnpm install` in frontend/ directory
- [ ] T003 [P] Create JSDoc type definitions in frontend/src/types/player.js for RegisteredPlayer and PublicProfile entities
- [ ] T004 [P] Create JSDoc type definitions in frontend/src/types/room.js for RoomFilter entity
- [ ] T005 [P] Create JSDoc type definitions in frontend/src/types/game.js for GameAction, ClueItem, Suspect, Investigation, Accusation entities
- [ ] T006 [P] Create JSDoc type definitions in frontend/src/types/websocket.js for WebSocket event payloads
- [ ] T007 Configure ESLint to enforce JSDoc type checking in frontend/.eslintrc.cjs
- [ ] T008 Verify backend is running on http://localhost:8000 and WebSocket connection succeeds

**Completion Criteria**:
- ✅ `pnpm dev` starts frontend on http://localhost:5173
- ✅ `pnpm lint` passes with zero warnings
- ✅ All JSDoc type files created with exports
- ✅ WebSocket connection confirmed in browser console

---

## Phase 2: Foundational

**Goal**: Create shared infrastructure needed by all user stories

**Independent Test**: Stores initialize, composables load, error logging works

### Tasks

- [ ] T009 Create profile store in frontend/src/stores/profile.js with getProfile and cacheProfile actions
- [ ] T010 [P] Create useValidation composable in frontend/src/composables/useValidation.js with username, email, password validators
- [ ] T011 [P] Create useGameActions composable in frontend/src/composables/useGameActions.js with submitAction skeleton
- [ ] T012 [P] Create useTurnTimer composable in frontend/src/composables/useTurnTimer.js with countdown logic and warning thresholds
- [ ] T013 Enhance WebSocket service in frontend/src/services/websocket.js to map 15 events from AsyncAPI contract to store actions
- [ ] T014 Add error logging utility in frontend/src/utils/logger.js for API failures and WebSocket disconnects (FR-037)

**Completion Criteria**:
- ✅ All stores accessible via `import { useXxxStore } from '@/stores/xxx'`
- ✅ All composables return expected functions/refs
- ✅ WebSocket service has event handler registry
- ✅ Logger records errors to console

---

## Phase 3: User Story 1 - User Registration and Profile Management (P1)

**Goal**: Players can register accounts and view profiles (own and others)

**Priority**: P1 - Foundation for user identity system

**Independent Test**: 
1. Create guest account
2. Fill registration form (username, email, password)
3. Submit and verify success message
4. View own profile with email visible
5. Click another player's avatar and see public profile (no email)

**Functional Requirements**: FR-001 to FR-008

### Test Tasks

- [ ] T015 [P] [US1] Write unit test for useValidation composable in tests/unit/composables/useValidation.spec.js covering FR-002, FR-003, FR-004
- [ ] T016 [P] [US1] Write unit test for useRegistration composable in tests/unit/composables/useRegistration.spec.js covering registration flow
- [ ] T017 [P] [US1] Write component test for RegisterForm component in tests/component/components/profile/RegisterForm.spec.js covering FR-001, FR-005
- [ ] T018 [P] [US1] Write component test for ProfileCard component in tests/component/components/profile/ProfileCard.spec.js covering FR-006, FR-007
- [ ] T019 [US1] Write E2E test in tests/e2e/registration.spec.js covering all 6 acceptance scenarios from spec.md

### Implementation Tasks

- [ ] T020 [US1] Create useRegistration composable in frontend/src/composables/useRegistration.js with registerPlayer, validateUsername, validateEmail, validatePassword functions
- [ ] T021 [P] [US1] Implement POST /api/v1/players/register service method in frontend/src/services/api.js per REST API contract
- [ ] T022 [P] [US1] Implement GET /api/v1/players/{id} service method in frontend/src/services/api.js per REST API contract
- [ ] T023 [P] [US1] Implement GET /api/v1/players/me service method in frontend/src/services/api.js per REST API contract
- [ ] T024 [P] [US1] Create RegisterForm component in frontend/src/components/profile/RegisterForm.vue with Element Plus form, validation rules from useValidation (FR-001 to FR-005)
- [ ] T025 [P] [US1] Create ProfileCard component in frontend/src/components/profile/ProfileCard.vue displaying public profile fields (FR-006)
- [ ] T026 [P] [US1] Create ProfileView component in frontend/src/components/profile/ProfileView.vue showing full profile including email for current user (FR-007)
- [ ] T027 [US1] Create RegisterView page in frontend/src/views/RegisterView.vue integrating RegisterForm component
- [ ] T028 [US1] Add /register route to frontend/src/router/index.js pointing to RegisterView
- [ ] T029 [US1] Update auth store in frontend/src/stores/auth.js to auto-login after successful registration (FR-008)
- [ ] T030 [US1] Add "升级账号" button in existing UI that navigates to /register route
- [ ] T031 [US1] Add profile modal/page accessible from player avatars showing ProfileCard or ProfileView based on current user
- [ ] T032 [US1] Run all US1 tests and verify 100% pass rate

**Completion Criteria**:
- ✅ All 6 acceptance scenarios pass in E2E test
- ✅ Registration form validates per FR-002, FR-003, FR-004
- ✅ Error messages show for duplicate username/email (FR-005)
- ✅ Public profiles hide email (FR-007)
- ✅ Auto-login works post-registration (FR-008)
- ✅ Test coverage ≥ 80% for new code

---

## Phase 4: User Story 3 - Game Action Submission (P1)

**Goal**: Players can submit game actions (investigate, interrogate, accuse) during their turn

**Priority**: P1 - Core gameplay mechanic

**Independent Test**:
1. Start game and wait for player's turn
2. Click "调查" and select location
3. Verify action sent via WebSocket
4. Verify game state updates with discovered clue
5. Verify action UI disabled when not player's turn

**Functional Requirements**: FR-016 to FR-024

### Test Tasks

- [ ] T033 [P] [US3] Write unit test for useGameActions composable in tests/unit/composables/useGameActions.spec.js covering action validation (FR-021)
- [ ] T034 [P] [US3] Write unit test for useTurnTimer composable in tests/unit/composables/useTurnTimer.spec.js covering countdown and timeout (FR-023, FR-024)
- [ ] T035 [P] [US3] Write component test for ActionPanel component in tests/component/components/game/ActionPanel.spec.js covering FR-016, FR-017, FR-019
- [ ] T036 [US3] Write E2E test in tests/e2e/game-actions.spec.js covering all 6 acceptance scenarios from spec.md

### Implementation Tasks

- [ ] T037 [US3] Implement submitAction in frontend/src/composables/useGameActions.js to emit game_action WebSocket event per AsyncAPI contract (FR-018)
- [ ] T038 [US3] Add action validation logic to useGameActions to prevent invalid actions (e.g., re-investigating same location) (FR-021)
- [ ] T039 [P] [US3] Create ActionPanel component in frontend/src/components/game/ActionPanel.vue with buttons for investigate, interrogate, accuse, pass (FR-016)
- [ ] T040 [P] [US3] Create InvestigateAction component in frontend/src/components/game/InvestigateAction.vue for selecting locations
- [ ] T041 [P] [US3] Create InterrogateAction component in frontend/src/components/game/InterrogateAction.vue for selecting suspects and questions
- [ ] T042 [P] [US3] Create AccuseAction component in frontend/src/components/game/AccuseAction.vue for selecting suspects and evidence
- [ ] T043 [US3] Disable action UI when not current player's turn in ActionPanel using gameStore.currentTurn (FR-017)
- [ ] T044 [US3] Show loading spinner in ActionPanel during action processing (FR-019)
- [ ] T045 [US3] Update game store in frontend/src/stores/game.js to handle game_state_update event and apply state changes (FR-020)
- [ ] T046 [US3] Display error toast using ElMessage when action fails (FR-022)
- [ ] T047 [US3] Implement countdown timer in useTurnTimer with setInterval decrementing remaining_seconds (FR-023)
- [ ] T048 [US3] Auto-submit pass action when timer reaches 0 in useTurnTimer (FR-024, FR-032)
- [ ] T049 [US3] Run all US3 tests and verify 100% pass rate

**Completion Criteria**:
- ✅ All 6 acceptance scenarios pass in E2E test
- ✅ Actions submit via WebSocket with correct payload
- ✅ Game state updates after server response (FR-020)
- ✅ Invalid actions rejected with error message (FR-021, FR-022)
- ✅ Turn timer counts down and auto-skips on timeout (FR-023, FR-024)
- ✅ Action UI disabled for non-current players (FR-017)

---

## Phase 5: User Story 6 - Crime Scene Game Core Logic (P1)

**Goal**: Full crime scene game playable from case reveal to accusation

**Priority**: P1 - Core game content

**Independent Test**:
1. Start game and verify case background displays
2. See locations list with investigated status
3. See suspects list with info
4. Investigate location and find clue
5. Interrogate suspect and see answer
6. View reasoning panel with collected clues
7. Accuse suspect with evidence
8. See game result with case truth

**Functional Requirements**: FR-038 to FR-049

### Test Tasks

- [ ] T050 [P] [US6] Write unit test for game store in tests/unit/stores/game.spec.js covering state management for clues, suspects, investigations
- [ ] T051 [P] [US6] Write component test for CrimeSceneBoard component in tests/component/components/game/CrimeSceneBoard.spec.js covering FR-038, FR-039, FR-040
- [ ] T052 [P] [US6] Write component test for ClueList component in tests/component/components/game/ClueList.spec.js covering FR-041, FR-042
- [ ] T053 [P] [US6] Write component test for SuspectPanel component in tests/component/components/game/SuspectPanel.spec.js covering FR-043, FR-044
- [ ] T054 [US6] Write E2E test in tests/e2e/game-flow.spec.js covering all 7 acceptance scenarios from spec.md

### Implementation Tasks

- [ ] T055 [US6] Extend game store in frontend/src/stores/game.js to manage suspects, locations, clues, investigation history, accusations
- [ ] T056 [US6] Add game_started event handler in WebSocket service to initialize game state (FR-038)
- [ ] T057 [P] [US6] Create GameHeader component in frontend/src/components/game/GameHeader.vue displaying case background and info (FR-038)
- [ ] T058 [P] [US6] Create LocationGrid component in frontend/src/components/game/LocationGrid.vue listing all locations with investigated status (FR-039)
- [ ] T059 [P] [US6] Create LocationCard component in frontend/src/components/game/LocationCard.vue for individual location display
- [ ] T060 [P] [US6] Create SuspectPanel component in frontend/src/components/game/SuspectPanel.vue listing suspects with basic info (FR-040)
- [ ] T061 [P] [US6] Create SuspectCard component in frontend/src/components/game/SuspectCard.vue for individual suspect display
- [ ] T062 [P] [US6] Create ClueList component in frontend/src/components/game/ClueList.vue displaying discovered clues sorted by importance (FR-041, FR-042)
- [ ] T063 [P] [US6] Create ClueItem component in frontend/src/components/game/ClueItem.vue for individual clue with importance highlighting
- [ ] T064 [US6] Update InvestigateAction to display discovered clues after investigation (FR-041)
- [ ] T065 [US6] Update InterrogateAction to show dialog interface with suspect's answer (FR-043)
- [ ] T066 [US6] Store interrogation history in game store and make it accessible (FR-044)
- [ ] T067 [P] [US6] Create ReasoningPanel component in frontend/src/components/game/ReasoningPanel.vue showing clue relationships (FR-045)
- [ ] T068 [US6] Update AccuseAction component to allow selecting suspect and dragging evidence items (FR-046)
- [ ] T069 [US6] Add accusation validation in useGameActions to require minimum 2 evidence items (FR-046)
- [ ] T070 [US6] Handle accusation result from server and show success/failure feedback (FR-047)
- [ ] T071 [P] [US6] Create GameResultModal component in frontend/src/components/game/GameResultModal.vue displaying case truth, winner, player stats (FR-048)
- [ ] T072 [US6] Add game_ended event handler in WebSocket service to show GameResultModal (FR-035, FR-048)
- [ ] T073 [US6] Record action history in game store for each player (FR-049)
- [ ] T074 [US6] Assemble CrimeSceneBoard component in frontend/src/components/game/CrimeSceneBoard.vue integrating all child components
- [ ] T075 [US6] Create GameView page in frontend/src/views/GameView.vue with CrimeSceneBoard and ActionPanel
- [ ] T076 [US6] Add /game/:roomCode route to frontend/src/router/index.js pointing to GameView
- [ ] T077 [US6] Run all US6 tests and verify 100% pass rate

**Completion Criteria**:
- ✅ All 7 acceptance scenarios pass in E2E test
- ✅ Case background displays on game start (FR-038)
- ✅ Locations and suspects visible with correct status (FR-039, FR-040)
- ✅ Clues appear after investigation (FR-041)
- ✅ Interrogation shows answers and records history (FR-043, FR-044)
- ✅ Reasoning panel displays clue relationships (FR-045)
- ✅ Accusation validates evidence and shows result (FR-046, FR-047)
- ✅ Game end reveals truth (FR-048)
- ✅ Action history tracked (FR-049)

---

## Phase 6: User Story 2 - Room List Filtering (P2)

**Goal**: Players can filter room list by status and game type

**Priority**: P2 - UX enhancement for room discovery

**Independent Test**:
1. Create rooms with different statuses and game types
2. Apply status filter "Waiting"
3. Verify only waiting rooms shown
4. Apply game type filter "Crime Scene"
5. Verify only crime scene rooms shown
6. Combine filters and verify AND logic
7. Clear filters and verify all rooms shown
8. Apply filter with no matches and see empty state

**Functional Requirements**: FR-009 to FR-015

### Test Tasks

- [ ] T078 [P] [US2] Write unit test for room store in tests/unit/stores/room.spec.js covering filter state management
- [ ] T079 [P] [US2] Write component test for RoomFilter component in tests/component/components/room/RoomFilter.spec.js covering FR-009, FR-010, FR-011, FR-012
- [ ] T080 [US2] Write E2E test in tests/e2e/room-filtering.spec.js covering all 5 acceptance scenarios from spec.md

### Implementation Tasks

- [ ] T081 [US2] Update room store in frontend/src/stores/room.js to manage filters state (status, game_type, limit, offset)
- [ ] T082 [US2] Implement GET /api/v1/rooms with query params in frontend/src/services/api.js per REST API contract (FR-009, FR-010)
- [ ] T083 [P] [US2] Create RoomFilter component in frontend/src/components/room/RoomFilter.vue with dropdowns for status and game type (FR-009, FR-010)
- [ ] T084 [P] [US2] Create RoomList component in frontend/src/components/room/RoomList.vue displaying filtered rooms (FR-015)
- [ ] T085 [US2] Add "清除筛选" button in RoomFilter to reset filters (FR-012)
- [ ] T086 [US2] Show "未找到匹配的房间" empty state when no rooms match filters (FR-013)
- [ ] T087 [US2] Fix leave room API call to use DELETE method in frontend/src/services/api.js (FR-014)
- [ ] T088 [US2] Integrate RoomFilter and RoomList in frontend/src/views/RoomListView.vue
- [ ] T089 [US2] Run all US2 tests and verify 100% pass rate

**Completion Criteria**:
- ✅ All 5 acceptance scenarios pass in E2E test
- ✅ Status filter works (FR-009)
- ✅ Game type filter works (FR-010)
- ✅ Multiple filters combine with AND logic (FR-011)
- ✅ Clear filters button resets to show all (FR-012)
- ✅ Empty state displays for no matches (FR-013)
- ✅ Leave room uses DELETE method (FR-014)
- ✅ Room cards show all basic info (FR-015)

---

## Phase 7: User Story 4 - Turn Timeout Warning (P2)

**Goal**: Visual and audio warnings before turn timeout

**Priority**: P2 - UX improvement to prevent accidental timeouts

**Independent Test**:
1. Start game and wait for turn with short timeout (e.g., 45s)
2. Wait until 30s remaining
3. Verify yellow warning appears
4. Wait until 10s remaining
5. Verify red flashing warning and sound
6. Submit action before timeout
7. Verify warnings clear immediately
8. Let timeout occur and verify "超时" message

**Functional Requirements**: FR-025 to FR-029

### Test Tasks

- [ ] T090 [P] [US4] Write unit test for TurnTimer component in tests/component/components/common/TurnTimer.spec.js covering warning thresholds (FR-025, FR-026)
- [ ] T091 [US4] Write E2E test in tests/e2e/turn-warnings.spec.js covering all 4 acceptance scenarios from spec.md

### Implementation Tasks

- [ ] T092 [US4] Create TurnTimer component in frontend/src/components/common/TurnTimer.vue displaying countdown with color changes (FR-025, FR-026)
- [ ] T093 [US4] Add yellow styling to TurnTimer when remaining < 30s (FR-025)
- [ ] T094 [US4] Add red flashing animation to TurnTimer when remaining < 10s using CSS keyframes (FR-026)
- [ ] T095 [US4] Add audio alert in TurnTimer when remaining < 10s with mute option (FR-027)
- [ ] T096 [US4] Clear warnings in TurnTimer immediately when action submitted (FR-028)
- [ ] T097 [US4] Display "超时" toast message in useTurnTimer when countdown reaches 0 (FR-029)
- [ ] T098 [US4] Integrate TurnTimer component in GameHeader showing current player's remaining time
- [ ] T099 [US4] Connect TurnTimer to turn_changed WebSocket event for reset and player update (FR-032)
- [ ] T100 [US4] Run all US4 tests and verify 100% pass rate

**Completion Criteria**:
- ✅ All 4 acceptance scenarios pass in E2E test
- ✅ Yellow warning at 30s (FR-025)
- ✅ Red flashing + sound at 10s (FR-026, FR-027)
- ✅ Warnings clear on action submit (FR-028)
- ✅ Timeout message shown at 0s (FR-029)
- ✅ Timer syncs with turn_changed event (FR-032)

---

## Cross-Cutting: WebSocket Event Handling (P3)

**Note**: User Story 5 (WebSocket Enhancement) tasks are distributed across phases as they enable other features.

**Functional Requirements**: FR-030 to FR-037

### Event Handler Tasks (Already Integrated)

- **T013**: WebSocket event mapping registry (Phase 2)
- **T014**: Error logging for API/WebSocket failures (Phase 2, FR-037)
- **T045**: game_state_update handler (Phase 4, FR-031)
- **T048**: turn_changed handler for timeout (Phase 4, FR-032)
- **T056**: game_started handler (Phase 5)
- **T072**: game_ended handler (Phase 5, FR-035)
- **T099**: turn_changed handler for timer reset (Phase 7, FR-032)

### Additional WebSocket Tasks

- [ ] T101 [P] Add lobby_joined event handler in WebSocket service to confirm connection (FR-030)
- [ ] T102 [P] Add lobby_left event handler in WebSocket service to confirm disconnect (FR-030)
- [ ] T103 [P] Add player_joined event handler to update room participants
- [ ] T104 [P] Add player_left event handler to update room participants
- [ ] T105 [P] Add ai_thinking event handler to show AI loading state (FR-033)
- [ ] T106 [P] Add ai_action event handler to display AI action details (FR-034)
- [ ] T107 [P] Add ai_timeout event handler to show timeout notification
- [ ] T108 [P] Add reconnect event handler to request full state snapshot (FR-036)
- [ ] T109 Implement rejoin_room emit on reconnect to restore session
- [ ] T110 Test full state snapshot reconciliation after disconnect/reconnect (FR-036)

**Completion Criteria**:
- ✅ All 15 WebSocket events have handlers
- ✅ lobby_joined and lobby_left confirm connection status (FR-030)
- ✅ game_state_update applies full snapshot on reconnect (FR-031, FR-036)
- ✅ turn_changed highlights current player (FR-032)
- ✅ ai_thinking shows loading animation (FR-033)
- ✅ ai_action displays AI details (FR-034)
- ✅ game_ended shows results (FR-035)
- ✅ Error and warning logs captured (FR-037)
- ✅ All events tested in integration tests

---

## Implementation Strategy

### MVP Scope (User Story 1 Only)

For fastest time-to-value, implement **Phase 3 only**:
- User registration
- Profile viewing
- Basic authentication flow

**Deliverable**: Users can create accounts and view profiles (~2-3 days)

**Independent Value**: Establishes user identity system, prerequisite for all other features

### Incremental Delivery Sequence

1. **Sprint 1** (Days 1-3): Phase 1 + Phase 2 + Phase 3 (US1)
   - Deliverable: Working registration and profiles
   
2. **Sprint 2** (Days 4-7): Phase 4 + Phase 5 (US3 + US6)
   - Deliverable: Playable crime scene game
   
3. **Sprint 3** (Days 8-10): Phase 6 + Phase 7 (US2 + US4)
   - Deliverable: Enhanced UX with filtering and warnings
   
4. **Sprint 4** (Days 11-12): Cross-Cutting WebSocket tasks (US5)
   - Deliverable: Robust real-time synchronization

### Parallel Execution Opportunities

**Phase 1 (Setup)**: Tasks T003-T006 can run in parallel (4 type definition files)

**Phase 2 (Foundational)**: Tasks T010-T012 can run in parallel (3 composables)

**Phase 3 (US1)**:
- Tests: T015-T018 can run in parallel (4 test files)
- API methods: T021-T023 can run in parallel (3 endpoints)
- Components: T024-T026 can run in parallel (3 components)

**Phase 4 (US3)**:
- Tests: T033-T035 can run in parallel (3 test files)
- Sub-components: T040-T042 can run in parallel (3 action components)

**Phase 5 (US6)**:
- Tests: T050-T053 can run in parallel (4 test files)
- Sub-components: T057-T063 can run in parallel (7 components)

**Phase 6 (US2)**:
- Tests: T078-T079 can run in parallel (2 test files)
- Components: T083-T084 can run in parallel (2 components)

**Cross-Cutting WebSocket**: Tasks T101-T109 can run in parallel (9 event handlers)

**Total Parallelizable Tasks**: 42 out of 87 (48%)

---

## Dependencies

### User Story Dependencies

```
Phase 1 (Setup) 
    ↓
Phase 2 (Foundational)
    ↓
    ├─→ Phase 3 (US1) [Independent - can deploy alone]
    │
    ├─→ Phase 4 (US3) [Depends on: Phase 2, game store]
    │       ↓
    │   Phase 5 (US6) [Depends on: Phase 4, US3 complete]
    │
    ├─→ Phase 6 (US2) [Independent - can run parallel to US3/US6]
    │
    └─→ Phase 7 (US4) [Depends on: Phase 4, turn timer]
```

**Critical Path**: Phase 1 → Phase 2 → Phase 4 → Phase 5 (US6)

**Parallel Path**: Phase 6 (US2) can develop independently

### Task-Level Blocking Dependencies

- T032 blocks Phase 4 start (US1 must complete first for auth context)
- T049 blocks Phase 5 start (US3 action system needed for US6)
- T077 blocks final integration (US6 game logic needed for complete experience)
- T013 (WebSocket mapping) blocks T045, T056, T072 (event handlers)
- T020 (useRegistration) blocks T024 (RegisterForm component)
- T037 (submitAction) blocks T039-T042 (action components)

---

## Validation & Quality Gates

### Per-Phase Gates

Each phase must pass before proceeding:
1. ✅ All unit tests pass (Vitest)
2. ✅ All component tests pass (Vitest + @vue/test-utils)
3. ✅ All E2E tests pass (Playwright)
4. ✅ ESLint passes with zero warnings
5. ✅ Code coverage ≥ 80% for new code
6. ✅ Manual testing confirms acceptance scenarios
7. ✅ WebSocket events handled without errors
8. ✅ Performance: UI response <100ms, state sync <1s

### Final Integration Gate

Before marking feature complete:
- ✅ All 87 tasks checked off
- ✅ All 34 acceptance scenarios pass in E2E tests
- ✅ All 49 functional requirements validated
- ✅ All 11 success criteria measured and met:
  - SC-001: Registration completes in <2 minutes
  - SC-002: Room found in <3 clicks with filters
  - SC-003: Timeout warnings visible at 30s and 10s
  - SC-004: 90% actions respond in <3s
  - SC-005: Game rules understood in <5 minutes
  - SC-006: Full game completes in 30-60 minutes
  - SC-007: No UI jank >500ms
  - SC-008: Profile loads in <1s
  - SC-009: Filter results in <500ms
  - SC-010: 100 concurrent users supported
  - SC-011: 85% new users complete investigate + interrogate
- ✅ Constitution compliance confirmed:
  - Test-first: All code has tests written first
  - Component isolation: No direct backend access
  - API contracts: All calls match OpenAPI/AsyncAPI specs
  - Real-time sync: State updates within 1s
  - AI degradation: Timeouts handled gracefully
- ✅ Browser compatibility verified (Chrome 120+, Firefox 121+, Safari 17+)
- ✅ Accessibility audit passes (WCAG 2.1 Level A)

---

## Task Format Reference

### Checklist Components

- `[ ]` - Checkbox (mandatory)
- `T###` - Sequential task ID
- `[P]` - Parallel flag (can run simultaneously with other [P] tasks)
- `[USX]` - User story label (only for story-specific tasks)
- Description with file path

### Examples

✅ **Correct**:
```
- [ ] T001 Verify Node.js 18+ installed
- [ ] T003 [P] Create type definitions in frontend/src/types/player.js
- [ ] T015 [P] [US1] Write unit test in tests/unit/composables/useValidation.spec.js
```

❌ **Incorrect**:
```
- [ ] Create type definitions (missing task ID)
- T001 Install Node.js (missing checkbox)
- [ ] [US1] Write test (missing task ID)
```

---

## Summary

**Total Implementation**: 87 tasks across 7 phases  
**Estimated Duration**: 10-14 days (experienced Vue 3 developer)  
**Parallel Opportunities**: 42 tasks (48%) can run in parallel  
**Critical Path**: Setup → Foundational → US3 → US6 (8-10 days)  
**MVP Scope**: Phase 3 only (US1 Registration, 2-3 days)  
**Test Coverage Target**: ≥80% for all new code  
**Performance Targets**: <100ms UI, <1s WebSocket sync, 60fps animations

**Next Steps**:
1. Review all tasks and confirm understanding
2. Set up task tracking (GitHub Issues, Jira, etc.)
3. Begin Phase 1 (Setup) following test-first approach
4. Execute phases sequentially with parallel task optimization
5. Validate quality gates after each phase
6. Deliver incrementally per sprint schedule

**Documentation References**:
- Feature Spec: `specs/003-frontend-missing-features/spec.md`
- Implementation Plan: `specs/003-frontend-missing-features/plan.md`
- Research Decisions: `specs/003-frontend-missing-features/research.md`
- Data Models: `specs/003-frontend-missing-features/data-model.md`
- REST API Contract: `specs/003-frontend-missing-features/contracts/api-rest.yaml`
- WebSocket Contract: `specs/003-frontend-missing-features/contracts/api-websocket.yaml`
- Quickstart Guide: `specs/003-frontend-missing-features/quickstart.md`

---

**Tasks File Status**: ✅ COMPLETE - Ready for implementation  
**Last Updated**: 2025-11-12  
**Branch**: `003-frontend-missing-features`
