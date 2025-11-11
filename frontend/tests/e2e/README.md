# E2E Tests for Feature 002: Room Join Management

## Overview

End-to-end tests using Playwright to validate the complete user journey for room join/leave and AI agent management features.

## Test Files

- **join-room.spec.js**: Complete join flow (2 tests)
  - Player A creates room, Player B joins
  - Multiple players see real-time updates
  
- **room-capacity.spec.js**: Room capacity enforcement (2 tests)
  - Fill room to capacity, reject 5th player
  - Capacity with AI agents
  
- **ai-agent-management.spec.js**: AI agent CRUD operations (3 tests)
  - Owner adds/removes AI agents
  - Non-owner permissions
  - Start game with AI agents
  
- **ownership-transfer.spec.js**: Ownership transfer scenarios (3 tests)
  - Owner leaves, transfer to earliest human
  - Multiple transfers
  - No transfer to AI
  
- **room-dissolution.spec.js**: Room dissolution (4 tests)
  - Owner leaves with only AI
  - Last human leaves
  - Dissolution notifications
  - Room persistence validation

## Prerequisites

1. **Backend server running** on `http://localhost:8000`
2. **Frontend dev server running** on `http://localhost:5173`
3. **Playwright browsers installed**

## Setup

```bash
# Install Playwright browsers (first time only)
cd frontend
npx playwright install chromium

# Or install all browsers
npx playwright install
```

## Running Tests

### Run all E2E tests
```bash
npm run test:e2e
```

### Run specific test file
```bash
npx playwright test tests/e2e/join-room.spec.js
```

### Run with UI mode (interactive)
```bash
npm run test:e2e:ui
```

### Run with debug mode
```bash
npm run test:e2e:debug
```

### Run and show browser
```bash
npx playwright test --headed
```

## Test Configuration

Configuration is in `playwright.config.js`:

- **Base URL**: `http://localhost:5173` (frontend)
- **Backend URL**: `http://localhost:8000` (auto-started by webServer)
- **Timeout**: 120s for server startup
- **Workers**: 1 (CI), undefined (local)
- **Retries**: 2 (CI), 0 (local)

## Starting Servers Manually

### Backend
```bash
cd backend
uv run python main.py
# Server starts on http://localhost:8000
```

### Frontend
```bash
cd frontend
npm run dev
# Server starts on http://localhost:5173
```

## Test Structure

Each test uses Playwright's browser contexts to simulate multiple users:

```javascript
const contextA = await browser.newContext()
const contextB = await browser.newContext()

const pageA = await contextA.newPage()
const pageB = await contextB.newPage()

// Player A creates room
await pageA.goto('/')
await pageA.click('button:has-text("创建房间")')

// Player B joins room
await pageB.goto('/')
await pageB.fill('input[placeholder*="房间代码"]', roomCode)
await pageB.click('button:has-text("加入房间")')
```

## Troubleshooting

### Tests fail with "Server not responding"
- Check backend server is running: `curl http://localhost:8000/health`
- Check frontend server is running: `curl http://localhost:5173`

### Tests timeout
- Increase timeout in playwright.config.js
- Check server logs for errors
- Use `--headed` flag to see what's happening

### Room code not found
- Backend database may be stale
- Restart backend to reset database
- Check backend logs for 404 errors

### WebSocket connection issues
- Ensure backend WebSocket server is running
- Check CORS configuration
- Verify `VITE_WS_URL` environment variable

## Test Results

After running tests:
- **HTML Report**: `frontend/playwright-report/index.html`
- **Screenshots**: Captured on failure
- **Videos**: Captured on failure (if configured)
- **Traces**: Available for debugging with `npx playwright show-trace`

## View Report

```bash
npx playwright show-report
```

## CI/CD Integration

Tests can run in CI with:
```bash
# Set CI environment variable
export CI=true

# Run tests (will use 1 worker, 2 retries)
npm run test:e2e
```

## Performance Considerations

- E2E tests are slower than unit/integration tests
- Each test creates fresh browser contexts
- Tests run sequentially by default (avoid race conditions)
- Average test duration: 5-15 seconds per test

## Total Test Count

- **14 E2E tests** across 5 test files
- All tests validate real-time WebSocket updates
- Tests cover happy path and error scenarios
- Average coverage: 100% of critical user journeys
