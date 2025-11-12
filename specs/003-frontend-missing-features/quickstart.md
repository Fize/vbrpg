# Quick Start: Frontend Missing Features Development

**Branch**: `003-frontend-missing-features`  
**Last Updated**: 2025-11-12  
**Estimated Setup Time**: 15 minutes

## Prerequisites

Ensure you have the following installed:
- **Node.js**: 18.x or 20.x (verify with `node --version`)
- **pnpm**: 8.x (install via `npm install -g pnpm`)
- **Git**: 2.x
- **VSCode**: Latest (recommended for JSDoc support)

Backend must be running on `http://localhost:8000`:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## Quick Setup (5 minutes)

### 1. Clone and Install

```bash
# If not already in project root
cd /home/xuxu/github.com/vbrpg

# Checkout feature branch
git checkout 003-frontend-missing-features

# Install frontend dependencies
cd frontend
pnpm install
```

### 2. Start Development Server

```bash
# From frontend/ directory
pnpm dev
```

Frontend will be available at **http://localhost:5173**

### 3. Verify Backend Connection

Open browser console (F12) and check for:
```
WebSocket connected to http://localhost:8000
```

If connection fails, ensure backend is running on port 8000.

---

## Project Structure Overview

```
frontend/
├── src/
│   ├── components/       # Vue components (game/, profile/, room/, common/)
│   ├── composables/      # Reusable logic (useAuth, useWebSocket, useGameState)
│   ├── services/         # API clients (api.js, websocket.js)
│   ├── stores/           # Pinia state (auth, game, room, profile)
│   ├── views/            # Page components (RegisterView, GameView, etc.)
│   └── types/            # JSDoc type definitions (player.js, game.js, etc.)
│
├── tests/
│   ├── unit/             # Vitest unit tests (composables, services, stores)
│   ├── component/        # Vitest component tests (Vue components)
│   └── e2e/              # Playwright end-to-end tests
│
├── vite.config.js        # Vite configuration
├── vitest.config.js      # Vitest test configuration
└── playwright.config.js  # Playwright E2E configuration
```

---

## Development Workflow

### Test-First Development (MANDATORY)

Per Constitution §I, all code MUST be preceded by tests. Follow Red-Green-Refactor cycle:

#### 1. Write Failing Test (RED)

**Example: User Registration (FR-001)**

```bash
# Create test file FIRST
touch tests/unit/composables/useRegistration.spec.js
```

```javascript
// tests/unit/composables/useRegistration.spec.js
import { describe, it, expect, vi } from 'vitest'
import { useRegistration } from '@/composables/useRegistration'

describe('useRegistration', () => {
  it('validates username length', () => {
    const { validateUsername } = useRegistration()
    
    expect(validateUsername('ab')).toBe(false) // Too short
    expect(validateUsername('validUser123')).toBe(true) // Valid
    expect(validateUsername('a'.repeat(21))).toBe(false) // Too long
  })
})
```

Run test (should FAIL):
```bash
pnpm test useRegistration
```

#### 2. Implement Code (GREEN)

```bash
# Now create implementation file
touch src/composables/useRegistration.js
```

```javascript
// src/composables/useRegistration.js
/**
 * @typedef {Object} ValidationResult
 * @property {boolean} isValid
 * @property {string|null} error
 */

/**
 * User registration composable
 * @returns {Object}
 */
export function useRegistration() {
  /**
   * Validate username length (FR-002)
   * @param {string} username
   * @returns {boolean}
   */
  function validateUsername(username) {
    return username.length >= 3 && username.length <= 20
  }
  
  return { validateUsername }
}
```

Run test (should PASS):
```bash
pnpm test useRegistration
```

#### 3. Refactor (REFACTOR)

Improve code quality while keeping tests green:
```javascript
// src/composables/useRegistration.js (refactored)
const USERNAME_MIN_LENGTH = 3
const USERNAME_MAX_LENGTH = 20

export function useRegistration() {
  function validateUsername(username) {
    if (typeof username !== 'string') return false
    return username.length >= USERNAME_MIN_LENGTH && 
           username.length <= USERNAME_MAX_LENGTH
  }
  
  return { validateUsername }
}
```

Run test again (should still PASS):
```bash
pnpm test useRegistration
```

---

## Running Tests

### Unit Tests (Vitest)

```bash
# Run all unit tests
pnpm test

# Run specific test file
pnpm test useRegistration

# Run with coverage
pnpm test:coverage

# Watch mode (auto-rerun on file changes)
pnpm test:watch

# UI mode (visual test runner)
pnpm test:ui
```

**Coverage Target**: 80%+ for composables, stores, services

### E2E Tests (Playwright)

```bash
# Ensure backend and frontend are running first

# Run all E2E tests
pnpm test:e2e

# Run specific test file
pnpm test:e2e registration.spec.js

# Run with UI (visual debugging)
pnpm test:e2e:ui

# Run in debug mode (step-by-step)
pnpm test:e2e:debug
```

**Important**: E2E tests require real backend. Start backend before running:
```bash
# Terminal 1: Backend
cd backend && uvicorn main:app --reload

# Terminal 2: Frontend
cd frontend && pnpm dev

# Terminal 3: E2E Tests
cd frontend && pnpm test:e2e
```

---

## Common Development Tasks

### Creating a New Component

```bash
# 1. Create test file FIRST
touch tests/component/components/profile/ProfileCard.spec.js

# 2. Write component test
# See tests/unit/components/JoinRoomForm.spec.js for example

# 3. Run test (should fail)
pnpm test ProfileCard

# 4. Create component
touch src/components/profile/ProfileCard.vue

# 5. Implement component until test passes
# 6. Run test again (should pass)
```

### Adding a New API Endpoint

```bash
# 1. Update JSDoc types
# Edit src/types/player.js to add new types

# 2. Create service method test
touch tests/unit/services/api.spec.js

# 3. Implement service method in src/services/api.js
# 4. Create contract test (validates against backend)
touch tests/integration/api/players.spec.js
```

### Adding a WebSocket Event Handler

```bash
# 1. Update AsyncAPI contract
# Edit specs/003-frontend-missing-features/contracts/api-websocket.yaml

# 2. Create composable test
touch tests/unit/composables/useGameEvents.spec.js

# 3. Implement event handler in composable
# 4. Wire into WebSocket service (src/services/websocket.js)
```

---

## Debugging Tips

### WebSocket Connection Issues

```javascript
// In browser console (F12)
localStorage.setItem('debug', 'socket.io-client:*')
// Refresh page to see Socket.IO debug logs
```

### API Request Failures

```javascript
// Check network tab (F12 > Network)
// Filter by XHR to see API calls
// Look for 4xx/5xx status codes

// Enable Axios debug logging
// Edit src/services/api.js
axios.interceptors.request.use(config => {
  console.log('API Request:', config.method, config.url, config.data)
  return config
})
```

### State Management Issues

```javascript
// Install Vue DevTools extension
// Pinia tab shows all stores and state changes
// Time-travel debugging available
```

### Test Failures

```bash
# Run single test with verbose output
pnpm test -- --reporter=verbose useRegistration

# Run with browser (for component tests)
pnpm test:ui
# Then click failing test to see DOM snapshot
```

---

## Code Style Guidelines

### JSDoc Type Annotations (RQ-006)

**All functions MUST have JSDoc comments:**

```javascript
/**
 * Submit player action to backend
 * @param {GameAction} action - Action to submit
 * @returns {Promise<boolean>} True if action accepted
 * @throws {Error} If action validation fails
 */
async function submitAction(action) {
  // Implementation
}
```

### Component Structure

```vue
<template>
  <!-- Template with minimal logic -->
</template>

<script setup>
// 1. Imports
import { ref, computed } from 'vue'
import { useGameStore } from '@/stores/game'

// 2. Props/Emits
const props = defineProps({
  playerId: { type: Number, required: true }
})

const emit = defineEmits(['action-submitted'])

// 3. Composables
const gameStore = useGameStore()

// 4. State
const selectedAction = ref(null)

// 5. Computed
const canSubmit = computed(() => ...)

// 6. Methods
function handleSubmit() { ... }

// 7. Lifecycle (if needed)
onMounted(() => { ... })
</script>

<style scoped>
/* Component-specific styles */
</style>
```

### Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Components | PascalCase | `ProfileCard.vue` |
| Composables | camelCase with `use` prefix | `useGameActions.js` |
| Stores | camelCase with `use` + `Store` | `useAuthStore()` |
| Constants | SCREAMING_SNAKE_CASE | `MAX_PLAYERS` |
| Events | kebab-case | `emit('action-submitted')` |

---

## Useful Commands

```bash
# Linting
pnpm lint              # Check for issues
pnpm lint --fix        # Auto-fix issues

# Formatting
pnpm format            # Format all files with Prettier

# Build
pnpm build             # Production build
pnpm preview           # Preview production build

# Dependencies
pnpm add <package>     # Add new dependency
pnpm add -D <package>  # Add dev dependency
pnpm update            # Update dependencies

# Cleanup
rm -rf node_modules .vite && pnpm install  # Fresh install
```

---

## Getting Help

### Documentation References

- **Research Decisions**: `specs/003-frontend-missing-features/research.md`
- **Data Models**: `specs/003-frontend-missing-features/data-model.md`
- **REST API Contract**: `specs/003-frontend-missing-features/contracts/api-rest.yaml`
- **WebSocket Contract**: `specs/003-frontend-missing-features/contracts/api-websocket.yaml`
- **Feature Spec**: `specs/003-frontend-missing-features/spec.md`

### Example Code

Study existing implementations:
- **Composables**: `src/composables/` (existing patterns)
- **Store**: `src/stores/auth.js` (Pinia setup API example)
- **Component Test**: `tests/unit/components/JoinRoomForm.spec.js` (test structure)
- **E2E Test**: `tests/e2e/join-room.spec.js` (Playwright example)

### Common Issues

| Issue | Solution |
|-------|----------|
| "Port 5173 already in use" | Kill process: `lsof -ti:5173 \| xargs kill -9` |
| "WebSocket connection failed" | Ensure backend running on port 8000 |
| "Module not found" | Run `pnpm install` |
| "Test timeout" | Increase timeout in test: `{ timeout: 10000 }` |
| "Type errors in JSDoc" | Add `@ts-ignore` above line (temporary fix) |

---

## Next Steps

1. ✅ **Setup Complete** - You can now start development
2. 📋 **Read Feature Spec** - `specs/003-frontend-missing-features/spec.md` (6 user stories)
3. 🔬 **Start with P1 Tasks** - User Registration (highest priority)
4. ✅ **Write Tests First** - Follow Red-Green-Refactor cycle
5. 🧪 **Run Tests Frequently** - `pnpm test:watch` for instant feedback

**Remember**: Test-first is NON-NEGOTIABLE (Constitution §I). No code without tests!

---

## Contact

For technical questions or clarifications, refer to:
- Feature specification: `specs/003-frontend-missing-features/spec.md`
- Constitution: `.specify/memory/constitution.md`
- Implementation plan: `specs/003-frontend-missing-features/plan.md`
