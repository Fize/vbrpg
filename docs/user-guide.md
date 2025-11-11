# VBRPG User Guide

## Table of Contents

- [Getting Started](#getting-started)
- [Creating Your First Game Room](#creating-your-first-game-room)
- [Joining a Friend's Game Room](#joining-a-friends-game-room)
- [Managing AI Agents in Your Room](#managing-ai-agents-in-your-room)
- [Starting and Playing the Game](#starting-and-playing-the-game)
- [Troubleshooting](#troubleshooting)

---

## Getting Started

Welcome to VBRPG (Virtual Board Role-Playing Game)! This guide will walk you through the core features of the platform, including creating rooms, joining friends' games, and managing AI agents.

### System Requirements

- Modern web browser (Chrome, Firefox, Safari, or Edge)
- Stable internet connection
- JavaScript enabled

### Account Setup

1. **Guest Access**: Click "Play as Guest" for quick access with limited features
2. **Registered Account**: Sign up for full features including save progress and stats

---

## Creating Your First Game Room

### Step 1: Navigate to Room Creation

1. From the main dashboard, click the **"Create New Room"** button
2. You'll be taken to the room configuration screen

### Step 2: Configure Room Settings

**Basic Settings**:
- **Max Players**: Choose 2-8 players (default: 4)
  - _Note: Game type requirements apply (e.g., Crime Scene requires 4-8 players)_
- **Difficulty**: Select Easy, Medium, or Hard
- **Turn Time Limit**: Set 30-300 seconds per turn
- **AI Narrator**: Toggle to enable/disable AI game narration

**Example Configuration**:
```
Max Players: 4
Difficulty: Medium
Turn Time Limit: 60 seconds
AI Narrator: Enabled
```

### Step 3: Create Room

1. Click **"Create Room"** button
2. You'll receive a unique **6-character room code** (e.g., `ABC123`)
3. Share this code with friends to invite them

### Room Status

After creation, you'll enter the **Waiting Lobby** where you can:
- View connected participants
- Manage AI agents (see [Managing AI Agents](#managing-ai-agents-in-your-room))
- Wait for other players to join
- Start the game when ready

---

## Joining a Friend's Game Room

### Method 1: Using Room Code

**Step-by-Step Instructions**:

1. **Get the Room Code**
   - Ask the room creator for their 6-character room code
   - Example: `ABC123`

2. **Navigate to Join Screen**
   - From the main dashboard, click **"Join Existing Room"**
   - Or use the "Enter Room Code" input field

3. **Enter Room Code**
   - Type the 6-character code (case-insensitive)
   - Valid characters: A-Z, 0-9
   - Example: `abc123` or `ABC123` both work

4. **Click "Join Room"**
   - System validates the code
   - You'll be added to the lobby if space is available

5. **Wait in Lobby**
   - You'll see the participant list with all players and AI agents
   - Room owner is marked with an **"Owner"** badge
   - Wait for the owner to start the game

### What You'll See in the Lobby

**Participant List**:
```
┌──────────────────────────────────┐
│  Room: ABC123        Players: 3/4│
├──────────────────────────────────┤
│ 👤 Alice         [Owner]         │
│ 👤 Bob                           │
│ 👤 Charlie                       │
│ 🤖 AI玩家1                        │
└──────────────────────────────────┘
```

- **Human players**: Show username and avatar
- **AI agents**: Display sequential names (AI玩家1, AI玩家2, etc.)
- **Owner badge**: Indicates who controls room settings
- **Capacity**: Shows current/maximum players (e.g., 3/4)

### Join Status Messages

**Success**:
- ✅ "Successfully joined room ABC123"
- You'll see the lobby with all participants

**Common Errors**:
- ❌ **"Room is full"** (409): All slots occupied, wait or try another room
- ❌ **"Room not found"** (404): Invalid code or room dissolved
- ❌ **"Game already started"** (409): Cannot join games in progress
- ❌ **"Already in this room"** (400): You're already a participant

### Real-Time Updates

The lobby automatically updates when:
- New players join (receive `player_joined` event)
- Players leave (receive `player_left` event)
- AI agents are added/removed (if you're not the owner, you see these updates)
- Ownership transfers (see new owner badge)

**Latency**: Updates typically arrive within **1-2 seconds**

---

## Managing AI Agents in Your Room

_Note: Only the **room owner** can manage AI agents._

### Overview

AI agents fill empty slots when you don't have enough human players. They:
- Count toward the total player count
- Follow game rules automatically
- Cannot become room owners
- Are removed if the room needs space for human players (manual removal only)

### Adding AI Agents

**Requirements**:
- You must be the room owner
- Room must have available slots (current players < max players)
- Game must not be started yet

**Steps**:

1. **Locate the "Add AI Agent" Button**
   - Found below the participant list in the lobby
   - Only visible to room owner

2. **Click "Add AI Agent"**
   - System creates a new AI participant
   - AI is automatically named sequentially: `AI玩家1`, `AI玩家2`, `AI玩家3`, etc.

3. **AI Appears in Participant List**
   - Marked with 🤖 robot icon
   - Shows Chinese name (AI玩家 = AI Player)
   - Counts toward room capacity

**Example**:
```
Before:                    After clicking "Add AI Agent":
┌──────────────────┐      ┌──────────────────┐
│  Players: 2/4    │      │  Players: 3/4    │
├──────────────────┤      ├──────────────────┤
│ 👤 Alice [Owner] │      │ 👤 Alice [Owner] │
│ 👤 Bob           │      │ 👤 Bob           │
│                  │      │ 🤖 AI玩家1        │
└──────────────────┘      └──────────────────┘
```

### Removing AI Agents

**Steps**:

1. **Find the AI Agent in Participant List**
   - Each AI has a ❌ remove button next to it
   - Only visible to room owner

2. **Click the ❌ Remove Button**
   - Confirm the action if prompted
   - AI is immediately removed from the room

3. **Slot Becomes Available**
   - Room capacity decreases by 1
   - Slot can be filled by human players or new AI

**Example**:
```
Before:                    After clicking ❌ next to AI玩家1:
┌──────────────────┐      ┌──────────────────┐
│  Players: 3/4    │      │  Players: 2/4    │
├──────────────────┤      ├──────────────────┤
│ 👤 Alice [Owner] │      │ 👤 Alice [Owner] │
│ 👤 Bob           │      │ 👤 Bob           │
│ 🤖 AI玩家1 ❌     │      │                  │
└──────────────────┘      └──────────────────┘
```

### AI Agent Naming

AI agents are named sequentially based on the order they're added:
- First AI: `AI玩家1`
- Second AI: `AI玩家2`
- Third AI: `AI玩家3`
- And so on...

**Name Behavior**:
- If you remove AI玩家1 and add a new AI, it becomes AI玩家1 again (fills lowest available number)
- Names always reflect current numbering order

### Non-Owner View

If you're **not the room owner**:
- You can **see** AI agents in the participant list
- You **cannot** add or remove AI agents
- You receive real-time updates when owner adds/removes AI
- No AI management buttons are visible to you

### Error Messages

**Cannot Add AI**:
- ❌ **"Room is full"** (409): All slots occupied, remove a player or AI first
- ❌ **"Not room owner"** (403): Only owner can manage AI
- ❌ **"Game already started"** (409): Cannot modify participants after game starts

**Cannot Remove AI**:
- ❌ **"AI agent not found"** (404): AI doesn't exist or already removed
- ❌ **"Not room owner"** (403): Only owner can manage AI

---

## Starting and Playing the Game

### Pre-Game Checklist

Before starting the game, ensure:
- ✅ Minimum player requirement met (varies by game type)
  - Crime Scene: 4-8 players (human + AI combined)
- ✅ All players are ready
- ✅ AI agents configured as desired
- ✅ You are the room owner (only owner can start)

### Starting the Game

1. **Click "Start Game" Button**
   - Located at the bottom of the lobby screen
   - Only visible to room owner

2. **System Validation**
   - Checks minimum player count
   - Verifies room status
   - Initializes game state

3. **Game Begins**
   - All players redirected to game screen
   - Lobby is locked (no new joins allowed)

### During the Game

**Leaving During Game**:
- You **cannot** leave a room while the game is in progress
- Error message: "Cannot leave room while game is active"
- Workaround: Wait until game completes or ask owner to end the game

**Ownership During Game**:
- Ownership cannot be transferred during active gameplay
- If owner disconnects, game continues but room cannot be modified

---

## Troubleshooting

### Common Issues and Solutions

#### "Room not found" when joining

**Possible Causes**:
- Room code is incorrect (check spelling and case)
- Room was dissolved (last human player left)
- Room expired due to inactivity

**Solutions**:
- Verify room code with the creator
- Ask creator to create a new room if dissolved
- Ensure room is still active

---

#### "Room is full" error

**Cause**: All player slots are occupied (human players + AI agents = max capacity)

**Solutions**:
- Wait for a player to leave
- Ask room owner to remove an AI agent to free a slot
- Join a different room or create your own

---

#### Cannot see AI management buttons

**Cause**: You are not the room owner

**Solution**:
- Only the room owner can add/remove AI agents
- If you need to manage AI, ask the current owner to transfer ownership (if supported)
- Or create your own room

---

#### Ownership transferred unexpectedly

**Cause**: The previous owner left the room

**Behavior**:
- Ownership automatically transfers to the earliest-joined human player
- You may become owner if you joined earliest
- AI agents are never eligible for ownership

**What to do**:
- Check for the "Owner" badge next to your name
- If you're now owner, you gain AI management controls
- Room continues operating normally

---

#### Room dissolved without warning

**Causes**:
- Last human player left the room
- Only AI agents remained (rooms cannot exist with only AI)
- Room timeout due to inactivity

**What to do**:
- Room is permanently deleted (cannot be rejoined)
- Create a new room if needed
- Ensure at least one human stays in the room to keep it alive

---

#### Real-time updates are slow

**Expected Latency**: < 1-2 seconds for lobby events

**If updates are slower**:
- Check your internet connection
- Refresh the browser page
- Reconnect to the room if disconnected

---

### Getting Help

If you encounter issues not covered here:
1. Check the [API Documentation](./api.md) for technical details
2. Contact support with:
   - Room code (if applicable)
   - Error message (exact text)
   - Steps to reproduce
   - Browser and OS information

---

## Quick Reference

### Room Codes
- **Format**: 6 alphanumeric characters (A-Z, 0-9)
- **Example**: ABC123, XYZ789
- **Case**: Insensitive (abc123 = ABC123)

### Room Capacity
- **Min Players**: Varies by game type (typically 2-4)
- **Max Players**: 2-8 (configurable at room creation)
- **AI Agents**: Count toward total capacity

### Room Owner Privileges
- Start the game
- Add/remove AI agents
- Configure room settings (before start)
- Cannot be AI agent (always human)

### Room Statuses
- **Waiting**: Lobby phase, players can join/leave
- **In Progress**: Game active, no joins allowed
- **Completed**: Game finished, room archived

---

**Version**: 1.0.0 (Feature 002: Room Join & AI Agent Management)  
**Last Updated**: 2025-11-09
