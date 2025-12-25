# AI-Powered Tabletop Game Platform (VBRPG)

## 核心功能模块

### 1. 狼人杀游戏系统
- **单人模式游戏**: 支持玩家与 9 名 AI 玩家进行狼人杀游戏
- **角色系统**: 支持狼人、预言家、女巫、猎人、村民等多种角色
- **游戏流程管理**: 包括夜晚阶段（狼人杀人、预言家查验、女巫救人/毒人）和白天阶段（发言讨论、投票放逐）
- **AI 智能决策**: 基于 LangChain 和大语言模型的智能 AI 玩家，能够进行策略决策、发言和投票
- **观察者模式**: 支持纯观察模式，观看 AI 玩家自动进行游戏
- **实时通信**: 通过 WebSocket 实时同步游戏状态和事件
- **与其他模块的交互**: 依赖 AI 服务模块、WebSocket 通信模块、数据库模块

### 2. AI 智能代理系统
- **多角色 AI 代理**: 为不同角色（狼人、预言家、女巫、猎人、村民）提供独立的 AI 决策逻辑
- **AI 主持人**: 自动主持游戏流程，生成游戏公告和剧情叙述
- **LLM 集成**: 使用 LangChain 框架集成 OpenAI 等大语言模型
- **流式响应**: 支持 AI 发言的流式输出，提升用户体验
- **决策上下文管理**: 维护游戏历史和上下文，使 AI 决策更加智能
- **与其他模块的交互**: 为游戏系统提供 AI 能力，通过 LLM 客户端调用外部 AI 服务

### 3. 房间和会话管理
- **游戏房间**: 创建和管理游戏房间，支持快速匹配和房间代码加入
- **玩家会话**: 管理玩家的游戏会话，支持访客模式（无需注册）
- **房间状态**: 维护房间状态（等待中、进行中、已完成）
- **参与者管理**: 管理房间内的人类玩家和 AI 玩家
- **与其他模块的交互**: 连接用户系统和游戏系统，为 WebSocket 通信提供会话基础

### 4. 实时通信系统
- **WebSocket 服务**: 基于 Socket.IO 的双向实时通信
- **事件广播**: 向房间内所有玩家广播游戏事件
- **流式传输**: 支持 AI 发言的流式传输
- **会话管理**: 管理 WebSocket 连接和用户会话映射
- **与其他模块的交互**: 为前端和后端提供实时通信桥梁，传递游戏状态和玩家操作

### 5. 用户和认证系统
- **访客模式**: 支持无需注册直接游戏
- **用户注册和登录**: 可选的用户账户系统
- **会话管理**: JWT 令牌或会话 ID 管理
- **玩家数据**: 存储玩家的基本信息和游戏历史
- **与其他模块的交互**: 为房间管理和游戏系统提供用户身份认证

### 6. 监控和日志系统
- **健康检查**: 提供系统健康状态和就绪检查端点
- **指标监控**: Prometheus 格式的监控指标（活跃游戏数、玩家数等）
- **结构化日志**: 统一的日志配置和管理
- **AI 调用日志**: 专门记录 AI 调用的详细信息，用于调试和优化
- **与其他模块的交互**: 为所有模块提供监控和日志能力

## 项目结构分析

### 入口文件
- `backend/main.py` - FastAPI 应用入口，配置路由、中间件、Socket.IO 集成
- `backend/pyproject.toml` - Python 项目配置，依赖管理
- `docker-compose.yml` - Docker 编排配置，定义后端、前端、MySQL 服务
- `frontend/src/main.js` - Vue 3 前端应用入口，配置路由、状态管理、UI 组件库
- `frontend/package.json` - Node.js 项目配置，前端依赖管理

### 核心业务包
- `backend/src/services/` - 业务服务层
  - `werewolf_game_service.py` - 狼人杀游戏核心业务逻辑（4700+ 行）
  - `game_room_service.py` - 房间管理服务
  - `player_service.py` - 玩家管理服务
  - `ai_service.py` - AI 调度服务
  - `games/werewolf_engine.py` - 狼人杀游戏引擎和状态机
  - `games/crime_scene_engine.py` - 犯罪现场游戏引擎（预留）
- `backend/src/services/ai_agents/` - AI 代理实现
  - `werewolf_agent.py` - 狼人角色 AI
  - `seer_agent.py` - 预言家角色 AI
  - `witch_agent.py` - 女巫角色 AI
  - `hunter_agent.py` - 猎人角色 AI
  - `villager_agent.py` - 村民角色 AI
  - `host/werewolf_host.py` - AI 游戏主持人
  - `prompts/` - AI 提示词模板
- `backend/src/models/` - 数据模型层
  - `game.py` - 游戏相关模型（房间、参与者、游戏状态、会话）
  - `user.py` - 用户和玩家模型
  - `base.py` - 模型基类和混入
- `backend/src/api/` - API 路由层
  - `werewolf_routes.py` - 狼人杀游戏 API
  - `game_routes.py` - 通用游戏 API
  - `user_routes.py` - 用户管理 API
  - `monitoring.py` - 监控端点 API
  - `schemas.py` - Pydantic 数据验证模式
- `frontend/src/views/` - 前端视图组件
  - `LobbyView.vue` - 游戏大厅
  - `CreateRoomView.vue` - 创建房间
  - `RoomLobbyView.vue` - 房间等待室
  - `WerewolfGameView.vue` - 狼人杀游戏主界面
  - `GameDetails.vue` - 游戏详情
- `frontend/src/stores/` - Pinia 状态管理
  - `game.js` - 游戏状态
  - `auth.js` - 认证状态
  - `lobby.js` - 大厅状态
  - `socket.js` - WebSocket 连接状态

### 基础设施包
- `backend/src/utils/` - 工具类和辅助函数
  - `config.py` - 配置管理（环境变量、设置）
  - `logging_config.py` - 日志配置
  - `ai_logger.py` - AI 调用专用日志
  - `errors.py` - 自定义异常类
  - `helpers.py` - 通用辅助函数
  - `rate_limiter.py` - 速率限制
  - `sessions.py` - 会话管理
  - `input_processing.py` - 输入处理和验证
- `backend/src/websocket/` - WebSocket 通信
  - `server.py` - Socket.IO 服务器配置
  - `handlers.py` - 通用 WebSocket 事件处理
  - `werewolf_handlers.py` - 狼人杀专用事件处理（2000+ 行）
  - `sessions.py` - WebSocket 会话管理
- `backend/src/integrations/` - 外部集成
  - `llm_client.py` - LangChain LLM 客户端（450+ 行）
- `backend/src/constants/` - 常量定义
  - `game_types.py` - 游戏类型定义
  - `roles.py` - 角色定义
- `frontend/src/services/` - 前端服务层
  - API 调用封装
- `frontend/src/components/` - Vue 可复用组件
- `frontend/src/utils/` - 前端工具函数

### 代码目录文件结构

```
backend/src/
├── __init__.py                           # 包初始化
├── database.py                           # 数据库连接和会话管理（MySQL + SQLAlchemy）
├── api/                                  # API 路由层
│   ├── __init__.py
│   ├── schemas.py                        # Pydantic 请求/响应模式定义
│   ├── game_routes.py                    # 通用游戏 API 端点
│   ├── user_routes.py                    # 用户管理 API 端点
│   ├── werewolf_routes.py                # 狼人杀游戏专用 API（快速开始、行动处理）
│   └── monitoring.py                     # 监控端点（健康检查、Prometheus 指标）
├── models/                               # SQLAlchemy 数据模型层
│   ├── __init__.py
│   ├── base.py                           # 模型基类（UUID 混入、时间戳混入）
│   ├── user.py                           # 用户和玩家模型
│   └── game.py                           # 游戏房间、参与者、状态、会话模型
├── services/                             # 业务服务层
│   ├── __init__.py
│   ├── werewolf_game_service.py          # 狼人杀游戏核心服务（4700+ 行）
│   ├── game_room_service.py              # 房间管理服务
│   ├── game_state_service.py             # 游戏状态服务
│   ├── player_service.py                 # 玩家管理服务
│   ├── ai_service.py                     # AI 调度服务
│   ├── games/                            # 游戏引擎
│   │   ├── __init__.py
│   │   ├── werewolf_engine.py            # 狼人杀游戏引擎和状态机
│   │   └── crime_scene_engine.py         # 犯罪现场游戏引擎（预留）
│   └── ai_agents/                        # AI 智能代理
│       ├── __init__.py
│       ├── base.py                       # AI 代理基类
│       ├── werewolf_agent.py             # 狼人角色 AI
│       ├── seer_agent.py                 # 预言家角色 AI
│       ├── witch_agent.py                # 女巫角色 AI
│       ├── hunter_agent.py               # 猎人角色 AI
│       ├── villager_agent.py             # 村民角色 AI
│       ├── host/                         # AI 主持人
│       │   ├── __init__.py
│       │   ├── base_host.py              # 主持人基类
│       │   ├── werewolf_host.py          # 狼人杀主持人
│       │   └── prompts/                  # 主持人提示词
│       │       ├── __init__.py
│       │       └── host_prompts.py
│       └── prompts/                      # AI 提示词模板
│           ├── __init__.py
│           ├── common_prompts.py         # 通用提示词
│           ├── game_rules.py             # 游戏规则提示词
│           ├── werewolf_prompts.py       # 狼人提示词
│           ├── seer_prompts.py           # 预言家提示词
│           ├── witch_prompts.py          # 女巫提示词
│           ├── hunter_prompts.py         # 猎人提示词
│           ├── villager_prompts.py       # 村民提示词
│           └── host_prompts.py           # 主持人提示词（已迁移到 host/prompts/）
├── websocket/                            # WebSocket 实时通信
│   ├── __init__.py                       # 导出所有广播函数
│   ├── server.py                         # Socket.IO 服务器配置
│   ├── sessions.py                       # WebSocket 会话管理
│   ├── handlers.py                       # 通用 WebSocket 事件处理器
│   └── werewolf_handlers.py              # 狼人杀专用事件广播（2000+ 行）
├── integrations/                         # 外部服务集成
│   ├── __init__.py
│   └── llm_client.py                     # LangChain LLM 客户端（OpenAI API 集成）
├── utils/                                # 工具类和辅助函数
│   ├── __init__.py
│   ├── config.py                         # 配置管理（Pydantic Settings）
│   ├── logging_config.py                 # 日志配置（统一日志格式）
│   ├── ai_logger.py                      # AI 调用日志（专门记录 LLM 请求/响应）
│   ├── errors.py                         # 自定义异常类（APIError 层次结构）
│   ├── helpers.py                        # 通用辅助函数
│   ├── rate_limiter.py                   # 速率限制工具
│   ├── sessions.py                       # 会话管理工具
│   └── input_processing.py               # 输入处理和验证
└── constants/                            # 常量定义
    ├── __init__.py
    ├── game_types.py                     # 游戏类型定义（狼人杀、犯罪现场等）
    └── roles.py                          # 角色定义（狼人、预言家、女巫等）

frontend/src/
├── main.js                               # Vue 应用入口
├── App.vue                               # 根组件
├── router/                               # 路由配置
│   └── index.js                          # Vue Router 路由定义
├── views/                                # 页面视图组件
│   ├── LobbyView.vue                     # 游戏大厅
│   ├── GameDetails.vue                   # 游戏详情
│   ├── CreateRoomView.vue                # 创建房间
│   ├── RoomLobbyView.vue                 # 房间等待室
│   └── WerewolfGameView.vue              # 狼人杀游戏主界面
├── components/                           # 可复用组件
│   ├── common/                           # 通用组件
│   ├── werewolf/                         # 狼人杀专用组件
│   ├── lobby/                            # 大厅相关组件
│   └── icons/                            # 图标组件
├── stores/                               # Pinia 状态管理
│   ├── index.js                          # Store 入口
│   ├── auth.js                           # 认证状态
│   ├── game.js                           # 游戏状态
│   ├── lobby.js                          # 大厅状态
│   └── socket.js                         # WebSocket 连接状态
├── services/                             # API 服务封装
├── utils/                                # 前端工具函数
├── config/                               # 前端配置
├── assets/                               # 静态资源
├── plugins/                              # Vue 插件
└── types/                                # TypeScript 类型定义（如使用 TS）
```

## 技术栈

### 主要依赖

#### 后端
- **Python 3.11+** - 核心语言
- **FastAPI 0.109+** - 现代异步 Web 框架，提供 RESTful API
- **SQLAlchemy 2.0+** - 异步 ORM，用于数据库访问和对象映射
- **MySQL 8.0** - 关系型数据库，存储用户、房间、游戏数据
- **aiomysql 0.2+** - MySQL 异步数据库驱动
- **python-socketio 5.11+** - WebSocket 实时通信（Socket.IO 协议）
- **Pydantic 2.5+** - 数据验证和序列化
- **LangChain 0.1+** - AI 决策框架，用于集成大语言模型
- **langchain-openai 0.0.5+** - LangChain 的 OpenAI 集成
- **OpenAI 1.10+** - OpenAI API 客户端，用于调用 GPT 等模型
- **Alembic 1.13+** - 数据库迁移工具
- **python-dotenv 1.0+** - 环境变量管理
- **uvicorn 0.27+** - ASGI 服务器

#### 前端
- **Vue 3.5+** - 渐进式 JavaScript 框架（使用 Composition API）
- **Element Plus 2.11+** - Vue 3 UI 组件库
- **Pinia 3.0+** - Vue 3 状态管理库
- **Vue Router 4.6+** - Vue 路由管理
- **Socket.IO Client 4.8+** - WebSocket 客户端库
- **Axios 1.13+** - HTTP 请求库
- **Vite 7.0+** - 前端构建工具和开发服务器

### 开发工具

#### 后端
- **uv** - Python 包和项目管理工具（推荐使用，替代 pip）
- **虚拟环境** - 使用 `.venv` 虚拟环境进行依赖隔离
- **pytest 7.4+** - 测试框架
- **pytest-asyncio 0.23+** - 异步测试支持
- **pytest-cov 4.1+** - 测试覆盖率工具
- **Ruff 0.1+** - Python 代码检查和格式化（替代 flake8、black、isort）
- **httpx 0.26+** - 用于测试的异步 HTTP 客户端

#### 前端
- **pnpm / npm** - Node.js 包管理器（推荐使用 pnpm）
- **Vitest 4.0+** - 单元测试框架（Vite 原生支持）
- **Playwright 1.57+** - E2E 测试框架
- **ESLint 9.0+** - JavaScript/Vue 代码检查
- **Prettier 3.7+** - 代码格式化工具

#### DevOps
- **Docker & Docker Compose** - 容器化部署
- **Git** - 版本控制

## 开发和使用指南

### 环境配置

#### 后端环境配置

```bash
# 进入后端目录
cd backend

# 使用 uv 创建虚拟环境（推荐）
uv venv

# 激活虚拟环境
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 使用 uv 安装依赖
uv pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置以下关键变量：
# - DATABASE_URL: MySQL 数据库连接 URL
# - OPENAI_API_KEY 或 AI_API_KEY: LLM API 密钥
# - AI_API_BASE_URL: LLM API 基础 URL（可选，用于自定义 API 端点）
# - SECRET_KEY: JWT 密钥
# - LOG_LEVEL: 日志级别（DEBUG/INFO/WARNING/ERROR）

# 初始化数据库
alembic upgrade head
```

**关键环境变量说明：**
- `DATABASE_URL`: 数据库连接字符串，格式 `mysql+aiomysql://user:password@host:port/database`
- `OPENAI_API_KEY` / `AI_API_KEY`: OpenAI 或兼容的 LLM API 密钥
- `AI_API_BASE_URL`: 自定义 LLM API 端点（用于 OpenAI 兼容的第三方服务）
- `AI_MODEL`: AI 模型名称（默认值在代码中配置）
- `SECRET_KEY`: 用于会话加密和 JWT 签名
- `CORS_ORIGINS`: 允许的 CORS 源，多个用逗号分隔
- `LOG_LEVEL`: 日志级别，默认 INFO
- `ENVIRONMENT`: 运行环境（development/production）

#### 前端环境配置

```bash
# 进入前端目录
cd frontend

# 使用 pnpm 安装依赖（推荐）
pnpm install
# 或使用 npm
npm install

# 配置环境变量（可选）
cp .env.example .env.local
# 编辑 .env.local 文件：
# - VITE_API_URL: 后端 API 地址（默认 http://localhost:8000）
# - VITE_WS_URL: WebSocket 地址（默认 http://localhost:8000）
```

**关键环境变量说明：**
- `VITE_API_URL`: 后端 API 基础 URL
- `VITE_WS_URL`: WebSocket 服务器 URL

### 构建和运行

#### 开发模式

```bash
# 启动后端（在 backend/ 目录下）
source .venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 启动前端（在 frontend/ 目录下，新终端）
pnpm dev
# 或
npm run dev
```

**访问地址：**
- 前端应用: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/api/v1/health
- 监控指标: http://localhost:8000/monitoring/metrics

#### Docker 编排运行

```bash
# 在项目根目录下
docker-compose up --build

# 后台运行
docker-compose up -d

# 停止服务
docker-compose down
```

**Docker 服务端口映射：**
- MySQL: 3306
- 后端: 8000
- 前端: 5173

#### 测试命令

```bash
# 后端测试（在 backend/ 目录下）
pytest                           # 运行所有测试
pytest tests/test_specific.py    # 运行特定测试文件
pytest --cov                     # 生成覆盖率报告
pytest -v                        # 详细输出

# 前端测试（在 frontend/ 目录下）
pnpm test                        # 运行单元测试
pnpm test:coverage               # 生成覆盖率报告
pnpm test:e2e                    # 运行 E2E 测试
pnpm test:e2e:ui                 # 以 UI 模式运行 E2E 测试
```

#### 代码质量检查

```bash
# 后端代码检查（在 backend/ 目录下）
ruff check .                     # 检查代码问题
ruff format .                    # 格式化代码

# 前端代码检查（在 frontend/ 目录下）
pnpm lint                        # ESLint 检查
pnpm format                      # Prettier 格式化
```

## 项目架构特点

### 设计模式
- **分层架构**: 明确的 API 层、服务层、数据访问层分离
- **DDD 风格**: 将游戏逻辑封装在独立的服务类和引擎中（`WerewolfGameService`、`WerewolfEngine`）
- **异步编程**: 全面使用 Python async/await 和 Vue 3 Composition API
- **策略模式**: 不同角色的 AI 代理实现统一接口但有不同的决策策略
- **状态机模式**: 游戏引擎使用状态机管理游戏阶段转换
- **依赖注入**: FastAPI 的依赖注入系统管理数据库会话和服务实例
- **单例模式**: Socket.IO 服务器实例、游戏服务实例缓存
- **工厂模式**: 动态创建不同角色的 AI 代理实例

### 数据流设计
- **请求流向**: 
  - RESTful API: `前端 → API Router → Service Layer → Database → 响应`
  - WebSocket: `前端 ↔ Socket.IO Server ↔ Game Service ↔ Broadcast to Room`
- **游戏状态管理**: 
  - 数据库存储: 持久化游戏房间、参与者、会话数据（MySQL）
  - 内存缓存: 运行时游戏状态、AI 代理实例、WebSocket 会话映射（Python 字典）
- **实时同步**: 
  - 游戏状态变更通过 WebSocket 广播到房间内所有连接
  - 前端 Pinia Store 监听 Socket 事件更新本地状态
- **AI 决策流**: 
  - `Game Service → AI Agent → LLM Client → External LLM API → 解析响应 → 执行动作 → 广播结果`

### 错误处理
- **异常层次**: 
  - 基类 `APIError`，派生出 `NotFoundError`、`BadRequestError`、`UnauthorizedError`、`ConflictError` 等
  - 每种异常映射到对应的 HTTP 状态码
- **全局异常处理**: FastAPI 的异常处理器捕获所有 APIError 并返回统一格式的错误响应
- **日志记录**: 
  - 所有异常都记录到日志，包括堆栈跟踪（`exc_info=True`）
  - 前端通过 Element Plus Message 组件显示用户友好的错误消息
- **错误边界**: Vue 3 的 `errorHandler` 捕获未处理的前端错误

### 日志记录策略
- **统一配置**: `src/utils/logging_config.py` 统一配置所有日志器
- **日志格式**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- **日志级别**: 通过环境变量 `LOG_LEVEL` 控制，默认 INFO
- **模块级日志**: 每个模块使用 `logger = get_logger(__name__)` 获取命名日志器
- **AI 专用日志**: `ai_logger.py` 专门记录 LLM 调用的请求、响应、耗时
- **第三方库日志**: SQLAlchemy 设为 WARNING，Uvicorn/SocketIO 设为 INFO

## 安全考虑
- **环境变量隔离**: 敏感配置（API 密钥、数据库密码）通过环境变量注入，不硬编码
- **CORS 配置**: 通过 `CORS_ORIGINS` 环境变量限制允许的跨域请求源
- **SQL 注入防护**: 使用 SQLAlchemy ORM，避免原始 SQL 拼接
- **输入验证**: Pydantic 模式验证所有 API 请求输入
- **会话管理**: WebSocket 会话使用 SID 映射，隔离不同用户的数据
- **速率限制**: `rate_limiter.py` 提供速率限制工具（可选应用）
- **密码加密**: 如果实现完整用户系统，应使用 bcrypt 或 argon2 加密密码
- **JWT 令牌**: 如果使用 JWT，应配置合理的过期时间和刷新机制

## 性能优化
- **数据库连接池**: SQLAlchemy 配置连接池（pool_size=5, max_overflow=10）避免频繁创建连接
- **异步 I/O**: 全面使用异步数据库驱动（aiomysql）和异步 Web 框架（FastAPI）
- **流式响应**: AI 发言使用流式输出，减少首字节延迟，提升用户体验
- **懒加载关系**: SQLAlchemy 关系配置为懒加载，避免 N+1 查询
- **WebSocket 复用**: 单个 WebSocket 连接复用，避免频繁握手
- **前端优化**: 
  - Vite 快速冷启动和热更新
  - Vue 3 响应式系统性能优化
  - 按需加载 Element Plus 组件（如配置）
- **缓存策略**: 
  - 游戏服务实例缓存在内存中（`_game_services` 字典）
  - 静态游戏类型和角色数据作为常量定义，避免重复查询

## 扩展性设计
- **游戏引擎抽象**: `games/` 目录设计支持多种游戏类型（已有 `werewolf_engine.py`、`crime_scene_engine.py`）
- **AI 代理插件化**: 
  - 统一的 `BaseAgent` 接口
  - 新增角色只需继承基类并实现决策方法
- **提示词模板化**: AI 提示词集中在 `prompts/` 目录，易于调整和优化
- **LLM 客户端抽象**: `LLMClient` 封装了 LangChain，支持切换不同的 LLM 提供商
- **事件驱动架构**: WebSocket 事件系统支持灵活添加新事件类型
- **数据库迁移**: Alembic 管理数据库 schema 变更，支持版本化迁移
- **配置外部化**: 所有配置通过环境变量或配置文件管理，易于部署到不同环境
- **微服务就绪**: 服务层设计相对独立，未来可拆分为微服务

## 部署和运维
- **容器化部署**: 
  - Dockerfile 定义后端和前端镜像
  - docker-compose.yml 编排所有服务（后端、前端、MySQL）
- **环境隔离**: 
  - 开发环境使用 `.env` 文件
  - 生产环境通过容器环境变量注入配置
- **数据库管理**: 
  - 使用 Alembic 进行数据库迁移
  - MySQL 数据通过 Docker Volume 持久化
- **监控和健康检查**: 
  - `/monitoring/health`: 基本健康检查
  - `/monitoring/readiness`: 就绪检查（可用于 Kubernetes readinessProbe）
  - `/monitoring/liveness`: 存活检查（可用于 Kubernetes livenessProbe）
  - `/monitoring/metrics`: Prometheus 格式指标
  - `/monitoring/metrics/json`: JSON 格式指标
- **日志收集**: 
  - 结构化日志输出到标准输出
  - 可集成 ELK、Loki 等日志收集系统
- **指标监控**: 
  - 核心指标：活跃游戏数、等待房间数、玩家数、完成游戏总数、运行时间
  - 可集成 Prometheus + Grafana 进行可视化监控
- **部署流程**: 
  - 使用 `scripts/deploy.sh` 部署脚本
  - CI/CD 可集成 GitHub Actions、GitLab CI 等
- **数据备份**: 
  - MySQL 数据定期备份
  - 重要游戏日志和 AI 调用日志归档
