# 狼人杀游戏交互增强 - 技术设计文档

## 1. 设计概述

### 1.1 设计目标

基于现有的狼人杀游戏架构，增强游戏交互功能，实现：
1. 游戏手动开始控制
2. 游戏暂停/继续功能
3. 实时游戏日志（含日志级别切换）
4. 玩家发言输入与 AI 交互
5. AI 发言气泡实时显示

### 1.2 技术栈

严格使用项目现有技术栈：
- **后端**: FastAPI + python-socketio + SQLAlchemy
- **前端**: Vue 3 + Pinia + Element Plus + Socket.IO Client
- **通信**: WebSocket (Socket.IO) 实时双向通信

### 1.3 设计原则

- 复用现有组件和服务，不重复造轮子
- 保持与现有代码风格一致
- 最小化改动范围，专注于需求功能

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Vue 3)                         │
├─────────────────────────────────────────────────────────────────┤
│  WerewolfGameView.vue                                           │
│  ├── GameControlBar (新增)     - 开始/暂停/继续按钮              │
│  ├── SeatCircle.vue           - 座位圈 + AI发言气泡(增强)        │
│  │   └── PlayerSeat.vue       - 玩家座位 + 气泡组件(增强)        │
│  ├── GameLog.vue (增强)       - 日志显示 + 级别切换              │
│  └── PlayerInputBar (新增)    - 玩家发言输入框                   │
├─────────────────────────────────────────────────────────────────┤
│  Stores (Pinia)                                                  │
│  ├── game.js (增强)           - 游戏状态 + 暂停状态 + 发言状态    │
│  └── socket.js (增强)         - WebSocket 事件处理               │
└───────────────────────────────┬─────────────────────────────────┘
                                │ WebSocket (Socket.IO)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Backend (FastAPI)                        │
├─────────────────────────────────────────────────────────────────┤
│  API Routes                                                      │
│  └── werewolf_routes.py (增强) - 开始/暂停/继续/发言 API         │
├─────────────────────────────────────────────────────────────────┤
│  WebSocket Handlers                                              │
│  └── werewolf_handlers.py (增强) - 游戏控制 + 玩家发言事件        │
├─────────────────────────────────────────────────────────────────┤
│  Services                                                        │
│  └── werewolf_game_service.py (增强)                             │
│      ├── 游戏暂停/继续逻辑                                       │
│      ├── 玩家发言处理 + 上下文构建                               │
│      └── AI 发言流式输出                                         │
├─────────────────────────────────────────────────────────────────┤
│  AI Agents                                                       │
│  └── 各角色 Agent (现有)      - 接收玩家发言作为上下文           │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流设计

#### 2.2.1 游戏开始流程

```
用户点击"开始游戏"
    │
    ▼
Frontend: emit('werewolf:start_game', { room_code })
    │
    ▼
Backend: werewolf_handlers.py 接收事件
    │
    ▼
WerewolfGameService.start_game()
    │
    ├── 初始化游戏状态
    ├── 创建 AI Agents
    ├── 广播 game_started 事件
    └── 开始第一个夜晚
    │
    ▼
Frontend: 接收 werewolf:game_started, 更新 UI
```

#### 2.2.2 暂停/继续流程

```
用户点击"暂停"
    │
    ▼
Frontend: emit('werewolf:pause_game', { room_code })
    │
    ▼
Backend: 
    ├── 设置 is_paused = True
    ├── 等待当前行动完成
    └── 广播 werewolf:game_paused
    │
    ▼
Frontend: 
    ├── 更新 isPaused 状态
    └── 显示暂停遮罩

用户点击"继续"
    │
    ▼
Frontend: emit('werewolf:resume_game', { room_code })
    │
    ▼
Backend: 
    ├── 设置 is_paused = False
    ├── 继续游戏流程
    └── 广播 werewolf:game_resumed
```

#### 2.2.3 玩家发言流程

```
主持人要求玩家发言
    │
    ▼
Backend: emit('werewolf:request_speech', { player_id, seat_number })
    │
    ▼
Frontend: 
    ├── 启用输入框
    ├── 显示"请发言"提示
    └── 启动提醒计时器
    │
用户输入发言内容，点击发送
    │
    ▼
Frontend: emit('werewolf:player_speech', { room_code, content })
    │
    ▼
Backend: WerewolfGameService.process_player_speech()
    ├── 记录发言到 game_log
    ├── 广播 werewolf:speech_end (完整发言)
    ├── 更新 AI Agents 的上下文
    └── 继续游戏流程（下一位发言或投票）
    │
    ▼
Frontend: 
    ├── 禁用输入框
    ├── 在日志显示玩家发言
    └── 在玩家座位显示发言气泡
```

#### 2.2.4 AI 发言流程（含气泡显示）

```
轮到 AI 发言
    │
    ▼
Backend: WerewolfGameService._execute_speeches()
    │
    ├── emit('werewolf:speech_start', { speaker_seat, speaker_name })
    │   │
    │   ▼ Frontend: 
    │       ├── 设置 speakingPlayerId
    │       ├── 在 PlayerSeat 显示气泡（空内容）
    │       └── 在 GameLog 添加流式日志
    │
    ├── AI Agent 生成发言（流式）
    │   │
    │   └── 循环 emit('werewolf:speech_chunk', { speaker_seat, chunk, accumulated })
    │       │
    │       ▼ Frontend:
    │           ├── 更新气泡内容（打字机效果）
    │           └── 更新日志内容
    │
    └── emit('werewolf:speech_end', { speaker_seat, content })
        │
        ▼ Frontend:
            ├── 完成气泡显示
            ├── 启动 5 秒消失计时器
            └── 完成日志记录
```

## 3. 接口设计

### 3.1 WebSocket 事件（新增/增强）

#### 3.1.1 客户端 → 服务端

| 事件名 | 数据结构 | 说明 |
|--------|----------|------|
| `werewolf:start_game` | `{ room_code: string }` | 开始游戏 |
| `werewolf:pause_game` | `{ room_code: string }` | 暂停游戏 |
| `werewolf:resume_game` | `{ room_code: string }` | 继续游戏 |
| `werewolf:player_speech` | `{ room_code: string, content: string }` | 玩家发言 |

#### 3.1.2 服务端 → 客户端

| 事件名 | 数据结构 | 说明 |
|--------|----------|------|
| `werewolf:game_started` | `{ room_code, phase, day_number, players }` | 游戏开始 |
| `werewolf:game_paused` | `{ room_code }` | 游戏已暂停 |
| `werewolf:game_resumed` | `{ room_code }` | 游戏已继续 |
| `werewolf:request_speech` | `{ player_id, seat_number, timeout?: number }` | 请求玩家发言 |
| `werewolf:speech_reminder` | `{ seat_number, message }` | 发言提醒 |
| `werewolf:speech_chunk` | `{ speaker_seat, chunk, accumulated }` | 发言片段（增强：含累积内容） |

### 3.2 REST API（增强）

#### POST /api/v1/werewolf/rooms/{room_code}/start

启动游戏（备用方案，主要使用 WebSocket）

**Request Body:**
```json
{
  "player_id": "string"
}
```

**Response:**
```json
{
  "success": true,
  "message": "游戏已开始"
}
```

#### POST /api/v1/werewolf/rooms/{room_code}/pause

暂停游戏

**Request Body:**
```json
{
  "player_id": "string"
}
```

#### POST /api/v1/werewolf/rooms/{room_code}/resume

继续游戏

#### POST /api/v1/werewolf/rooms/{room_code}/speech

玩家发言

**Request Body:**
```json
{
  "player_id": "string",
  "content": "string"
}
```

#### GET /api/v1/werewolf/rooms/{room_code}/logs

获取游戏日志（用于断线重连恢复）

**Query Params:**
- `level`: `basic` | `detailed` (默认 basic)

**Response:**
```json
{
  "logs": [
    {
      "id": "string",
      "type": "speech | host_announcement | death | vote | ...",
      "player_id": "string?",
      "player_name": "string?",
      "content": "string",
      "day": 1,
      "phase": "night | day",
      "time": "ISO8601"
    }
  ]
}
```

## 4. 数据模型设计

### 4.1 游戏状态扩展 (WerewolfGameState)

```python
@dataclass
class WerewolfGameState:
    # 现有字段...
    
    # 新增字段
    is_paused: bool = False                    # 是否暂停
    is_started: bool = False                   # 是否已开始
    current_speaker_seat: int | None = None    # 当前发言者座位
    waiting_for_player_input: bool = False     # 是否等待玩家输入
    speech_reminder_count: int = 0             # 发言提醒次数
    game_logs: list[GameLogEntry] = field(default_factory=list)  # 完整日志
```

### 4.2 游戏日志条目 (GameLogEntry)

```python
@dataclass
class GameLogEntry:
    id: str
    type: str                    # speech, host_announcement, death, vote, skill, etc.
    content: str
    day: int
    phase: str
    time: datetime
    player_id: str | None = None
    player_name: str | None = None
    seat_number: int | None = None
    metadata: dict | None = None  # 额外信息（如投票结果、死亡原因等）
    is_public: bool = True       # 是否公开（用于日志级别过滤）
```

### 4.3 前端状态扩展 (game.js store)

```javascript
// 新增状态
const isStarted = ref(false)           // 游戏是否已开始
const isPaused = ref(false)            // 游戏是否暂停
const canSpeak = ref(false)            // 当前是否可以发言
const speechReminderVisible = ref(false) // 发言提醒是否可见
const logLevel = ref('basic')          // 日志级别: 'basic' | 'detailed'

// AI 发言气泡状态
const activeSpeechBubbles = ref({})    // { [seatNumber]: { content, isStreaming, timer } }
```

## 5. 组件设计

### 5.1 GameControlBar 组件（新增）

**文件**: `frontend/src/components/werewolf/GameControlBar.vue`

**功能**:
- 显示"开始游戏"按钮（游戏未开始时）
- 显示"暂停"/"继续"按钮（游戏进行中）
- 显示暂停状态指示

**Props**:
```typescript
{
  isStarted: boolean
  isPaused: boolean
  isSpectator: boolean
  disabled: boolean
}
```

**Events**:
```typescript
{
  start: () => void
  pause: () => void
  resume: () => void
}
```

### 5.2 PlayerInputBar 组件（新增）

**文件**: `frontend/src/components/werewolf/PlayerInputBar.vue`

**功能**:
- 发言输入框
- 发送按钮
- 禁用状态显示（"等待发言时机"）
- 发言提醒动画

**Props**:
```typescript
{
  disabled: boolean
  placeholder: string
  reminderVisible: boolean
}
```

**Events**:
```typescript
{
  submit: (content: string) => void
}
```

### 5.3 SpeechBubble 组件（新增）

**文件**: `frontend/src/components/werewolf/SpeechBubble.vue`

**功能**:
- 显示发言气泡
- 支持流式内容（打字机效果）
- 自动消失动画

**Props**:
```typescript
{
  content: string
  isStreaming: boolean
  position: 'top' | 'bottom' | 'left' | 'right'
  autoHide: boolean
  hideDelay: number  // 默认 5000ms
}
```

### 5.4 GameLog 组件增强

**增强内容**:
- 添加日志级别切换开关
- 支持基础/详细两种级别
- 详细级别显示 AI 思考过程

**新增 Props**:
```typescript
{
  logLevel: 'basic' | 'detailed'
}
```

**新增 Events**:
```typescript
{
  'update:logLevel': (level: string) => void
}
```

### 5.5 PlayerSeat 组件增强

**增强内容**:
- 集成 SpeechBubble 组件
- 显示 AI 发言气泡

**新增 Props**:
```typescript
{
  speechBubble: {
    content: string
    isStreaming: boolean
    visible: boolean
  } | null
}
```

## 6. 后端服务设计

### 6.1 WerewolfGameService 增强

#### 6.1.1 游戏控制方法

```python
async def start_game_manual(self, room_code: str) -> bool:
    """手动开始游戏（由用户触发）"""
    pass

async def pause_game(self, room_code: str) -> bool:
    """暂停游戏，等待当前行动完成"""
    pass

async def resume_game(self, room_code: str) -> bool:
    """继续游戏"""
    pass
```

#### 6.1.2 玩家发言处理

```python
async def process_player_speech(
    self, 
    room_code: str, 
    player_id: str, 
    content: str
) -> None:
    """
    处理玩家发言：
    1. 验证是否轮到该玩家发言
    2. 记录发言到日志
    3. 更新所有 AI Agent 的上下文
    4. 广播发言
    5. 继续游戏流程
    """
    pass

async def _request_player_speech(
    self, 
    room_code: str, 
    player_seat: int
) -> None:
    """请求玩家发言，并启动提醒机制"""
    pass

async def _send_speech_reminder(
    self, 
    room_code: str, 
    player_seat: int
) -> None:
    """发送发言提醒"""
    pass
```

#### 6.1.3 AI 上下文构建

```python
def _build_ai_context(
    self, 
    game_state: WerewolfGameState,
    agent_seat: int
) -> dict:
    """
    为 AI Agent 构建上下文，包括：
    - 游戏历史日志
    - 当天所有公开发言
    - 玩家发言（作为上下文输入）
    - 存活玩家信息
    """
    pass
```

### 6.2 WebSocket Handlers 增强

**文件**: `backend/src/websocket/werewolf_handlers.py`

新增事件处理器：

```python
@sio.event
async def werewolf_start_game(sid: str, data: dict):
    """处理开始游戏事件"""
    pass

@sio.event
async def werewolf_pause_game(sid: str, data: dict):
    """处理暂停游戏事件"""
    pass

@sio.event
async def werewolf_resume_game(sid: str, data: dict):
    """处理继续游戏事件"""
    pass

@sio.event
async def werewolf_player_speech(sid: str, data: dict):
    """处理玩家发言事件"""
    pass
```

### 6.3 AI Agent 上下文增强

在各 AI Agent（WerewolfAgent, SeerAgent, VillagerAgent 等）中增强：

```python
def update_context(self, speeches: list[dict]) -> None:
    """更新对话上下文，包含玩家发言"""
    pass

async def generate_speech_stream(
    self,
    game_history: list[str],
    alive_players: list[int],
    day_number: int,
    player_speeches: list[dict]  # 新增：包含玩家发言
) -> AsyncGenerator[str, None]:
    """生成发言（流式），考虑玩家发言作为上下文"""
    pass
```

## 7. 实现任务清单

### 7.1 后端任务

| # | 任务 | 文件 | 优先级 |
|---|------|------|--------|
| B1 | 增加游戏状态字段 (is_paused, is_started 等) | `werewolf_engine.py` | P0 |
| B2 | 实现 start_game_manual 方法 | `werewolf_game_service.py` | P0 |
| B3 | 实现 pause_game/resume_game 方法 | `werewolf_game_service.py` | P0 |
| B4 | 实现玩家发言处理和上下文构建 | `werewolf_game_service.py` | P0 |
| B5 | 增强 AI speech_chunk 事件（含累积内容） | `werewolf_handlers.py` | P0 |
| B6 | 新增 WebSocket 事件处理器 | `werewolf_handlers.py` | P0 |
| B7 | 新增日志获取 API（断线重连） | `werewolf_routes.py` | P0 |
| B8 | 实现发言提醒机制 | `werewolf_game_service.py` | P1 |

### 7.2 前端任务

| # | 任务 | 文件 | 优先级 |
|---|------|------|--------|
| F1 | 创建 GameControlBar 组件 | `components/werewolf/GameControlBar.vue` | P0 |
| F2 | 创建 PlayerInputBar 组件 | `components/werewolf/PlayerInputBar.vue` | P0 |
| F3 | 创建 SpeechBubble 组件 | `components/werewolf/SpeechBubble.vue` | P0 |
| F4 | 增强 GameLog 组件（日志级别切换） | `components/werewolf/GameLog.vue` | P0 |
| F5 | 增强 PlayerSeat 组件（集成气泡） | `components/werewolf/PlayerSeat.vue` | P0 |
| F6 | 更新 WerewolfGameView（集成新组件） | `views/WerewolfGameView.vue` | P0 |
| F7 | 增强 game store（新状态和方法） | `stores/game.js` | P0 |
| F8 | 增强 socket store（新事件处理） | `stores/socket.js` | P0 |
| F9 | 实现断线重连日志恢复 | `views/WerewolfGameView.vue` | P0 |
| F10 | 实现发言提醒动画 | `components/werewolf/PlayerInputBar.vue` | P1 |

## 8. 关键实现细节

### 8.1 暂停机制实现

```python
# werewolf_game_service.py

async def pause_game(self, room_code: str) -> bool:
    """暂停游戏"""
    game_state = self._game_states.get(room_code)
    if not game_state or game_state.is_paused:
        return False
    
    # 标记暂停（当前行动完成后生效）
    game_state.is_paused = True
    
    # 广播暂停事件
    await sio.emit('werewolf:game_paused', {'room_code': room_code}, room=room_code)
    
    return True

async def _check_paused_before_next_action(self, room_code: str) -> bool:
    """在执行下一个行动前检查是否暂停"""
    game_state = self._game_states.get(room_code)
    if game_state and game_state.is_paused:
        # 等待继续信号
        while game_state.is_paused:
            await asyncio.sleep(0.5)
    return True
```

### 8.2 玩家发言与 AI 上下文

```python
# werewolf_game_service.py

async def _execute_speeches_with_player(self, room_code: str):
    """执行发言流程（含玩家发言）"""
    game_state = self._game_states.get(room_code)
    alive_players = sorted(
        [p for p in game_state.players.values() if p.is_alive],
        key=lambda p: p.seat_number
    )
    
    # 收集当轮发言作为 AI 上下文
    current_round_speeches = []
    
    for player in alive_players:
        await self._check_paused_before_next_action(room_code)
        
        if player.seat_number in self._ai_agents:
            # AI 发言
            agent = self._ai_agents[player.seat_number]
            speech_content = await self._execute_ai_speech_streaming(
                room_code, player, agent, current_round_speeches
            )
            current_round_speeches.append({
                'seat': player.seat_number,
                'content': speech_content,
                'is_ai': True
            })
        else:
            # 人类玩家发言
            speech_content = await self._wait_for_player_speech(room_code, player)
            current_round_speeches.append({
                'seat': player.seat_number,
                'content': speech_content,
                'is_ai': False
            })
```

### 8.3 AI 发言气泡前端实现

```vue
<!-- PlayerSeat.vue 增强 -->
<template>
  <div class="cyber-player-seat" ...>
    <!-- 现有内容 -->
    
    <!-- 发言气泡 -->
    <SpeechBubble
      v-if="speechBubble?.visible"
      :content="speechBubble.content"
      :is-streaming="speechBubble.isStreaming"
      :position="bubblePosition"
      :auto-hide="!speechBubble.isStreaming"
      :hide-delay="5000"
      @hidden="$emit('bubble-hidden')"
    />
  </div>
</template>
```

```vue
<!-- SpeechBubble.vue -->
<template>
  <Transition name="bubble">
    <div 
      v-show="visible"
      class="speech-bubble"
      :class="[`position-${position}`]"
    >
      <div class="bubble-content">
        <span class="bubble-text">{{ content }}</span>
        <span v-if="isStreaming" class="typing-cursor">|</span>
      </div>
      <div class="bubble-arrow"></div>
    </div>
  </Transition>
</template>
```

### 8.4 日志级别切换

```vue
<!-- GameLog.vue 增强 -->
<template>
  <div class="game-log">
    <div class="log-header">
      <h3 class="log-title">游戏日志</h3>
      <div class="log-controls">
        <el-switch
          v-model="isDetailedMode"
          active-text="详细"
          inactive-text="基础"
          size="small"
          @change="handleLevelChange"
        />
        <!-- 其他控制 -->
      </div>
    </div>
    
    <div class="log-content">
      <template v-for="entry in filteredLogs" :key="entry.id">
        <!-- 根据日志类型渲染 -->
      </template>
    </div>
  </div>
</template>

<script setup>
const filteredLogs = computed(() => {
  if (props.logLevel === 'basic') {
    return props.logs.filter(log => log.is_public !== false)
  }
  return props.logs
})
</script>
```

## 9. 测试计划

### 9.1 单元测试

| 测试项 | 文件 | 说明 |
|--------|------|------|
| 游戏开始控制 | `tests/unit/test_werewolf_game_control.py` | 测试开始游戏逻辑 |
| 暂停/继续逻辑 | `tests/unit/test_werewolf_pause.py` | 测试暂停状态管理 |
| 玩家发言处理 | `tests/unit/test_player_speech.py` | 测试发言验证和广播 |
| AI 上下文构建 | `tests/unit/test_ai_context.py` | 测试上下文包含玩家发言 |

### 9.2 集成测试

| 测试项 | 文件 | 说明 |
|--------|------|------|
| 完整游戏流程 | `tests/integration/test_werewolf_full_game.py` | 含开始、暂停、发言的完整流程 |
| WebSocket 事件 | `tests/integration/test_werewolf_ws_events.py` | 测试所有新增 WebSocket 事件 |

### 9.3 前端测试

| 测试项 | 文件 | 说明 |
|--------|------|------|
| GameControlBar | `tests/unit/components/GameControlBar.spec.js` | 按钮状态和事件 |
| PlayerInputBar | `tests/unit/components/PlayerInputBar.spec.js` | 输入和禁用状态 |
| SpeechBubble | `tests/unit/components/SpeechBubble.spec.js` | 气泡显示和动画 |
| GameLog 增强 | `tests/unit/components/GameLog.spec.js` | 日志级别切换 |

## 10. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 暂停时机不准确 | 用户体验差 | 使用异步锁确保当前行动完成后再暂停 |
| 发言气泡遮挡界面 | 信息展示问题 | 使用智能定位，根据座位位置选择气泡方向 |
| 断线重连丢失日志 | 玩家错过重要信息 | 实现日志 API，重连时拉取历史日志 |
| AI 上下文过长 | LLM 调用超时 | 限制上下文长度，只保留当天发言 |
