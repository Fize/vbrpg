# 快速入门指南

**分支**: 001-backend-refactor  
**日期**: 2025-11-26  
**目的**: 单用户游戏平台后端服务的快速入门

## 概述

本指南介绍如何快速设置和使用简化后的单用户游戏平台后端服务。该服务专注于单用户与AI对手的游戏体验，移除了多用户相关功能，提供更轻量级的架构。

## 系统要求

- Python 3.11+
- SQLite (内置)
- 2GB可用内存
- 1GB可用磁盘空间

## 安装与设置

### 1. 克隆仓库并切换分支

```bash
git clone <repository-url>
cd vbrpg
git checkout 001-backend-refactor
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 初始化数据库

```bash
python -m alembic upgrade head
```

### 5. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动。

## 基本使用流程

### 1. 创建会话

```bash
curl -X POST "http://localhost:8000/api/v1/sessions" \
  -H "Content-Type: application/json"
```

响应：
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "sess_abc123def456",
  "created_at": "2025-11-26T10:30:00Z",
  "last_active": "2025-11-26T10:30:00Z",
  "expires_at": "2025-11-27T10:30:00Z"
}
```

### 2. 创建游戏房间

```bash
curl -X POST "http://localhost:8000/api/v1/rooms" \
  -H "Content-Type: application/json" \
  -d '{
    "game_type_slug": "chess-like",
    "max_players": 4,
    "min_players": 2
  }'
```

响应：
```json
{
  "id": "room_id_123",
  "code": "ABC12345",
  "status": "Waiting",
  "max_players": 4,
  "min_players": 2,
  "current_player_count": 0,
  "game_type": {
    "id": "game_type_id",
    "name": "棋类游戏",
    "slug": "chess-like"
  },
  "created_at": "2025-11-26T10:31:00Z",
  "started_at": null,
  "completed_at": null,
  "participants": []
}
```

### 3. 加入房间

```bash
curl -X POST "http://localhost:8000/api/v1/rooms/ABC12345/join"
```

### 4. 添加AI对手

```bash
curl -X POST "http://localhost:8000/api/v1/rooms/ABC12345/ai-agents" \
  -H "Content-Type: application/json" \
  -d '{
    "personality_type": "aggressive",
    "difficulty_level": 3
  }'
```

### 5. 开始游戏

```bash
curl -X POST "http://localhost:8000/api/v1/rooms/ABC12345/start"
```

## WebSocket 交互

### 连接WebSocket

```javascript
import io from 'socket.io-client';

const socket = io('http://localhost:8000', {
  query: {
    session: 'sess_abc123def456'
  }
});

socket.on('connect', () => {
  console.log('Connected to server');
  
  // 加入房间
  socket.emit('join-room', {
    roomCode: 'ABC12345'
  });
});
```

### 接收游戏事件

```javascript
// 游戏开始事件
socket.on('game-started', (data) => {
  console.log('Game started:', data);
  // 初始化游戏UI
});

// 游戏状态更新
socket.on('game-state-updated', (data) => {
  console.log('Game state updated:', data);
  // 更新游戏UI
});

// AI动作
socket.on('ai-action', (data) => {
  console.log('AI made a move:', data);
  // 显示AI动作
});

// 游戏结束
socket.on('game-completed', (data) => {
  console.log('Game completed:', data);
  // 显示游戏结果
});
```

### 执行游戏动作

```javascript
function makeMove(from, to, piece) {
  socket.emit('game-action', {
    roomCode: 'ABC12345',
    action: 'move',
    data: {
      from: from,
      to: to,
      piece: piece
    }
  });
}
```

## 旁观模式

### 创建AI对战房间

```bash
curl -X POST "http://localhost:8000/api/v1/rooms/ABC12345/watch" \
  -H "Content-Type: application/json" \
  -d '{
    "game_type_slug": "chess-like",
    "ai_count": 2,
    "ai_personalities": ["aggressive", "defensive"],
    "ai_difficulties": [3, 3]
  }'
```

### 作为旁观者观看

```javascript
// 开始旁观
socket.emit('start-spectating', {
  roomCode: 'ABC12345'
});

// 接收游戏事件（与正常游戏相同）
socket.on('game-started', (data) => {
  console.log('AI game started:', data);
});

socket.on('ai-action', (data) => {
  console.log('AI made a move:', data);
  // 显示AI决策和思考过程
});

// 停止旁观
socket.emit('stop-spectating', {
  roomCode: 'ABC12345'
});
```

## 获取游戏历史

```bash
curl "http://localhost:8000/api/v1/sessions/sess_abc123def456/history?limit=10"
```

响应：
```json
[
  {
    "id": "session_id_1",
    "game_type": {
      "name": "棋类游戏",
      "slug": "chess-like"
    },
    "started_at": "2025-11-26T10:30:00Z",
    "completed_at": "2025-11-26T10:45:00Z",
    "duration_minutes": 15,
    "user_won": true,
    "final_score": 25,
    "participants_count": 2,
    "ai_agents_count": 1
  },
  {
    "id": "session_id_2",
    "game_type": {
      "name": "策略游戏",
      "slug": "strategy-game"
    },
    "started_at": "2025-11-25T14:20:00Z",
    "completed_at": "2025-11-25T14:50:00Z",
    "duration_minutes": 30,
    "user_won": false,
    "final_score": 18,
    "participants_count": 3,
    "ai_agents_count": 2
  }
]
```

## 常见问题

### Q: 如何重置所有数据？

A: 删除数据库文件并重新运行迁移：

```bash
rm game.db
python -m alembic upgrade head
```

### Q: 如何更改AI难度？

A: 在添加AI代理时指定不同的难度等级（1-5）：

```bash
curl -X POST "http://localhost:8000/api/v1/rooms/ABC12345/ai-agents" \
  -H "Content-Type: application/json" \
  -d '{
    "personality_type": "balanced",
    "difficulty_level": 5
  }'
```

### Q: 如何处理连接丢失？

A: 实现自动重连逻辑：

```javascript
socket.on('disconnect', () => {
  console.log('Disconnected from server');
  
  // 指数退避重连
  const retryDelay = Math.min(1000 * Math.pow(2, attemptCount), 30000);
  setTimeout(connect, retryDelay);
});

function connect() {
  socket.connect();
}
```

### Q: 如何暂停和恢复游戏？

A: 使用WebSocket事件：

```javascript
// 暂停游戏
socket.emit('pause-game', {
  roomCode: 'ABC12345'
});

// 恢复游戏
socket.emit('resume-game', {
  roomCode: 'ABC12345'
});
```

## 性能优化提示

1. **批量处理**: 对于频繁的游戏状态更新，考虑批量发送
2. **压缩**: 启用WebSocket消息压缩以减少带宽
3. **缓存**: 缓存游戏类型和其他不变数据
4. **清理**: 定期清理超过30天的游戏历史

## API文档

完整的API文档可在以下地址查看：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 故障排除

### 服务无法启动

检查端口是否被占用，或尝试使用不同端口：

```bash
python main.py --port 8001
```

### 数据库错误

确保数据库文件权限正确，或重新创建数据库：

```bash
chmod 664 game.db
# 或
python -m alembic downgrade base && python -m alembic upgrade head
```

### WebSocket连接问题

确保客户端和服务器使用相同版本的Socket.IO库，并检查防火墙设置。

## 下一步

1. 尝试不同类型的游戏和AI配置
2. 实现自己的AI个性类型
3. 扩展游戏历史分析功能
4. 探索前端集成的最佳实践

如有更多问题，请参考项目的完整文档或提交issue。