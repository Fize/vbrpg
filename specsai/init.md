# VBRPG - 单人桌游平台

## 核心功能模块

### 1. AI 代理系统
- 提供 AI 对手功能，支持多种 AI 性格类型（分析型侦探、直觉型调查员、谨慎观察者、冒险家、策略思考者、共情倾听者）
- 基于 LangChain + OpenAI 实现智能决策，可根据游戏状态生成合理行动
- 支持断线重连时自动 AI 替补，断线超过 5 分钟后由 AI 接管玩家位置
- 与游戏引擎集成，参与回合制游戏流程

### 2. 实时多人通信
- 基于 Socket.IO 的 WebSocket 双向通信
- 支持房间大厅订阅、游戏内事件广播、玩家状态同步
- 断线重连机制：5 分钟宽限期，自动恢复游戏状态
- 玩家连接状态追踪与通知（断线/重连事件广播）

### 3. 游戏引擎（多游戏支持）
- **犯罪现场**：推理解谜游戏，Setup → Investigation → Accusation → Resolution 四阶段
  - 支持证据卡牌系统、嫌疑人/武器/地点推理
  - 回合制行动管理：抽卡、调查地点、揭示线索、提出指控
- **狼人杀**：社交推理游戏，村民与狼人的智慧较量
  - 角色系统：村民、狼人、预言家、女巫、猎人
  - 昼夜轮换机制：白天投票、夜晚行动
- 胜负条件判定与游戏结算

### 4. 房间与会话管理
- 房间创建/加入/离开，支持房间码机制（8 位字母数字）
- 参与者管理：人类玩家 + AI 代理混合
- 房间状态机：Waiting → In Progress → Completed
- 单人模式支持：观众模式和角色选择

### 5. 前端用户界面
- Vue 3 + Element Plus 响应式界面
- Pinia 状态管理：游戏状态、认证状态、大厅状态、Socket 状态
- 游戏大厅、房间配置、游戏面板等完整视图
- 狼人杀专用组件：座位圈、角色卡、投票面板、夜间行动面板
- 断线重连反馈组件、AI 思考状态指示器

## 项目结构分析

### 入口文件
- `backend/main.py` - FastAPI 应用入口，配置中间件和路由
- `frontend/src/main.js` - Vue 应用入口，挂载插件和路由
- `docker-compose.yml` - 容器编排配置

### 核心业务包
- `backend/src/services/` - 业务服务层（游戏房间、游戏状态、AI 代理、玩家服务）
- `backend/src/models/` - SQLAlchemy 数据模型（game.py, user.py）
- `backend/src/constants/` - 静态配置数据（game_types.py 游戏类型定义, roles.py 角色定义）
- `backend/src/api/` - RESTful API 路由端点

### 基础设施包
- `backend/src/utils/` - 工具函数（配置、错误处理、输入处理、速率限制、日志配置）
- `backend/src/websocket/` - WebSocket 服务器和事件处理器
- `backend/src/integrations/` - 外部服务集成（LLM 客户端）

### 代码目录文件结构

```
backend/
├── main.py                          # FastAPI 应用入口
├── pyproject.toml                   # Python 项目配置和依赖
├── alembic.ini                      # 数据库迁移配置
├── alembic/
│   ├── env.py                       # Alembic 环境配置
│   └── versions/                    # 数据库迁移脚本
└── src/
    ├── __init__.py
    ├── database.py                  # 数据库连接和会话管理
    ├── api/
    │   ├── __init__.py
    │   ├── game_routes.py           # 游戏和房间 API 路由
    │   ├── user_routes.py           # 玩家和会话 API 路由
    │   ├── werewolf_routes.py       # 狼人杀专用 API 路由
    │   ├── monitoring.py            # 监控和健康检查 API
    │   └── schemas.py               # Pydantic 请求/响应模型
    ├── constants/
    │   ├── __init__.py
    │   ├── game_types.py            # 游戏类型静态定义（犯罪现场、狼人杀等）
    │   └── roles.py                 # 角色静态定义（狼人杀角色等）
    ├── models/
    │   ├── __init__.py              # 模型导出
    │   ├── base.py                  # SQLAlchemy 基类和 Mixin
    │   ├── game.py                  # 游戏相关模型 (GameRoom, GameState, GameSession, etc.)
    │   └── user.py                  # 用户相关模型 (Player, Session, etc.)
    ├── services/
    │   ├── __init__.py
    │   ├── ai_service.py            # AI 代理服务与调度器
    │   ├── game_room_service.py     # 游戏房间管理服务
    │   ├── game_state_service.py    # 游戏状态管理服务
    │   ├── player_service.py        # 玩家管理服务
    │   ├── werewolf_game_service.py # 狼人杀游戏服务（流程控制与状态管理）
    │   ├── ai_agents/               # AI 代理实现目录
    │   │   ├── __init__.py
    │   │   ├── base.py              # AI 代理基类
    │   │   ├── werewolf_agent.py    # 狼人 AI 代理
    │   │   ├── seer_agent.py        # 预言家 AI 代理
    │   │   ├── witch_agent.py       # 女巫 AI 代理
    │   │   ├── hunter_agent.py      # 猎人 AI 代理
    │   │   ├── villager_agent.py    # 村民 AI 代理
    │   │   ├── host/                # 主持人 AI 模块
    │   │   └── prompts/             # AI Prompt 模板
    │   └── games/
    │       ├── __init__.py
    │       ├── crime_scene_engine.py # 犯罪现场游戏引擎
    │       └── werewolf_engine.py    # 狼人杀游戏引擎（规则与状态机）
    ├── utils/
    │   ├── __init__.py
    │   ├── ai_logger.py             # AI 专用日志工具
    │   ├── config.py                # 应用配置和中间件
    │   ├── errors.py                # 自定义异常类层次
    │   ├── helpers.py               # 房间码和用户名生成工具
    │   ├── input_processing.py      # 输入清理和验证
    │   ├── logging_config.py        # 日志配置
    │   ├── rate_limiter.py          # API 速率限制器
    │   └── sessions.py              # 会话管理工具
    ├── integrations/
    │   ├── __init__.py
    │   └── llm_client.py            # LangChain/OpenAI LLM 客户端
    └── websocket/
        ├── __init__.py
        ├── server.py                # Socket.IO 服务器实例
        ├── sessions.py              # WebSocket 会话管理
        ├── handlers.py              # 通用 WebSocket 事件处理器
        └── werewolf_handlers.py     # 狼人杀专用 WebSocket 事件处理器

frontend/
├── index.html                       # HTML 入口
├── package.json                     # NPM 依赖和脚本
├── vite.config.js                   # Vite 构建配置
├── vitest.config.js                 # Vitest 测试配置
├── playwright.config.js             # E2E 测试配置
└── src/
    ├── main.js                      # Vue 应用入口
    ├── App.vue                      # 根组件
    ├── router/
    │   └── index.js                 # Vue Router 路由配置
    ├── stores/
    │   ├── index.js                 # Pinia 存储入口
    │   ├── game.js                  # 游戏状态存储
    │   ├── auth.js                  # 认证状态存储
    │   ├── lobby.js                 # 大厅状态存储
    │   └── socket.js                # Socket 连接状态存储
    ├── services/
    │   ├── api.js                   # Axios API 客户端
    │   ├── websocket.js             # Socket.IO 客户端封装
    │   └── analytics.ts             # 分析服务
    ├── views/
    │   ├── LobbyView.vue            # 游戏大厅视图
    │   ├── CreateRoomView.vue       # 创建房间视图
    │   ├── RoomLobbyView.vue        # 房间等待大厅
    │   ├── GameDetails.vue          # 游戏详情视图
    │   └── WerewolfGameView.vue     # 狼人杀游戏视图
    ├── components/
    │   ├── common/                  # 通用组件
    │   │   ├── AppLayout.vue        # 应用布局组件
    │   │   ├── AIThinkingIndicator.vue  # AI 思考状态指示
    │   │   ├── ReconnectionDialog.vue   # 重连对话框
    │   │   ├── ReconnectionFeedback.vue # 重连反馈组件
    │   │   ├── ConnectionStatus.vue     # 连接状态组件
    │   │   ├── ErrorDialog.vue      # 错误对话框
    │   │   ├── ErrorMessage.vue     # 错误信息组件
    │   │   ├── EmptyState.vue       # 空状态组件
    │   │   └── LoadingIndicator.vue # 加载指示器
│   │   ├── werewolf/                # 狼人杀专用组件
│   │   │   ├── SeatCircle.vue       # 座位圈组件
│   │   │   ├── PlayerSeat.vue       # 玩家座位组件
│   │   │   ├── RoleCard.vue         # 角色卡组件
│   │   │   ├── RoleSelector.vue     # 角色选择器
│   │   │   ├── VotePanel.vue        # 投票面板
│   │   │   ├── NightActionPanel.vue # 夜间行动面板
│   │   │   ├── PlayerInputPanel.vue # 玩家输入面板
│   │   │   ├── SpeechBubble.vue     # 发言气泡组件
│   │   │   ├── GameLog.vue          # 游戏日志
│   │   │   ├── GameControlBar.vue   # 游戏控制栏
│   │   │   ├── GamePhaseIndicator.vue # 游戏阶段指示器
│   │   │   ├── LogLevelSwitch.vue   # 日志级别切换
│   │   │   ├── HostAnnouncement.vue # 主持人公告组件
│   │   │   ├── HostAnnouncementPanel.vue # 主持人公告面板
│   │   │   ├── WerewolfModeDialog.vue # 狼人杀模式选择对话框
│   │   │   ├── ParticipantList.vue  # 参与者列表
│   │   │   └── WerewolfGameCard.vue # 狼人杀游戏卡片
    │   ├── lobby/                   # 大厅相关组件
    │   │   ├── JoinRoomForm.vue     # 加入房间表单
    │   │   └── AIAgentControls.vue  # AI 代理控制组件
    │   └── icons/                   # 图标组件目录
    ├── types/
    │   ├── websocket.js             # WebSocket 类型定义
    │   ├── game.js                  # 游戏相关类型
    │   ├── player.js                # 玩家相关类型
    │   └── room.js                  # 房间相关类型
    ├── config/
    │   └── assetConfig.js           # 静态资源配置
    ├── plugins/
    │   └── element-plus.js          # Element Plus 插件配置
    ├── utils/
    │   └── imageOptimization.js     # 图片优化工具
    └── assets/
        └── styles/
            ├── global.css           # 全局样式
            ├── transitions.css      # 过渡动画
            ├── typography.css       # 排版样式
            └── interactive.css      # 交互样式

scripts/
├── deploy.sh                        # 部署脚本
├── run-phase7-tests.sh              # Phase7 测试脚本
└── smoke-tests.sh                   # 冒烟测试脚本
```

## 技术栈

### 主要依赖
- **Python 3.11+** - 后端主要语言
- **FastAPI 0.109+** - 异步 Web 框架，提供 RESTful API
- **SQLAlchemy 2.0+** - 异步 ORM，配合 aiomysql 使用 MySQL
- **MySQL 8.0** - 关系型数据库，用于持久化游戏状态和用户数据
- **python-socketio 5.11+** - WebSocket 实时通信
- **LangChain 0.1+** - LLM 集成框架
- **OpenAI 1.10+** - AI 决策生成
- **Pydantic 2.5+** - 数据验证和序列化
- **Vue 3.5+** - 前端响应式框架（Composition API）
- **Element Plus 2.11+** - Vue 3 UI 组件库
- **Pinia 3.0+** - Vue 状态管理
- **Socket.IO Client 4.8+** - 前端 WebSocket 客户端
- **Axios 1.13+** - HTTP 请求库
- **Vue Router 4.6+** - 前端路由

### 开发工具
- **uv** - Python 依赖管理（**必须**使用 uv）
- **pnpm / npm** - Node.js 包管理（推荐使用 pnpm）
- **Vite 7.0+** - 前端构建工具和开发服务器
- **Docker + Docker Compose** - 容器化部署
- **pytest 7.4+** - Python 测试框架
- **pytest-asyncio 0.23+** - 异步测试支持
- **pytest-cov 4.1+** - 测试覆盖率
- **Vitest 4.0+** - 前端单元测试
- **Playwright 1.57+** - E2E 端到端测试
- **Ruff 0.1+** - Python 代码检查和格式化
- **ESLint 9.0+ + Prettier 3.7+** - JavaScript/Vue 代码检查和格式化
- **Alembic 1.13+** - 数据库迁移工具

## 开发和使用指南

### 环境配置
```bash
# 后端依赖安装（必须使用 uv）
cd backend
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# 前端依赖安装
cd frontend
pnpm install

# 后端环境变量配置 (创建 backend/.env 文件)
AI_API_KEY=your-api-key                  # 主要 API Key（支持 OpenAI 或兼容提供商如 Deepseek）
AI_API_BASE_URL=                         # 可选：自定义 API 基础 URL
OPENAI_API_KEY=your-openai-api-key       # 可选：向后兼容
SECRET_KEY=your-secret-key
DATABASE_URL=mysql+aiomysql://vbrpg:vbrpgpassword@localhost:3306/vbrpg
CORS_ORIGINS=http://localhost:5173
LOG_LEVEL=INFO

# 前端环境变量配置 (创建 frontend/.env.local 文件)
VITE_API_URL=http://localhost:8000
VITE_WS_URL=http://localhost:8000
```

### 构建和运行
```bash
# 后端开发服务器
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 前端开发服务器
cd frontend
pnpm dev

# Docker 一键启动（推荐）
docker-compose up -d

# 数据库迁移
cd backend
alembic upgrade head

# 前端构建生产版本
cd frontend
pnpm build
```

### 测试命令
```bash
# 后端测试
cd backend
pytest                          # 运行所有测试
pytest --cov=src               # 带覆盖率报告
pytest tests/unit/             # 仅单元测试
pytest tests/integration/      # 仅集成测试

# 前端测试
cd frontend
pnpm test                      # 运行单元测试
pnpm test:e2e                  # 运行 E2E 测试
pnpm test:coverage             # 带覆盖率报告
```

## 项目架构特点

### 设计模式
- **分层架构**: API 层 → 服务层 → 数据访问层，职责清晰分离
- **服务模式**: 业务逻辑封装在 Service 类中，保持 API 路由简洁
- **策略模式**: 游戏引擎可扩展支持多种桌游（犯罪现场、狼人杀等）
- **观察者模式**: WebSocket 事件驱动的实时通信
- **单例模式**: Socket.IO 服务器和 LLM 客户端实例
- **工厂模式**: AI 代理根据角色类型动态创建

### 数据流设计
- **请求流**: HTTP/WebSocket → 路由 → 服务 → 数据库
- **状态管理**: 前端 Pinia 存储 + 后端 GameState 模型
- **实时同步**: WebSocket 事件广播游戏状态变更
- **流式输出**: AI 发言和主持人公告支持打字机效果
- **缓存策略**: 内存回合锁防止并发冲突

### 错误处理
- **异常层次**: APIError → NotFoundError / BadRequestError / ConflictError 等
- **统一响应**: 标准化错误响应格式（code, message, details）
- **日志记录**: 结构化日志，支持不同级别输出
- **监控端点**: /api/v1/health 健康检查，/api/v1/monitoring/* 运行指标

## 安全考虑
- **会话管理**: 基于 Session Middleware 的会话认证
- **输入验证**: Pydantic 模型验证 + 输入清理（input_processing.py）防止注入攻击
- **CORS 配置**: 限制跨域请求来源
- **速率限制**: API 调用频率控制（rate_limiter.py）
- **环境变量**: 敏感配置通过环境变量管理，不提交至代码库

## 性能优化
- **异步 I/O**: 全异步数据库操作和 HTTP 处理（asyncio + aiomysql）
- **连接池**: SQLAlchemy 异步会话管理
- **WebSocket 复用**: 单连接多事件复用，减少连接开销
- **流式响应**: AI 生成内容流式输出，提升用户体验
- **回合锁**: 防止游戏状态并发修改

## 扩展性设计
- **游戏引擎插件**: 可添加新游戏引擎到 services/games/
- **AI 代理扩展**: 可添加新角色代理到 services/ai_agents/
- **静态数据配置**: 游戏类型和角色定义在 constants/ 目录，易于扩展
- **AI 性格扩展**: 新增 AI 性格类型和决策策略
- **多数据库支持**: 当前使用 MySQL，可通过 SQLAlchemy 切换到 PostgreSQL 等

## 部署和运维
- **容器化**: Docker + Docker Compose 部署，支持一键启动
- **环境分离**: 开发/生产环境变量配置
- **数据持久化**: Docker Volume 存储 MySQL 数据
- **日志管理**: 结构化日志输出，支持日志收集
- **健康检查**: /api/v1/health 端点供负载均衡器探测
- **数据库迁移**: Alembic 管理数据库版本
