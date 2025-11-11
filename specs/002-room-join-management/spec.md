# Feature Specification: Multiplayer Room Join & AI Agent Management

**Feature Branch**: `002-room-join-management`  
**Created**: 2025-11-09  
**Status**: Draft  
**Input**: User description: "其他用户还没办法加入房间一起游戏。房主没办法指定使用ai agent加入游戏，我需要这些功能"

## Clarifications

### Session 2025-11-09

- Q: 房主离开房间时的处理规则？ → A: 自动转移给下一个最早加入的人类玩家；如果只剩AI则解散房间
- Q: AI代理的命名方式？ → A: 系统自动生成名称（如"AI玩家1"、"AI玩家2"、"AI玩家3"）
- Q: 游戏开始时的最小人类玩家要求？ → A: 允许纯AI游戏（0个人类玩家），用于测试或演示，人类玩家可以作为观众进行观看
- Q: 两个玩家同时尝试加入最后一个空位时的冲突解决？ → A: 先到先得（基于服务器接收请求的时间戳），后到者看到"房间已满"错误
- Q: 玩家在大厅中断线后的重连行为？ → A: 立即释放位置，但玩家可以用相同房间码重新加入（如果还有空位）

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Player Joins Existing Game Room (Priority: P1)

A player wants to join their friend's game room to play together. They receive a room code from the room creator, enter it into the system, and successfully join the lobby where they can see other players and wait for the game to start.

**Why this priority**: This is the core multiplayer functionality - without it, players cannot join rooms together, defeating the purpose of a multiplayer platform. This is the most critical missing feature.

**Independent Test**: Can be fully tested by having one player create a room, another player use the room code to join, and verifying both players appear in the same lobby. Delivers immediate value by enabling basic multiplayer functionality.

**Acceptance Scenarios**:

1. **Given** a player has a valid 6-character room code from a friend, **When** they enter the code and click join, **Then** they successfully enter the game room lobby and see the room creator and any other players already in the room
2. **Given** a player is on the main screen, **When** they select "Join Game" and enter a valid room code, **Then** they are added to that room's participant list
3. **Given** a game room is full (at maximum player capacity), **When** another player tries to join with the room code, **Then** they see an error message indicating the room is full
4. **Given** a player enters an invalid or non-existent room code, **When** they try to join, **Then** they see a clear error message explaining the room doesn't exist

---

### User Story 2 - Room Owner Manages AI Agent Slots (Priority: P1)

The room owner wants control over which player slots are filled by AI agents versus waiting for human players. They can manually add or remove AI agents before starting the game, allowing them to balance the game for the number of human players who joined.

**Why this priority**: This gives room owners control over game composition, allowing them to start games with specific AI/human ratios rather than automatic AI filling. This is essential for flexible game management and user satisfaction.

**Independent Test**: Can be tested by creating a room, manually adding AI agents to specific slots, verifying AI agents appear in the player list, and confirming the game starts with the specified configuration. Delivers value by giving room owners control over game setup.

**Acceptance Scenarios**:

1. **Given** a room owner is in the lobby with empty player slots, **When** they click "Add AI Agent" for a specific slot, **Then** an AI agent is added to that slot and appears in the participant list with an AI indicator
2. **Given** a room owner has added AI agents to slots, **When** they click "Remove" on an AI agent, **Then** that AI agent is removed and the slot becomes available for human players
3. **Given** a room owner has configured AI agents, **When** they start the game, **Then** the game begins with the specified mix of human players and AI agents
4. **Given** a room has both human players and AI agents, **When** the room owner adds more AI agents up to the maximum player count, **Then** all slots can be filled with any combination of humans and AI
5. **Given** a human player joins a room after AI agents were added, **When** the room owner wants to replace an AI with the human, **Then** they can remove the AI agent to free up a slot for the human player

---

### User Story 3 - Real-Time Lobby Updates (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

When players join or leave a game room, or when the room owner adds/removes AI agents, all participants see these changes immediately in their lobby view without needing to refresh. This creates a responsive, connected multiplayer experience.

**Why this priority**: Real-time updates improve user experience and prevent confusion about room state. While important, players can manually refresh if needed, making this lower priority than basic join functionality.

**Independent Test**: Can be tested by having multiple players in the same room lobby and verifying that when one player joins/leaves or the owner adds/removes an AI agent, all other players' screens update automatically within 1 second. Delivers value by providing modern real-time UX expectations.

**Acceptance Scenarios**:

1. **Given** multiple players are in the same game room lobby, **When** a new player joins, **Then** all existing players see the new player appear in their participant list within 1 second
2. **Given** players are waiting in a lobby, **When** another player leaves the room, **Then** all remaining players see that player removed from the list within 1 second
3. **Given** players are in a lobby, **When** the room owner adds an AI agent, **Then** all players see the AI agent appear in the participant list within 1 second
4. **Given** players are in a lobby, **When** the room owner removes an AI agent, **Then** all players see that AI agent disappear from the list within 1 second
5. **Given** a player's connection is temporarily disrupted, **When** they reconnect within 5 minutes, **Then** they see the current accurate state of the lobby

---

### Edge Cases

- Player tries to join a room that just transitioned from "Waiting" to "In Progress": Join request is rejected with "game already started" error (per FR-004)
- Two players simultaneously try to join the last remaining slot: Server uses timestamp ordering; first request succeeds, second receives "room full" error (per FR-018)
- Room owner leaves when other human players are present: Ownership automatically transfers to the earliest-joined human player (per FR-014)
- Room owner leaves when only AI agents remain: Room is immediately dissolved and all AI agents are removed (per FR-014)
- Player joins the same room in multiple browser tabs: System detects duplicate based on player ID and rejects subsequent join attempts from same player (per FR-012)
- Room owner adds an AI agent at the exact moment a human player joins: Server processes requests sequentially; whichever arrives first is accepted, the other succeeds only if slots remain
- Empty game rooms with no players: Rooms are cleaned up after 30 minutes of inactivity in "Waiting" status (per Assumptions)
- Player disconnects while in the lobby: Their slot is immediately released; they can rejoin using the room code if space is available (per FR-019)
- Game starts with 0 human players (pure AI): Allowed for testing/demonstration purposes; human players can observe as spectators (per FR-015, FR-017)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow players to join an existing game room by entering a valid 6-character room code
- **FR-002**: System MUST validate room codes and display appropriate error messages for invalid or non-existent codes
- **FR-003**: System MUST prevent players from joining rooms that are full (at maximum capacity)
- **FR-004**: System MUST prevent players from joining rooms that have already started (status is "In Progress" or "Completed")
- **FR-005**: Room owners MUST be able to manually add AI agents to available player slots in the lobby
- **FR-006**: Room owners MUST be able to remove AI agents they have added before the game starts
- **FR-007**: System MUST display AI agents differently from human players in the participant list (with clear visual indicator) and assign automatic sequential names (e.g., "AI玩家1", "AI玩家2", "AI玩家3")
- **FR-008**: System MUST broadcast real-time updates to all lobby participants when players join, leave, or AI agents are added/removed
- **FR-009**: System MUST update the participant list within 1 second for all lobby members when changes occur
- **FR-010**: System MUST track which player is the room owner and grant them exclusive AI agent management permissions
- **FR-011**: System MUST maintain accurate player count and available slot information for each room
- **FR-012**: System MUST prevent duplicate joins (same player joining the same room multiple times) but allow rejoining after disconnection if slots are available
- **FR-013**: Players MUST be able to voluntarily leave a room while it is in "Waiting" status
- **FR-014**: System MUST automatically transfer room ownership to the next earliest-joined human player when the current owner leaves; if only AI agents remain, the room MUST be dissolved
- **FR-015**: System MUST support any combination of human players and AI agents up to the maximum room capacity, including pure AI games (0 human players) for testing or spectator scenarios
- **FR-016**: System MUST persist lobby state changes (joins, leaves, AI additions/removals) to the database
- **FR-017**: System MUST allow games to start with any number of human players (including 0) as long as total player count (humans + AI) meets the game type's minimum requirement
- **FR-018**: System MUST resolve concurrent join conflicts using server-side timestamp ordering (first request accepted, subsequent requests rejected with "room full" error)
- **FR-019**: System MUST immediately release a disconnected player's slot but allow them to rejoin using the same room code if space remains available

### Key Entities

- **GameRoomParticipant**: Represents a player (human or AI) in a game room, with attributes including player reference, room reference, join timestamp, participant type (human/AI), and owner status
- **GameRoom**: Extended attributes including current participant count, available slots, and owner player reference
- **Player**: User or AI agent that can participate in game rooms
- **LobbyUpdate Event**: Real-time event broadcast to all room participants when lobby state changes (player joined, player left, AI added, AI removed)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Players can successfully join a game room by entering a 6-character code in under 5 seconds (from code entry to appearing in lobby)
- **SC-002**: Room owners can add or remove AI agents in under 3 seconds per action
- **SC-003**: All lobby participants see join/leave/AI agent updates within 1 second on 95% of actions
- **SC-004**: System handles 50 concurrent game rooms each with players joining/leaving simultaneously without errors
- **SC-005**: 90% of players successfully join their intended room on the first attempt (valid code entry)
- **SC-006**: Zero instances of duplicate player entries in the same room
- **SC-007**: 100% of room owner actions (add/remove AI) are properly authorized and executed
- **SC-008**: Lobby state remains consistent across all client views even during rapid join/leave sequences

## Assumptions

- The existing 6-character room code system remains unchanged and is already functioning for room creation
- The maximum player capacity per room is defined in the game type configuration (e.g., 4-8 players depending on game)
- Players are already identified with a unique player ID from guest mode or account system
- The existing WebSocket infrastructure can support the additional real-time lobby update events
- AI agents are created on-demand when added by the room owner and don't require pre-provisioning
- Room cleanup for abandoned rooms will happen after 30 minutes of inactivity in "Waiting" status
- Server-side clock is the authoritative source for timestamp-based conflict resolution
- Disconnected players do not maintain session state; rejoining is treated as a new join request
- AI agent naming follows a simple sequential pattern within each room (resets per room)


