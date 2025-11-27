# AI-Powered Tabletop Game Platform (VBRPG)

## 核心功能模块

### 1. AI代理系统 (AI Agent System)
- **功能描述**: 使用 LLM (大语言模型) 驱动的 AI 玩家,能够自动填充游戏空位、替代离线玩家
- **关键技术特性**: 
  - 基于 LangChain 集成 OpenAI API
  - 支持多种 AI 个性类型 (analytical_detective, intuitive_investigator, cautious_observer 等)
  - 异步决策生成,支持超时和重试机制
- **与其他模块的交互**: 
  - 与游戏状态服务交互获取当前游戏状态
  - 与 WebSocket 服务通信广播 AI 行动
  - 由 AI 调度器控制执行时机

### 2. 实时多人游戏系统 (Real-time Multiplayer System)
- **功能描述**: 基于 WebSocket 的实时游戏状态同步、房间管理、玩家连接管理
- **关键技术特性**:
  - Socket.IO 协议支持自动重连
  - 5分钟断线重连宽限期
  - 支持房间广播和私聊消息
- **与其他模块的交互**:
  - 与房间服务交互管理房间状态
  - 与玩家服务交互管理玩家状态
  - 触发 AI 代理服务在玩家断线时接管

### 3. 游戏引擎系统 (Game Engine System)
- **功能描述**: 犯罪现场(Crime Scene)桌游的核心逻辑引擎,处理游戏阶段、动作验证、胜负判定
- **关键技术特性**:
  - 阶段管理 (Setup, Investigation, Accusation, Resolution)
  - 动作验证 (调查地点、揭示线索、指控)
  - 胜负条件检测
- **与其他模块的交互**:
  - 被游戏状态服务调用处理游戏逻辑
  - 为 AI 代理提供可用动作列表

### 4. 房间与会话管理 (Room & Session Management)
- **功能描述**: 游戏房间创建/加入/管理,玩家会话管理,支持访客模式
- **关键技术特性**:
  - 8字符唯一房间码
  - 会话自动过期和延期
  - 访客账户30天过期机制
- **与其他模块的交互**:
  - 与 WebSocket 处理器交互管理房间连接
  - 与游戏状态服务交互初始化游戏

### 5. 前端用户界面 (Frontend UI)
- **功能描述**: 响应式 Web 界面,包含游戏大厅、房间配置、游戏板面、玩家资料等视图
- **关键技术特性**:
  - Vue 3 Composition API
  - Element Plus 组件库
  - Pinia 状态管理
  - 支持桌面和移动端
- **与其他模块的交互**:
  - 通过 REST API 与后端交互
  - 通过 WebSocket 接收实时更新

## 项目结构分析

### 入口文件
- `backend/main.py` - 后端 FastAPI 应用入口,配置中间件和路由
- `frontend/src/main.js` - 前端 Vue 应用入口
- `docker-compose.yml` - Docker 容器编排配置
- `start-demo.sh` - 快速启动演示脚本

### 核心业务包
- `backend/src/services/` - 核心业务服务层
- `backend/src/models/` - SQLAlchemy 数据模型定义
- `backend/src/api/` - REST API 端点
- `frontend/src/stores/` - Pinia 状态管理

### 基础设施包
- `backend/src/utils/` - 通用工具函数和配置
- `backend/src/websocket/` - WebSocket 服务器和事件处理
- `backend/src/integrations/` - 外部服务集成 (LLM)
- `frontend/src/services/` - API 和 WebSocket 客户端

### 代码目录文件结构

```
backend/
├── main.py                           # FastAPI 应用入口
├── alembic.ini                       # Alembic 数据库迁移配置
├── pyproject.toml                    # Python 项目配置和依赖
├── requirements.txt                  # pip 依赖列表
├── alembic/
│   ├── env.py                        # Alembic 环境配置
│   └── versions/                     # 数据库迁移脚本
├── src/
│   ├── __init__.py
│   ├── database.py                   # SQLAlchemy 异步引擎和会话配置
│   ├── api/
│   │   ├── __init__.py
│   │   ├── schemas.py                # Pydantic 请求/响应模型
│   │   ├── sessions.py               # 会话管理 API
│   │   ├── rooms.py                  # 房间管理 API
│   │   ├── games.py                  # 游戏操作 API
│   │   ├── players.py                # 玩家管理 API
│   │   └── monitoring.py             # 系统监控 API
│   ├── integrations/
│   │   ├── __init__.py
│   │   └── llm_client.py             # LangChain/OpenAI 集成客户端
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                   # SQLAlchemy 基类和 Mixin
│   │   ├── player.py                 # 玩家模型
│   │   ├── player_profile.py         # 玩家资料模型
│   │   ├── session.py                # 会话模型
│   │   ├── game_room.py              # 游戏房间模型
│   │   ├── game_room_participant.py  # 房间参与者模型
│   │   ├── game_session.py           # 游戏会话模型
│   │   ├── game_state.py             # 游戏状态模型
│   │   ├── game_type.py              # 游戏类型模型
│   │   └── ai_agent.py               # AI 代理模型
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_agent_service.py       # AI 代理管理服务
│   │   ├── ai_scheduler.py           # AI 行动调度器
│   │   ├── game_room_service.py      # 房间管理服务
│   │   ├── game_state_service.py     # 游戏状态管理服务
│   │   ├── player_service.py         # 玩家管理服务
│   │   └── games/
│   │       ├── __init__.py
│   │       └── crime_scene_engine.py # 犯罪现场游戏引擎
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py                 # 应用配置和响应模型
│   │   ├── errors.py                 # 自定义错误类
│   │   ├── logging_config.py         # 日志配置
│   │   ├── rate_limiter.py           # 速率限制器
│   │   ├── room_codes.py             # 房间码生成
│   │   ├── sanitization.py           # 输入清理
│   │   ├── sessions.py               # 会话工具
│   │   ├── username_generator.py     # 用户名生成器
│   │   └── validation.py             # 输入验证
│   └── websocket/
│       ├── __init__.py
│       ├── server.py                 # Socket.IO 服务器配置
│       └── handlers.py               # WebSocket 事件处理器

frontend/
├── index.html                        # HTML 入口
├── package.json                      # Node.js 项目配置
├── vite.config.js                    # Vite 构建配置
├── vitest.config.js                  # Vitest 测试配置
├── playwright.config.js              # Playwright E2E 测试配置
├── src/
│   ├── main.js                       # Vue 应用入口
│   ├── App.vue                       # 根组件
│   ├── assets/                       # 静态资源
│   ├── components/
│   │   ├── AppLayout.vue             # 应用布局
│   │   ├── CrimeSceneBoard.vue       # 犯罪现场游戏板面
│   │   ├── ActionPanel.vue           # 游戏动作面板
│   │   ├── PlayerList.vue            # 玩家列表
│   │   ├── TurnIndicator.vue         # 回合指示器
│   │   ├── AIThinkingIndicator.vue   # AI 思考指示器
│   │   ├── ConnectionStatus.vue      # 连接状态组件
│   │   ├── ReconnectionDialog.vue    # 重连对话框
│   │   ├── LoadingIndicator.vue      # 加载指示器
│   │   ├── ErrorDialog.vue           # 错误对话框
│   │   └── ...                       # 其他 UI 组件
│   ├── config/                       # 配置文件
│   ├── plugins/                      # Vue 插件
│   ├── router/
│   │   └── index.js                  # Vue Router 路由配置
│   ├── services/
│   │   ├── api.js                    # Axios API 客户端
│   │   ├── websocket.js              # Socket.IO 客户端
│   │   └── analytics.ts              # 分析服务
│   ├── stores/
│   │   ├── index.js                  # Pinia 存储入口
│   │   ├── auth.js                   # 认证状态
│   │   ├── game.js                   # 游戏状态
│   │   └── lobby.js                  # 大厅状态
│   ├── types/                        # TypeScript 类型定义
│   ├── utils/                        # 工具函数
│   └── views/
│       ├── GameLibrary.vue           # 游戏库视图
│       ├── GameDetails.vue           # 游戏详情视图
│       ├── GameRoomConfigView.vue    # 房间配置视图
│       ├── GameRoomLobby.vue         # 房间等待大厅
│       ├── GameBoard.vue             # 游戏主视图
│       ├── Profile.vue               # 个人资料视图
│       └── LobbyView.vue             # 大厅视图
```

## 技术栈

### 主要依赖
- **Python 3.11+** - 后端核心语言
- **FastAPI 0.109+** - 现代异步 Web 框架
- **SQLAlchemy 2.0+** - 异步 ORM (配合 aiosqlite)
- **python-socketio 5.11+** - WebSocket 服务器 (Socket.IO 协议)
- **LangChain 0.1+** - LLM 集成框架
- **Vue 3.4+** - 前端渐进式 JavaScript 框架
- **Element Plus 2.5+** - Vue 3 UI 组件库

### 开发工具
- **uv / pip** - Python 依赖管理
- **pnpm / npm** - Node.js 包管理
- **Vite 5.0+** - 前端构建工具
- **pytest 7.4+** - 后端测试框架
- **Vitest 1.2+** - 前端单元测试
- **Playwright 1.41+** - E2E 测试框架
- **Ruff 0.1+** - Python 代码检查和格式化

## 开发和使用指南

### 环境配置
```bash
# 后端依赖安装
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 前端依赖安装
cd frontend
pnpm install  # 或 npm install

# 环境变量配置
# 后端: 复制 .env.example 到 .env,配置 OPENAI_API_KEY
# 前端: 复制 .env.example 到 .env.local
```

### 构建和运行
```bash
# 初始化数据库
cd backend
python -m alembic upgrade head

# 启动后端 (开发模式)
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 启动前端 (开发模式)
cd frontend
pnpm dev  # 或 npm run dev

# 使用 Docker Compose 一键启动
docker-compose up -d

# 运行测试
cd backend && pytest
cd frontend && pnpm test
```

## 项目架构特点

### 设计模式
- **分层架构**: API 层 → 服务层 → 数据层
- **依赖注入**: FastAPI Depends 实现数据库会话注入
- **策略模式**: 不同 AI 个性类型使用不同决策策略
- **观察者模式**: WebSocket 事件广播机制

### 数据流设计
- **请求数据流**: HTTP/WebSocket → Router → Service → Database
- **状态管理**: 前端 Pinia Store + 后端数据库持久化
- **缓存策略**: SQLite WAL 模式提升并发性能

### 错误处理
- **自定义异常类**: APIError, NotFoundError, BadRequestError 等
- **全局错误处理**: FastAPI 异常处理器
- **日志记录**: 结构化日志配置,支持不同日志级别

## 安全考虑
- **CORS 配置**: 可配置的跨域资源共享
- **会话管理**: 支持会话过期和延期机制
- **输入验证**: Pydantic 模型验证所有输入
- **输入清理**: sanitization 模块防止 XSS

## 性能优化
- **异步 I/O**: 全异步数据库操作和 HTTP 处理
- **连接池**: SQLite WAL 模式优化并发
- **懒加载**: 前端路由组件懒加载

## 扩展性设计
- **游戏引擎抽象**: 可扩展支持更多桌游类型
- **AI 个性系统**: 可配置的 AI 行为参数
- **API 版本化**: /api/v1 路径前缀支持版本迭代

## 部署和运维
- **Docker 容器化**: Dockerfile + docker-compose.yml
- **环境配置**: 通过环境变量配置不同环境
- **健康检查**: /api/v1/health 端点
- **监控**: /api/v1/monitoring API 端点
