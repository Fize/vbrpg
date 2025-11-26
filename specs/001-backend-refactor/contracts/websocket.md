# WebSocket API Contract

**Branch**: 001-backend-refactor  
**Date**: 2025-11-26  
**Purpose**: WebSocket事件定义，用于实时游戏更新

## Overview

WebSocket API用于游戏过程中的实时状态更新，包括游戏状态变化、AI决策通知、玩家操作响应等。所有事件通过Socket.IO协议传输。

## Connection

### URL
```
ws://localhost:8000/socket.io/
```

### 连接参数
- `session`: 用户会话ID（必需）
- `roomCode`: 房间代码（可选，加入特定房间时使用）

## Events

### 客户端发送事件

#### `join-room`
加入游戏房间

```json
{
  "roomCode": "ABC12345"
}
```

#### `leave-room`
离开游戏房间

```json
{
  "roomCode": "ABC12345"
}
```

#### `game-action`
执行游戏动作

```json
{
  "roomCode": "ABC12345",
  "action": "move",
  "data": {
    "from": "position1",
    "to": "position2",
    "piece": "type"
  }
}
```

#### `start-spectating`
开始旁观游戏

```json
{
  "roomCode": "ABC12345"
}
```

#### `stop-spectating`
停止旁观游戏

```json
{
  "roomCode": "ABC12345"
}
```

#### `pause-game`
暂停游戏

```json
{
  "roomCode": "ABC12345"
}
```

#### `resume-game`
恢复游戏

```json
{
  "roomCode": "ABC12345"
}
```

### 服务器发送事件

#### `room-joined`
成功加入房间

```json
{
  "roomCode": "ABC12345",
  "participant": {
    "id": "participant-id",
    "sessionId": "session-id",
    "joinedAt": "2025-11-26T10:30:00Z"
  }
}
```

#### `room-left`
成功离开房间

```json
{
  "roomCode": "ABC12345",
  "participantId": "participant-id",
  "timestamp": "2025-11-26T10:30:00Z"
}
```

#### `game-started`
游戏开始

```json
{
  "roomCode": "ABC12345",
  "gameData": {
    "gameType": {
      "name": "棋类游戏",
      "slug": "chess-like"
    },
    "participants": [
      {
        "id": "participant-id",
        "name": "玩家",
        "isAI": false,
        "type": "human"
      },
      {
        "id": "ai-participant-id",
        "name": "AI玩家1",
        "isAI": true,
        "type": "ai",
        "personality": "aggressive"
      }
    ],
    "initialState": {
      "board": "...",
      "currentTurn": "participant-id"
    },
    "startedAt": "2025-11-26T10:30:00Z"
  }
}
```

#### `game-state-updated`
游戏状态更新

```json
{
  "roomCode": "ABC12345",
  "turnNumber": 5,
  "currentTurn": "participant-id",
  "gameState": {
    "board": "...",
    "pieces": "...",
    "scores": {
      "participant-id": 10,
      "ai-participant-id": 8
    }
  },
  "timestamp": "2025-11-26T10:35:00Z"
}
```

#### `ai-action`
AI执行动作

```json
{
  "roomCode": "ABC12345",
  "aiParticipantId": "ai-participant-id",
  "action": {
    "type": "move",
    "data": {
      "from": "position1",
      "to": "position2",
      "piece": "type",
      "reasoning": "进攻性策略"
    },
    "thinkingTime": 2.5
  },
  "timestamp": "2025-11-26T10:36:00Z"
}
```

#### `action-result`
动作执行结果

```json
{
  "roomCode": "ABC12345",
  "participantId": "participant-id",
  "action": {
    "type": "move",
    "data": {
      "from": "position1",
      "to": "position2",
      "piece": "type"
    }
  },
  "result": {
    "success": true,
    "gameState": {
      "board": "...",
      "scores": {
        "participant-id": 15,
        "ai-participant-id": 8
      }
    },
    "nextTurn": "ai-participant-id"
  },
  "timestamp": "2025-11-26T10:37:00Z"
}
```

#### `game-completed`
游戏结束

```json
{
  "roomCode": "ABC12345",
  "result": {
    "winner": "participant-id",
    "userWon": true,
    "finalScore": 25,
    "reason": "达成胜利条件"
  },
  "finalState": {
    "board": "...",
    "statistics": {
      "totalMoves": 12,
      "userMoves": 6,
      "aiMoves": 6,
      "gameDuration": 480
    }
  },
  "completedAt": "2025-11-26T10:45:00Z"
}
```

#### `game-paused`
游戏暂停

```json
{
  "roomCode": "ABC12345",
  "pausedAt": "2025-11-26T10:40:00Z",
  "reason": "user_requested"
}
```

#### `game-resumed`
游戏恢复

```json
{
  "roomCode": "ABC12345",
  "resumedAt": "2025-11-26T10:42:00Z",
  "currentTurn": "participant-id"
}
```

#### `ai-agent-added`
AI代理添加到房间

```json
{
  "roomCode": "ABC12345",
  "aiAgent": {
    "id": "ai-agent-id",
    "username": "AI玩家2",
    "personality": "defensive",
    "difficulty": 3,
    "addedAt": "2025-11-26T10:25:00Z"
  }
}
```

#### `ai-agent-removed`
AI代理从房间移除

```json
{
  "roomCode": "ABC12345",
  "aiAgentId": "ai-agent-id",
  "removedAt": "2025-11-26T10:28:00Z",
  "reason": "user_requested"
}
```

#### `error`
错误事件

```json
{
  "roomCode": "ABC12345",
  "error": {
    "code": "INVALID_ACTION",
    "message": "无效的游戏动作",
    "details": {
      "action": "move",
      "reason": "目标位置无效"
    }
  },
  "timestamp": "2025-11-26T10:35:00Z"
}
```

#### `connection-status`
连接状态更新

```json
{
  "status": "connected",
  "timestamp": "2025-11-26T10:30:00Z"
}
```

```json
{
  "status": "disconnected",
  "reason": "server_shutdown",
  "timestamp": "2025-11-26T10:30:00Z"
}
```

## 错误处理

### 常见错误代码

| 错误代码 | 描述 | 处理建议 |
|---------|------|----------|
| `INVALID_ACTION` | 无效的游戏动作 | 显示错误信息，阻止动作执行 |
| `NOT_YOUR_TURN` | 不是当前玩家回合 | 等待自己的回合 |
| `GAME_NOT_STARTED` | 游戏未开始 | 提示先开始游戏 |
| `GAME_ALREADY_ENDED` | 游戏已结束 | 查看结果，开始新游戏 |
| `ROOM_FULL` | 房间已满 | 移除AI代理或创建新房间 |
| `NOT_IN_ROOM` | 不在房间中 | 先加入房间 |
| `AI_ERROR` | AI执行错误 | 重试或替换AI代理 |
| `CONNECTION_LOST` | 连接丢失 | 重新连接并恢复状态 |

### 连接恢复

当连接丢失时，客户端应：

1. 尝试重新连接（最多3次，指数退避）
2. 重新连接成功后，重新发送join-room事件
3. 请求当前游戏状态以同步
4. 如果游戏正在进行中，继续游戏

## 房间命名空间

所有事件都在特定的房间命名空间内发送，格式为`room:{roomCode}`。客户端连接后需要加入相应房间的命名空间才能接收该房间的事件。

## 性能考虑

1. **消息大小限制**: 单条消息不超过64KB
2. **频率限制**: 每秒最多发送10条消息
3. **批处理**: 游戏状态更新可以批量发送
4. **压缩**: 大型游戏状态使用压缩传输

## 安全考虑

1. **会话验证**: 所有事件都包含会话ID验证
2. **房间权限**: 只能发送已加入房间的事件
3. **动作验证**: 游戏动作必须符合游戏规则
4. **频率限制**: 防止消息洪水攻击

## 测试场景

### 基本游戏流程
1. 客户端连接并加入房间
2. 客户端添加AI代理
3. 客户端开始游戏
4. 客户端执行动作，接收AI响应
5. 游戏结束，接收结果

### 错误处理
1. 客户端在非自己回合执行动作
2. 客户端发送无效动作
3. 连接丢失和恢复
4. AI代理执行失败

### 旁观模式
1. 客户端开始旁观AI对战
2. 接收游戏状态更新和AI决策
3. 停止旁观

这些WebSocket事件设计确保了实时游戏体验，同时保持了简单和可维护性。