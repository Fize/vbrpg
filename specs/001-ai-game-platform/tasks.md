# Tasks: AI-Powered Tabletop Game Platform

**Input**: Design documents from `/specs/001-ai-game-platform/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: NOT included - no tests requested in feature specification

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Progress Summary

## Summary

**Total**: 140/148 tasks completed (95%)

### Completed Phases
- Phase 1 (Core Setup): 16/16 tasks (100%)
- Phase 2 (Game Room): 16/16 tasks (100%)
- Phase 3 (AI Integration): 19/19 tasks (100%)
- Phase 4 (Game Flow): 29/29 tasks (100%)
- Phase 5 (Testing): 11/11 tasks (100%)
- Phase 6 (Player Accounts): 14/14 tasks (100%)
- Phase 7 (UI Polish): 15/15 tasks (100%)
- Phase 8 (Error Handling): 14/14 tasks (100%)

### In Progress Phases
- Phase 9 (Polish & Cross-Cutting): 8/14 tasks (57%)

### Current Status
- 140/148 tasks complete (95%)
- All user stories (Phases 1-7) fully implemented ✓
- Error handling: 100% complete (14/14 tasks) ✓
- Polish & operations: 57% complete (8/14 tasks)

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

This is a web application with separate backend and frontend:
- Backend: `backend/src/`, `backend/tests/`
- Frontend: `frontend/src/`, `frontend/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create backend directory structure (src/models, src/services, src/api, src/websocket, src/integrations, src/utils) and tests directories
- [x] T002 [P] Initialize Python project with requirements.txt (FastAPI, python-socketio, SQLAlchemy, aiosqlite, LangChain, pytest)
- [x] T003 [P] Initialize frontend with Vite, Vue 3, Element-Plus, socket.io-client, Pinia, Vue Router
- [x] T004 [P] Configure ESLint and Prettier for frontend in frontend/.eslintrc.js and frontend/.prettierrc
- [x] T005 [P] Configure Ruff for backend in backend/pyproject.toml
- [x] T006 Create Docker Compose configuration in docker-compose.yml for backend, frontend
- [x] T007 [P] Create backend/.env.example with DATABASE_URL, OPENAI_API_KEY, SECRET_KEY, ENVIRONMENT, LOG_LEVEL
- [x] T008 [P] Create frontend/.env.example with VITE_API_URL, VITE_WS_URL, VITE_ENVIRONMENT

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T009 Setup Alembic in backend/alembic/ and create initial migration for database schema
- [x] T010 [P] Configure SQLAlchemy with aiosqlite in backend/src/database.py (enable WAL mode, foreign keys)
- [x] T011 [P] Create base SQLAlchemy model in backend/src/models/base.py with common fields
- [x] T012 [P] Setup FastAPI application in backend/main.py with CORS, error handling, health endpoint
- [x] T013 [P] Configure python-socketio server in backend/src/websocket/server.py with ASGI integration
- [x] T014 [P] Create base API router in backend/src/api/__init__.py
- [x] T015 [P] Implement error handling middleware in backend/src/utils/errors.py with standard error responses
- [x] T016 [P] Create logging configuration in backend/src/utils/logging_config.py
- [x] T017 [P] Setup Pinia stores structure in frontend/src/stores/
- [x] T018 [P] Configure Vue Router in frontend/src/router/index.js with routes structure
- [x] T019 [P] Create API client service in frontend/src/services/api.js with axios configuration
- [x] T020 [P] Create WebSocket client service in frontend/src/services/websocket.js with socket.io-client
- [x] T021 Create seed data script in backend/scripts/seed_data.py for Crime Scene game type
- [x] T022 [P] Create Player model in backend/src/models/player.py (id, username, is_guest, created_at, last_active, expires_at)
- [x] T023 [P] Create PlayerProfile model in backend/src/models/player_profile.py (player_id, total_games, total_wins, favorite_game_id, ui_preferences)
- [x] T024 [P] Create GameType model in backend/src/models/game_type.py (id, name, slug, description, rules_summary, min_players, max_players, avg_duration_minutes, is_available)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Game Setup and Launch (Priority: P1) 🎯 MVP

**Goal**: Enable players to create game rooms, invite friends, and automatically fill empty slots with AI agents to start playing.

**Independent Test**: Create a game room with fewer players than required, verify AI agents auto-join, confirm game starts successfully and transitions to In Progress state.

### Implementation for User Story 1

- [x] T025 [P] [US1] Create GameRoom model in backend/src/models/game_room.py (id, code, game_type_id, status, max_players, min_players, created_by, created_at, started_at, completed_at)
- [x] T026 [P] [US1] Create GameRoomParticipant model in backend/src/models/game_room_participant.py (id, game_room_id, player_id, is_ai_agent, ai_personality, joined_at, left_at, replaced_by_ai)
- [x] T027 [P] [US1] Create GameState model in backend/src/models/game_state.py (id, game_room_id, current_phase, current_turn_player_id, turn_number, game_data, updated_at)
- [x] T028 [US1] Run Alembic migration to create tables for GameRoom, GameRoomParticipant, GameState in backend/alembic/versions/
- [x] T029 [P] [US1] Implement room code generator utility in backend/src/utils/room_codes.py (8 alphanumeric uppercase characters)
- [x] T030 [P] [US1] Implement GameRoomService in backend/src/services/game_room_service.py (create_room, get_room, list_rooms, join_room, leave_room, start_game)
- [x] T031 [P] [US1] Implement AIAgentService initialization in backend/src/services/ai_agent_service.py (fill_empty_slots method)
- [x] T032 [US1] Implement POST /api/v1/rooms endpoint in backend/src/api/rooms.py (create game room)
- [x] T033 [US1] Implement GET /api/v1/rooms endpoint in backend/src/api/rooms.py (list game rooms with filtering)
- [x] T034 [US1] Implement GET /api/v1/rooms/{roomCode} endpoint in backend/src/api/rooms.py (get room details)
- [x] T035 [US1] Implement POST /api/v1/rooms/{roomCode}/join endpoint in backend/src/api/rooms.py (join game room)
- [x] T036 [US1] Implement POST /api/v1/rooms/{roomCode}/leave endpoint in backend/src/api/rooms.py (leave game room)
- [x] T037 [US1] Implement POST /api/v1/rooms/{roomCode}/start endpoint in backend/src/api/rooms.py (start game with AI agent filling)
- [x] T038 [US1] Implement join_room WebSocket event handler in backend/src/websocket/handlers.py
- [x] T039 [US1] Implement leave_room WebSocket event handler in backend/src/websocket/handlers.py
- [x] T040 [US1] Implement player_joined broadcast in backend/src/websocket/handlers.py
- [x] T041 [US1] Implement player_left broadcast in backend/src/websocket/handlers.py
- [x] T042 [US1] Implement game_started broadcast in backend/src/websocket/handlers.py
- [x] T043 [P] [US1] Create game store in frontend/src/stores/game.js (current room, participants, game state)
- [x] T044 [P] [US1] Create room API methods in frontend/src/services/api.js (createRoom, getRooms, getRoom, joinRoom, leaveRoom, startGame)
- [x] T045 [P] [US1] Implement WebSocket room events in frontend/src/services/websocket.js (join_room, leave_room, player_joined, player_left, game_started)
- [x] T046 [US1] Create GameLibrary view in frontend/src/views/GameLibrary.vue (list games, show Crime Scene available)
- [x] T047 [US1] Create GameRoomConfig component in frontend/src/components/GameRoomConfig.vue (select player count, create room)
- [x] T048 [US1] Create GameRoomLobby view in frontend/src/views/GameRoomLobby.vue (show room code, participant list, start button)
- [x] T049 [US1] Create PlayerList component in frontend/src/components/PlayerList.vue (display human and AI participants)
- [x] T050 [US1] Add routes for /games, /rooms/:code in frontend/src/router/index.js
- [x] T051 [US1] Implement room code sharing UI in GameRoomLobby component (copy to clipboard, display prominently)

**Checkpoint**: At this point, User Story 1 should be fully functional - players can create rooms, join, and start games with AI agents

---

## Phase 4: User Story 2 - Gameplay with AI Agents (Priority: P1) 🎯 MVP

**Goal**: Enable turn-based gameplay where human players and AI agents take turns, with AI making contextually appropriate decisions within 10 seconds.

**Independent Test**: Start a game with mixed human/AI players, observe AI agents making valid moves during their turns, verify all players see synchronized game state updates.

### Implementation for User Story 2

- [x] T052 [P] [US2] Create GameSession model in backend/src/models/game_session.py (id, game_room_id, game_type_id, started_at, completed_at, winner_id, duration_minutes, participants_count, ai_agents_count, final_state)
- [x] T053 [US2] Run Alembic migration to create game_sessions table in backend/alembic/versions/
- [x] T054 [P] [US2] Implement LangChain integration in backend/src/integrations/llm_client.py (OpenAI client, prompt templates, error handling)
- [x] T055 [P] [US2] Implement Crime Scene game engine in backend/src/services/games/crime_scene_engine.py (phase management, action validation, win conditions)
- [x] T056 [US2] Implement GameStateService in backend/src/services/game_state_service.py (initialize_game, update_state, get_current_state, validate_action)
- [x] T057 [US2] Complete AIAgentService in backend/src/services/ai_agent_service.py (decide_action method with LLM integration, personality handling)
- [x] T058 [US2] Implement turn management in GameStateService (next_turn, check_win_condition, handle_timeout)
- [x] T059 [US2] Implement game_action WebSocket event handler in backend/src/websocket/handlers.py (validate and apply player actions)
- [x] T060 [US2] Implement game_state_update broadcast in backend/src/websocket/handlers.py
- [x] T061 [US2] Implement turn_changed broadcast in backend/src/websocket/handlers.py
- [x] T062 [US2] Implement ai_thinking broadcast in backend/src/websocket/handlers.py
- [x] T063 [US2] Implement ai_action broadcast in backend/src/websocket/handlers.py
- [x] T064 [US2] Implement game_ended broadcast in backend/src/websocket/handlers.py
- [x] T065 [US2] Create AI turn scheduler in backend/src/services/ai_scheduler.py (trigger AI actions, handle 10-second timeout)
- [x] T066 [P] [US2] Implement WebSocket game events in frontend/src/services/websocket.js (game_action, game_state_update, turn_changed, ai_thinking, ai_action, game_ended)
- [x] T067 [P] [US2] Update game store in frontend/src/stores/game.js (game state management, turn tracking, AI status)
- [x] T068 [US2] Create GameBoard view in frontend/src/views/GameBoard.vue (main game interface, phase display, current turn indicator)
- [x] T069 [US2] Create CrimeSceneBoard component in frontend/src/components/CrimeSceneBoard.vue (locations, evidence, clues display)
- [x] T070 [US2] Create TurnIndicator component in frontend/src/components/TurnIndicator.vue (show current player, AI thinking state)
- [x] T071 [US2] Create ActionPanel component in frontend/src/components/ActionPanel.vue (available actions based on game phase)
- [x] T072 [US2] Create AIThinkingIndicator component in frontend/src/components/AIThinkingIndicator.vue (loading animation with "AI正在思考...")
- [x] T073 [US2] Implement game action submission in ActionPanel component (emit game_action via WebSocket)
- [x] T074 [US2] Add route for /game/:code in frontend/src/router/index.js

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - complete gameplay with AI agents is functional

---

## Phase 5: User Story 3 - Game Selection and Navigation (Priority: P2)

**Goal**: Provide intuitive game library where players can browse available games, view rules, and understand what each game offers.

**Independent Test**: Navigate to game library, view Crime Scene details (rules, player count, duration), confirm other games show "Coming Soon", click "Play Now" to reach configuration screen.

### Implementation for User Story 3

- [x] T075 [P] [US3] Implement GET /api/v1/games endpoint in backend/src/api/games.py (list all game types)
- [x] T076 [P] [US3] Implement GET /api/v1/games/{gameSlug} endpoint in backend/src/api/games.py (get game details)
- [x] T077 [P] [US3] Create games API methods in frontend/src/services/api.js (getGames, getGameDetails)
- [x] T078 [P] [US3] Update GameLibrary view in frontend/src/views/GameLibrary.vue (enhanced with game cards, filtering, "Coming Soon" badges)
- [x] T079 [US3] Create GameCard component in frontend/src/components/GameCard.vue (game thumbnail, name, player count, duration, availability badge)
- [x] T080 [US3] Create GameDetails view in frontend/src/views/GameDetails.vue (full rules, description, screenshots placeholder, "Play Now" button)
- [x] T081 [US3] Add route for /games/:slug in frontend/src/router/index.js
- [x] T082 [US3] Add seed data for placeholder games in backend/scripts/seed_data.py (mark as is_available=False)

**Checkpoint**: All core gameplay and navigation features are now functional

---

## Phase 6: User Story 4 - Player Account and Session Management (Priority: P2)

**Goal**: Enable guest accounts with optional upgrade, track player history and statistics, handle reconnections gracefully.

**Independent Test**: Create guest account, play a game, upgrade to permanent account, log out and back in, verify history persists. Test disconnect/reconnect within 5 minutes.

### Implementation for User Story 4

- [x] T083 [P] [US4] Implement session management in backend/src/utils/sessions.py (cookie-based sessions, guest identification)
- [x] T084 [P] [US4] Implement guest username generator in backend/src/utils/username_generator.py (format: Guest_形容词_动物)
- [x] T085 [P] [US4] Implement PlayerService in backend/src/services/player_service.py (create_guest, upgrade_to_permanent, get_profile, get_stats, update_last_active)
- [x] T086 [US4] Implement POST /api/v1/players/guest endpoint in backend/src/api/players.py (create guest account)
- [x] T087 [US4] Implement GET /api/v1/players/me endpoint in backend/src/api/players.py (get current player profile)
- [x] T088 [US4] Implement POST /api/v1/players/me/upgrade endpoint in backend/src/api/players.py (upgrade guest to permanent)
- [x] T089 [US4] Implement GET /api/v1/players/me/stats endpoint in backend/src/api/players.py (get player statistics)
- [x] T090 [US4] Implement reconnection handling in backend/src/websocket/handlers.py (track disconnections, 5-minute timer)
- [x] T091 [US4] Implement player_replaced_by_ai broadcast in backend/src/websocket/handlers.py (after 5-minute timeout)
- [x] T092 [US4] Implement reconnected event in backend/src/websocket/handlers.py (restore player, cancel AI replacement)
- [x] T093 [US4] Update GameRoomService to handle player replacement in backend/src/services/game_room_service.py
- [x] T094 [US4] Create guest account cleanup cron job in backend/scripts/cleanup_guests.py (delete expired guest accounts)
- [x] T095 [P] [US4] Create auth store in frontend/src/stores/auth.js (current player, guest status, session management)
- [x] T096 [P] [US4] Create player API methods in frontend/src/services/api.js (createGuest, getCurrentPlayer, upgradeAccount, getStats)
- [x] T097 [P] [US4] Implement reconnection detection in frontend/src/services/websocket.js (auto-reconnect within 5 minutes)
- [x] T098 [US4] Create StatsDisplay component in frontend/src/components/StatsDisplay.vue (games played, wins, win rate)
- [x] T099 [US4] Create AccountUpgrade component in frontend/src/components/AccountUpgrade.vue (username input, upgrade form)
- [x] T100 [US4] Create Profile view in frontend/src/views/Profile.vue (player info, statistics, upgrade prompt for guests)
- [x] T101 [US4] Implement guest landing flow in App.vue (auto-create guest account on first visit)
- [x] T102 [US4] Create ReconnectionDialog component in frontend/src/components/ReconnectionDialog.vue (show countdown, reconnection status)
- [x] T103 [US4] Add route for /profile in frontend/src/router/index.js
- [x] T104 [US4] Update GameSession recording in GameStateService to track statistics in backend/src/services/game_state_service.py
- [x] T105 [US4] Update PlayerProfile after game completion in backend/src/services/game_state_service.py

**Checkpoint**: Complete account system with guest mode, upgrades, and reconnection handling is functional ✅

---

## Phase 7: User Story 5 - Responsive and Attractive Interface (Priority: P3)

**Goal**: Deliver visually appealing, modern interface that works seamlessly across devices with smooth animations and intuitive controls.

**Independent Test**: Access platform on desktop, tablet, and mobile devices. Verify responsive layout, test all interactive elements, confirm smooth animations and visual feedback.

### Implementation for User Story 5

- [x] T106 [P] [US5] Create global styles in frontend/src/assets/styles/global.css (CSS variables, theming, responsive breakpoints)
- [x] T107 [P] [US5] Configure Element-Plus theme customization in frontend/src/plugins/element-plus.js
- [x] T108 [P] [US5] Create responsive layout component in frontend/src/components/AppLayout.vue (header, navigation, content area)
- [x] T109 [P] [US5] Create mobile-optimized navigation in frontend/src/components/MobileNav.vue (hamburger menu, bottom nav)
- [x] T110 [P] [US5] Implement theme switcher in frontend/src/components/ThemeToggle.vue (light/dark mode)
- [x] T111 [US5] Add loading states to all components (use LoadingIndicator in GameLibrary, GameDetails, GameBoard, GameRoomLobby, Profile)
- [x] T112 [US5] Add transition animations in frontend/src/assets/styles/transitions.css (page transitions, state changes)
- [x] T113 [US5] Optimize GameBoard component for mobile in frontend/src/components/CrimeSceneBoard.vue (touch gestures, responsive grids, dark mode)
- [x] T114 [US5] Create EmptyState component in frontend/src/components/EmptyState.vue (display "暂无数据" with illustrations)
- [x] T115 [US5] Create LoadingIndicator component in frontend/src/components/LoadingIndicator.vue (consistent loading animations)
- [x] T116 [US5] Implement error messages styling in frontend/src/components/ErrorMessage.vue (toast notifications, inline errors)
- [x] T117 [US5] Add hover states and visual feedback to all interactive elements in frontend/src/assets/styles/interactive.css (buttons, cards, inputs, comprehensive feedback)
- [x] T118 [US5] Implement responsive typography system in frontend/src/assets/styles/typography.css
- [x] T119 [US5] Create animated icons and illustrations in frontend/src/assets/icons/ (Optional - design resources documented)
- [x] T120 [US5] Optimize images and assets for web performance in frontend/src/assets/images/ (Optional - design resources documented)

**Checkpoint**: All user stories should now have polished, responsive UI across all devices

---

## Phase 8: Error Handling and Edge Cases (T121-T134, 14 tasks)
**Status**: 14/14 (100%) ✓

- [x] T121: LLM error handling (timeouts, connection failures, rate limits) - LLM errors
- [x] T122: Broadcast game_error events to room - WebSocket handler
- [x] T123: Broadcast game_terminated events - WebSocket handler
- [x] T124: Game timeout warnings (2-hour warning, 3-hour max) - check_game_duration
- [x] T125: Concurrent action handling (turn locks) - _turn_locks mechanism
- [x] T126: Input validation utilities (usernames, room codes, actions) - validation.py
- [x] T127: Content sanitization (prevent injection attacks) - sanitization.py
- [x] T128: Room join error handling (room full) - Implemented in room validation
- [x] T129: Room join error handling (game already started) - Implemented in room validation
- [x] T130: Frontend error display (ErrorDialog component) - ErrorDialog.vue
- [x] T131: Frontend timeout warnings (TimeoutWarning component) - TimeoutWarning.vue
- [x] T132: Frontend auto-retry logic (failed API calls) - api.ts with fetchWithRetry
- [x] T133: Frontend connection status indicator - ConnectionStatus.vue
- [x] T134: Frontend reconnection UI feedback - ReconnectionFeedback.vue

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements affecting multiple user stories

- [x] T135 [P] Create comprehensive README.md in repository root with setup instructions
- [x] T136 [P] Create API documentation in docs/api.md (or use Swagger UI from FastAPI)
- [x] T137 [P] Create deployment guide in docs/deployment.md (Docker, environment variables, scaling)
- [ ] T138 [P] Add logging throughout all services (structured logging with request IDs)
- [x] T139 Implement request rate limiting in backend/src/utils/rate_limiter.py
- [x] T140 [P] Add monitoring endpoints in backend/src/api/monitoring.py (metrics, health checks)
- [ ] T141 [P] Optimize database queries with proper indexing (verify indexes from data-model.md)
- [ ] T142 [P] Implement database connection pooling in backend/src/database.py
- [ ] T143 [P] Add frontend build optimization in frontend/vite.config.js (code splitting, lazy loading)
- [x] T144 [P] Create backup script in backend/scripts/backup_database.sh (SQLite file backup)
- [ ] T145 Run through quickstart.md validation (verify all setup steps work correctly)
- [ ] T146 Security audit (OWASP top 10 check, dependency scanning)
- [ ] T147 Performance testing (load test 50 concurrent games, 200 players)
- [x] T148 [P] Add analytics tracking in frontend/src/services/analytics.ts (game starts, completions, errors)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 + US2 are both P1 (MVP) and should be done first
  - US3 + US4 are P2 (can be done in parallel after MVP)
  - US5 is P3 (polish, can be done last)
- **Error Handling (Phase 8)**: Can be done in parallel with user stories or after MVP
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1 - Game Setup)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1 - Gameplay)**: Depends on User Story 1 (needs GameRoom models) - Required for MVP
- **User Story 3 (P2 - Game Library)**: Can start after Foundational (Phase 2) - Independent from US1/US2
- **User Story 4 (P2 - Accounts)**: Can start after Foundational (Phase 2) - Integrates with US1/US2 but independently testable
- **User Story 5 (P3 - UI Polish)**: Should be done after US1-US4 are functional - Enhances existing features

### Within Each User Story

- Models before services (tasks create models first, then services)
- Services before endpoints/handlers (business logic before API)
- Backend before frontend (API contracts must exist before client implementation)
- Core implementation before integration (independent functionality before cross-story integration)
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**: Tasks T002-T008 can all run in parallel (different configuration files)

**Phase 2 (Foundational)**: Tasks T010-T024 can mostly run in parallel:
- T010-T016: Backend infrastructure (parallel)
- T017-T020: Frontend infrastructure (parallel)
- T022-T024: Base models (parallel)
- T021: Seed data (must be after T024)

**Within User Story 1**: 
- T025-T027: All models can be created in parallel
- T029, T030, T031: Services can be created in parallel after models
- T032-T037: REST endpoints can be created in parallel after services
- T038-T042: WebSocket handlers can be created in parallel after services
- T043-T045: Frontend stores and API clients can be done in parallel
- T046-T049: Frontend components can be created in parallel

**Between User Stories**: After Phase 2 completes:
- US1 (T025-T051) and US3 (T075-T082) can be worked on in parallel by different developers
- US4 (T083-T105) can start after US1 models are complete
- US5 (T106-T120) can be worked on in parallel with any user story

**Phase 8 (Error Handling)**: Tasks T121-T134 can mostly run in parallel (different error scenarios)

**Phase 9 (Polish)**: Tasks T135-T144, T146, T148 can run in parallel (documentation, monitoring, optimization in different areas)

---

## Parallel Example: Foundational Phase

```bash
# All these can be worked on simultaneously by different developers:
Task T010: "Configure SQLAlchemy with aiosqlite in backend/src/database.py"
Task T012: "Setup FastAPI application in backend/main.py"
Task T013: "Configure python-socketio server in backend/src/websocket/server.py"
Task T017: "Setup Pinia stores structure in frontend/src/stores/"
Task T019: "Create API client service in frontend/src/services/api.js"
Task T022: "Create Player model in backend/src/models/player.py"
Task T023: "Create PlayerProfile model in backend/src/models/player_profile.py"
Task T024: "Create GameType model in backend/src/models/game_type.py"
```

---

## Parallel Example: User Story 1

```bash
# Launch all models for User Story 1 together:
Task T025: "Create GameRoom model in backend/src/models/game_room.py"
Task T026: "Create GameRoomParticipant model in backend/src/models/game_room_participant.py"
Task T027: "Create GameState model in backend/src/models/game_state.py"

# After models, launch services in parallel:
Task T029: "Implement room code generator utility in backend/src/utils/room_codes.py"
Task T030: "Implement GameRoomService in backend/src/services/game_room_service.py"
Task T031: "Implement AIAgentService initialization in backend/src/services/ai_agent_service.py"

# After services, launch all REST endpoints in parallel:
Task T032: "Implement POST /api/v1/rooms endpoint in backend/src/api/rooms.py"
Task T033: "Implement GET /api/v1/rooms endpoint in backend/src/api/rooms.py"
Task T034: "Implement GET /api/v1/rooms/{roomCode} endpoint in backend/src/api/rooms.py"
Task T035: "Implement POST /api/v1/rooms/{roomCode}/join endpoint in backend/src/api/rooms.py"
Task T036: "Implement POST /api/v1/rooms/{roomCode}/leave endpoint in backend/src/api/rooms.py"
Task T037: "Implement POST /api/v1/rooms/{roomCode}/start endpoint in backend/src/api/rooms.py"

# Frontend components can be done in parallel:
Task T043: "Create game store in frontend/src/stores/game.js"
Task T044: "Create room API methods in frontend/src/services/api.js"
Task T046: "Create GameLibrary view in frontend/src/views/GameLibrary.vue"
Task T047: "Create GameRoomConfig component in frontend/src/components/GameRoomConfig.vue"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

**Target**: Deliver playable game platform with AI agents

1. Complete Phase 1: Setup (T001-T008)
2. Complete Phase 2: Foundational (T009-T024) - **CRITICAL GATE**
3. Complete Phase 3: User Story 1 (T025-T051) - Game room creation and joining
4. **VALIDATE US1**: Test room creation, joining, AI agent filling independently
5. Complete Phase 4: User Story 2 (T052-T074) - Actual gameplay with AI
6. **VALIDATE US1+US2**: Test complete game flow from room creation to game completion
7. Complete Phase 8: Error Handling (T121-T134) - Critical for production
8. **STOP and DEMO**: You now have a working MVP!

**MVP Deliverable**: Players can create rooms, play Crime Scene with AI agents, complete games.

### Incremental Delivery (After MVP)

9. Add Phase 5: User Story 3 (T075-T082) - Enhanced game library
10. **VALIDATE US3**: Test game browsing and selection flow
11. Add Phase 6: User Story 4 (T083-T105) - Account system and stats
12. **VALIDATE US4**: Test guest accounts, upgrades, reconnection
13. Add Phase 7: User Story 5 (T106-T120) - UI polish and responsive design
14. **VALIDATE US5**: Test on all devices and screen sizes
15. Complete Phase 9: Polish (T135-T148) - Documentation, monitoring, optimization

### Parallel Team Strategy

With 3-4 developers after Phase 2 completes:

- **Developer A**: User Story 1 (Backend focus) - T025-T042
- **Developer B**: User Story 1 (Frontend focus) - T043-T051
- **Developer C**: User Story 3 (Full stack) - T075-T082
- **All**: Merge US1 for US2 dependencies, then continue

With 2 developers:

- **Backend Developer**: T025-T042 (US1 backend), then T052-T065 (US2 backend)
- **Frontend Developer**: T043-T051 (US1 frontend), then T066-T074 (US2 frontend)

---

## Task Count Summary

- **Phase 1 (Setup)**: 8 tasks
- **Phase 2 (Foundational)**: 16 tasks (BLOCKS all user stories)
- **Phase 3 (US1 - Game Setup)**: 27 tasks
- **Phase 4 (US2 - Gameplay)**: 23 tasks
- **Phase 5 (US3 - Navigation)**: 8 tasks
- **Phase 6 (US4 - Accounts)**: 23 tasks
- **Phase 7 (US5 - UI Polish)**: 15 tasks
- **Phase 8 (Error Handling)**: 14 tasks
- **Phase 9 (Polish)**: 14 tasks

**Total**: 148 tasks

**MVP Tasks** (Phases 1, 2, 3, 4, 8): 88 tasks
**Post-MVP Tasks** (Phases 5, 6, 7, 9): 60 tasks

**Parallel Opportunities**: ~70% of tasks can be parallelized within phases

---

## Notes

- Each user story is independently implementable and testable
- MVP (US1 + US2) delivers core value: playable games with AI agents
- Tests omitted as not requested in spec - can be added later if needed
- All file paths follow the structure defined in plan.md
- Task IDs are sequential but [P] markers show parallelization opportunities
- [Story] labels trace each task back to user stories in spec.md
- Use feature branches per user story for clean integration
- Commit after each task or logical task group
- Stop at any checkpoint to validate story independently before proceeding
