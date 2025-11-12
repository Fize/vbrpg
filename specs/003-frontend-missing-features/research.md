# Phase 0 Research: Frontend Missing Features Implementation

**Generated**: 2025-11-12  
**Branch**: `003-frontend-missing-features`  
**Context**: Research technical decisions for implementing 49 functional requirements across 6 user stories

## Research Questions

### RQ-001: Vue 3 Composition API State Management Patterns

**Question**: What are the best practices for managing complex game state with Vue 3 Composition API and Pinia, especially for real-time updates from WebSocket events?

**Investigation**:

Existing codebase analysis reveals:
- Pinia stores using Composition API style with `ref()` and `computed()` (see `frontend/src/stores/auth.js`)
- WebSocket service maintains connection state and event handlers (see `frontend/src/services/websocket.js`)
- Current pattern: stores listen to WebSocket events and update state

Researched patterns from Vue 3 + Pinia best practices:
1. **Single Source of Truth**: Backend maintains authoritative state (already implemented)
2. **Reactive State Updates**: Use `ref()` for primitive state, `reactive()` for complex objects
3. **Computed Properties**: Derive UI state from store state (e.g., `isGuest` computed from `currentPlayer`)
4. **Action-Based Mutations**: All state changes through store actions (follows Flux pattern)
5. **WebSocket Integration**: Dedicated composable (`useWebSocket`) bridges socket events to store actions

**Decision**: 
Adopt **Composable-First Architecture** with these layers:
- **Stores (Pinia)**: Domain state (auth, game, room, profile)
- **Composables**: Feature logic (useGameActions, useTurnTimer, useReconnection)
- **Components**: UI presentation only, minimal logic

**Rationale**:
- Aligns with existing codebase patterns (auth store, lobby store, game store)
- Composables provide reusable logic across components
- Clear separation of concerns: stores = state, composables = behavior, components = UI
- Testability: composables can be unit tested independently

**Alternatives Rejected**:
- **Option**: Use provide/inject for state sharing
- **Rejected Because**: Pinia already integrated, provide/inject adds complexity without value
- **Option**: Component-local state with props drilling
- **Rejected Because**: Real-time updates require centralized state for efficiency

**References**:
- Vue 3 Composition API RFC: https://github.com/vuejs/rfcs/blob/master/active-rfcs/0013-composition-api.md
- Pinia documentation: https://pinia.vuejs.org/core-concepts/
- Existing implementation: `frontend/src/stores/auth.js`, `frontend/src/stores/game.js`

---

### RQ-002: WebSocket Event Handling and Reconnection Strategy

**Question**: How to implement robust WebSocket reconnection with state synchronization within 5-minute grace period, handling all 15+ event types from specification?

**Investigation**:

Existing implementation (`frontend/src/services/websocket.js`):
- Socket.IO client with auto-reconnection (up to 60 attempts @ 5s intervals = 5 minutes)
- Session storage tracks last room code and disconnect timestamp
- Grace period validation: checks if `Date.now() - disconnectTimestamp < 5min`
- Event handler registry: `Map<eventName, callback[]>`

Current gaps:
- No full state snapshot request on reconnection
- Limited event handlers (only lobby events implemented)
- No optimistic UI update rollback on error

Researched patterns:
1. **Event-Driven Architecture**: Each WebSocket event maps to store action
2. **Optimistic Updates**: Client updates immediately, rolls back on server rejection
3. **State Reconciliation**: On reconnect, request full state snapshot, merge with local state
4. **Event Ordering**: Socket.IO guarantees order per connection, no additional handling needed

**Decision**:
Implement **Event-Action Mapping Pattern** with these mechanics:
```javascript
// WebSocket event → Store action mapping
const EVENT_HANDLERS = {
  'game_state_update': (data) => gameStore.updateState(data),
  'turn_changed': (data) => gameStore.setCurrentTurn(data),
  'ai_thinking': (data) => gameStore.setAIThinking(data.player_id, true),
  'ai_action': (data) => gameStore.applyAIAction(data),
  'player_joined': (data) => roomStore.addParticipant(data),
  'player_left': (data) => roomStore.removeParticipant(data),
  'game_started': (data) => gameStore.startGame(data),
  'game_ended': (data) => gameStore.endGame(data),
  'reconnect': () => requestFullStateSnapshot(),
  // ... 7 more events
}
```

Reconnection flow:
1. Socket.IO auto-reconnects (existing)
2. On `reconnect` event, check grace period validity
3. If valid: emit `rejoin_room` with room code, player ID
4. Backend responds with `game_state_update` containing full snapshot
5. Store replaces local state with server state
6. UI automatically updates via reactive bindings

**Rationale**:
- Builds on existing reconnection infrastructure (grace period tracking)
- Centralized event handling simplifies debugging (all events in one map)
- Full state snapshot avoids complex delta merge logic
- Socket.IO's built-in ordering prevents race conditions

**Alternatives Rejected**:
- **Option**: Incremental state sync with event replay
- **Rejected Because**: Complex to implement, prone to bugs, full snapshot simpler for <50 players
- **Option**: Persistent WebSocket connection (no reconnection)
- **Rejected Because**: Mobile networks unreliable, reconnection mandatory for UX

**References**:
- Socket.IO reconnection docs: https://socket.io/docs/v4/client-socket-instance/#reconnection
- Existing implementation: `frontend/src/services/websocket.js` lines 70-95
- Constitution requirement: 5-minute grace period (§IV Real-Time State Synchronization)

---

### RQ-003: Form Validation and Error Handling Strategy

**Question**: How to implement client-side validation for registration, game actions, and room filters, with consistent error messaging and accessibility support?

**Investigation**:

Element Plus form validation:
- Built-in `<el-form>` with rules-based validation
- Async validators for server-side checks (e.g., username uniqueness)
- Localization support via `element-plus/locale`
- Accessibility: ARIA attributes, keyboard navigation

Current codebase:
- Room code validation in `JoinRoomForm.spec.js`: 6-character alphanumeric
- No centralized validation utilities
- API errors handled per-component (no global error handler)

Researched patterns:
1. **Rules-Based Validation**: Define validation rules declaratively
2. **Async Validators**: Check server constraints before submit
3. **Error Boundary**: Catch unexpected errors, prevent white screen
4. **Toast Notifications**: Non-blocking error messages (Element Plus `ElMessage`)

**Decision**:
Implement **Declarative Validation with Composable Utilities**:

```javascript
// src/composables/useValidation.js
export function useRegistrationValidation() {
  const rules = {
    username: [
      { required: true, message: '请输入用户名', trigger: 'blur' },
      { min: 3, max: 20, message: '用户名长度3-20字符', trigger: 'blur' },
      { 
        asyncValidator: checkUsernameAvailable, 
        message: '用户名已被使用', 
        trigger: 'blur' 
      }
    ],
    email: [
      { required: true, message: '请输入邮箱', trigger: 'blur' },
      { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
    ],
    password: [
      { required: true, message: '请输入密码', trigger: 'blur' },
      { min: 8, message: '密码至少需要8个字符', trigger: 'blur' }
    ]
  }
  
  return { rules }
}
```

Error handling layers:
1. **Form validation**: Prevent invalid submissions (Element Plus rules)
2. **API interceptors**: Global Axios error handling for 4xx/5xx
3. **Store actions**: Catch-try blocks return `{ success, error }` objects
4. **Components**: Display errors via `ElMessage.error()` toast

**Rationale**:
- Element Plus forms already integrated (existing codebase uses `el-button`, `el-card`)
- Composables make validation logic reusable (registration, profile edit)
- Consistent error messages improve UX (all validation in one place)
- Accessibility built-in (Element Plus WCAG 2.1 compliant)

**Alternatives Rejected**:
- **Option**: Vuelidate library for validation
- **Rejected Because**: Element Plus forms sufficient, avoid extra dependency
- **Option**: Global error modal (blocking)
- **Rejected Because**: Toast notifications non-blocking, better UX for non-critical errors

**References**:
- Element Plus form docs: https://element-plus.org/en-US/component/form.html
- Existing test: `frontend/tests/unit/components/JoinRoomForm.spec.js` lines 30-47
- WCAG 2.1 guidelines: https://www.w3.org/WAI/WCAG21/quickref/

---

### RQ-004: Game State Rendering and Component Architecture

**Question**: How to structure the Crime Scene game UI with multiple interactive elements (clue board, suspect list, action panel, turn timer) while maintaining 60fps performance?

**Investigation**:

Game requirements from spec:
- Display case background, locations (3-5), suspects (3-5), clues (10-20)
- Real-time updates on other players' actions
- Animated transitions (clue reveals, turn changes)
- Interactive elements: click locations, interrogate suspects, submit accusations

Performance concerns:
- Large DOM trees (50+ elements) can cause jank
- Frequent state updates from WebSocket (1s interval)
- CSS animations should use GPU acceleration (transform, opacity)

Researched patterns:
1. **Component Decomposition**: Split into 5-7 small components
2. **Virtual Scrolling**: Not needed (<100 total elements)
3. **Memoization**: `computed()` prevents unnecessary re-renders
4. **CSS Containment**: Isolate layout recalculations
5. **Lazy Loading**: Defer non-critical components

**Decision**:
Adopt **Feature-Based Component Tree** with performance optimizations:

```
GameView.vue (page)
├── GameHeader.vue (case info, timer)
│   └── TurnTimer.vue (animated countdown)
├── CrimeSceneBoard.vue (main gameplay area)
│   ├── LocationGrid.vue (clickable locations)
│   │   └── LocationCard.vue × N (individual locations)
│   └── ClueList.vue (discovered clues)
│       └── ClueItem.vue × N (draggable clues)
├── SuspectPanel.vue (sidebar)
│   └── SuspectCard.vue × N (interrogation UI)
└── ActionPanel.vue (player controls)
    ├── InvestigateAction.vue
    ├── InterrogateAction.vue
    └── AccuseAction.vue
```

Performance techniques:
- **v-once**: Static content (case background, suspect names)
- **v-memo**: Clue items (only re-render on clue change)
- **CSS containment**: `contain: layout style paint` on cards
- **Transform animations**: GPU-accelerated (no layout thrashing)
- **Debounced updates**: Batch state updates if events <50ms apart

**Rationale**:
- 5-7 components manageable (not over-engineered)
- Each component <150 LOC (testable, maintainable)
- Performance techniques proven for 60fps (CSS containment, v-memo)
- Existing codebase has similar structure (lobby has `RoomCard.vue`, `JoinRoomForm.vue`)

**Alternatives Rejected**:
- **Option**: Single monolithic `GameView.vue` component
- **Rejected Because**: Untestable (300+ LOC), violates Single Responsibility Principle
- **Option**: Canvas-based rendering
- **Rejected Because**: Overkill for <100 elements, accessibility nightmare

**References**:
- Vue 3 performance guide: https://vuejs.org/guide/best-practices/performance.html
- CSS containment: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Containment
- Existing structure: `frontend/src/components/lobby/`

---

### RQ-005: Testing Strategy for Real-Time Features

**Question**: How to test WebSocket event handling, reconnection logic, and game state synchronization in unit, integration, and E2E tests?

**Investigation**:

Existing test infrastructure:
- **Unit tests**: Vitest with jsdom, `@vue/test-utils` for component mounting
- **Integration tests**: Vitest with mocked WebSocket server
- **E2E tests**: Playwright with real backend (Docker Compose)
- Coverage: v8 provider, HTML reports

Current test patterns:
- Mock API with `vi.mock('@/services/api')` (see `JoinRoomForm.spec.js`)
- Mock router with `useRouter` mock
- Mock WebSocket: no pattern yet (needs implementation)

Researched approaches:
1. **Unit Tests**: Mock WebSocket service entirely, test store reactions
2. **Integration Tests**: Use `socket.io-mock` library for fake server
3. **E2E Tests**: Real WebSocket server (backend running), verify UI updates
4. **Contract Tests**: Validate event payloads match backend API

**Decision**:
Implement **Three-Layer Testing Pyramid**:

**Layer 1 - Unit Tests (Vitest):**
```javascript
// tests/unit/composables/useGameActions.spec.js
vi.mock('@/services/websocket', () => ({
  emit: vi.fn(),
  on: vi.fn(),
}))

it('submits investigate action via WebSocket', () => {
  const { investigateLocation } = useGameActions()
  investigateLocation('library')
  expect(websocket.emit).toHaveBeenCalledWith('game_action', {
    type: 'investigate',
    location: 'library'
  })
})
```

**Layer 2 - Integration Tests (Vitest + Mock Server):**
```javascript
// tests/integration/websocket/game-events.spec.js
import { Server } from 'socket.io'
import { io as ioc } from 'socket.io-client'

let mockServer, clientSocket

beforeAll(() => {
  mockServer = new Server(3001)
  clientSocket = ioc('http://localhost:3001')
})

it('updates game state on server event', (done) => {
  mockServer.emit('game_state_update', { turn: 2 })
  setTimeout(() => {
    expect(gameStore.currentTurn).toBe(2)
    done()
  }, 100)
})
```

**Layer 3 - E2E Tests (Playwright):**
```javascript
// tests/e2e/game-flow.spec.js
test('player completes full game flow', async ({ page }) => {
  await page.goto('http://localhost:5173/game/ABC123')
  await page.click('button:has-text("调查")')
  await page.click('text=图书馆')
  await expect(page.locator('.clue-item')).toContainText('血迹')
  await page.click('button:has-text("指控")')
  await expect(page.locator('.game-result')).toBeVisible()
})
```

Test coverage targets:
- Unit tests: 80%+ (composables, stores, utils)
- Integration tests: Key flows (reconnection, state sync, AI actions)
- E2E tests: 6 user stories × 1-2 happy path scenarios = 8-12 tests

**Rationale**:
- Three layers balance speed vs confidence (unit: fast, E2E: thorough)
- Mock server enables integration testing without backend (CI-friendly)
- Playwright E2E tests verify real user experience (acceptance criteria)
- Existing codebase has Vitest + Playwright setup (minimal new tooling)

**Alternatives Rejected**:
- **Option**: Only E2E tests (no unit/integration)
- **Rejected Because**: Slow CI (5min+ for full suite), hard to debug failures
- **Option**: Cypress for E2E
- **Rejected Because**: Playwright already integrated, avoid migration cost

**References**:
- Vitest mocking docs: https://vitest.dev/guide/mocking.html
- socket.io-mock: https://github.com/nullivex/mock-socket
- Existing tests: `frontend/tests/unit/components/JoinRoomForm.spec.js`, `frontend/tests/e2e/join-room.spec.js`

---

### RQ-006: Type Safety for API Contracts

**Question**: Should we use TypeScript for type safety, or can JSDoc comments provide sufficient type checking without migration overhead?

**Investigation**:

Current codebase:
- Pure JavaScript (no `.ts` files)
- No type annotations (JSDoc or TypeScript)
- IDE support: VSCode with Vetur/Volar (infers some types)

TypeScript benefits:
- Compile-time type checking (catch errors before runtime)
- Better IDE autocomplete (API payloads, event data)
- Refactoring safety (rename symbols, find usages)

TypeScript costs:
- Migration overhead (rename files, add types, fix errors)
- Build complexity (tsconfig, type declarations)
- Learning curve for team (if unfamiliar)

JSDoc alternative:
- Type annotations in comments: `/** @type {Player} */`
- VSCode understands JSDoc (hover, autocomplete)
- No build step changes (still JavaScript)

**Decision**:
Use **JSDoc Type Annotations** with shared type definitions:

```javascript
// src/types/player.js
/**
 * @typedef {Object} Player
 * @property {number} id - Player unique ID
 * @property {string} username - Display name
 * @property {boolean} is_guest - Guest account flag
 * @property {number} total_games - Total games played
 * @property {number} total_wins - Total games won
 */

// src/services/api.js
/**
 * Fetch player profile
 * @param {number} playerId - Player ID
 * @returns {Promise<Player>}
 */
export async function getPlayerProfile(playerId) {
  const response = await axios.get(`/api/v1/players/${playerId}`)
  return response.data
}
```

Type checking enforcement:
- ESLint with `@typescript-eslint/parser` in JSDoc mode
- VSCode `"checkJs": true` in jsconfig.json
- CI linting step catches type errors

**Rationale**:
- Zero migration cost (no file renames, no build changes)
- Incremental adoption (add types as we write new code)
- Sufficient for medium-sized project (<20k LOC)
- Existing codebase is JavaScript (consistency over perfection)

**Alternatives Rejected**:
- **Option**: Full TypeScript migration
- **Rejected Because**: High upfront cost (estimate 40+ hours), feature delivery delay
- **Option**: No types at all
- **Rejected Because**: Backend contracts complex (15+ event types), easy to misuse APIs

**References**:
- JSDoc documentation: https://jsdoc.app/
- VSCode JSDoc support: https://code.visualstudio.com/docs/languages/javascript#_jsdoc-support
- ESLint JSDoc plugin: https://github.com/gajus/eslint-plugin-jsdoc

---

## Summary of Decisions

| Research Question | Decision | Key Justification |
|-------------------|----------|-------------------|
| RQ-001: State Management | Composable-First Architecture (Pinia stores + composables) | Aligns with existing patterns, clear separation of concerns |
| RQ-002: WebSocket Handling | Event-Action Mapping + Full State Snapshot on Reconnect | Builds on existing reconnection, centralized event handling |
| RQ-003: Form Validation | Element Plus Declarative Validation + Composable Utilities | Already integrated, reusable, accessible |
| RQ-004: Game UI Architecture | Feature-Based Component Tree (5-7 components) | Testable, maintainable, proven 60fps techniques |
| RQ-005: Testing Strategy | Three-Layer Pyramid (Unit/Integration/E2E) | Balanced speed vs confidence, existing tooling |
| RQ-006: Type Safety | JSDoc Type Annotations | Zero migration cost, incremental adoption, sufficient |

All decisions comply with constitution principles:
- ✅ Test-First Development: Three-layer testing strategy ensures tests precede implementation
- ✅ Component Isolation: Clear boundaries between stores, composables, components
- ✅ API Contracts: JSDoc types validate backend contract compliance
- ✅ Real-Time State Sync: Event-action mapping + full state snapshot on reconnect
- ✅ AI Graceful Degradation: WebSocket events handle AI timeouts transparently

**Next Phase**: Phase 1 - Generate data-model.md and API contracts based on these technical decisions.
