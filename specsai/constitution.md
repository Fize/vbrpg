# VBRPG - 规约

## 技术栈

### 主要依赖

#### 后端
- **Python 3.11+** - 核心语言
- **FastAPI 0.109+** - 异步 Web 框架，RESTful API
- **SQLAlchemy 2.0+** - 异步 ORM，数据库访问
- **MySQL 8.0** - 关系型数据库
- **aiomysql 0.2+** - MySQL 异步驱动
- **python-socketio 5.11+** - WebSocket 实时通信
- **Pydantic 2.5+** - 数据验证和序列化
- **LangChain 0.1+** - AI 决策框架
- **OpenAI 1.10+** - LLM API 集成

#### 前端
- **Vue 3.4+** - 响应式前端框架
- **Element Plus 2.5+** - UI 组件库
- **Pinia 2.1+** - 状态管理
- **Vue Router 4.2+** - 路由管理
- **Socket.IO Client 4.6+** - WebSocket 客户端
- **Axios 1.6+** - HTTP 请求库

### 开发工具

#### 后端
- **uv** - Python 依赖管理，**必须**使用 **uv**
- **虚拟环境** - 必须使用 `.venv` 虚拟环境隔离依赖
- **Alembic 1.13+** - 数据库迁移工具
- **pytest 7.4+** - 测试框架，配合 pytest-asyncio 支持异步测试
- **pytest-cov 4.1+** - 测试覆盖率工具
- **Ruff 0.1+** - 代码检查和格式化（替代 flake8, black, isort）

#### 前端
- **pnpm / npm** - Node.js 包管理，推荐使用 pnpm
- **Vite 5.0+** - 构建工具
- **Vitest 1.2+** - 单元测试框架
- **Playwright 1.41+** - E2E 测试框架
- **ESLint 8.56+** - JavaScript 代码检查
- **Prettier 3.2+** - 代码格式化

## 项目开发要求

### 日志

#### 后端日志规范
- 使用 Python 标准库 `logging` 模块
- 通过 `src/utils/logging_config.py` 统一配置
- 日志格式：`%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- 日志级别通过环境变量 `LOG_LEVEL` 控制（默认 INFO）
- 获取 logger 使用 `get_logger(__name__)` 确保模块级别命名
- 第三方库日志级别：SQLAlchemy WARNING，Uvicorn/SocketIO INFO

```python
# 正确用法
from src.utils.logging_config import get_logger
logger = get_logger(__name__)

logger.info("用户加入房间", extra={"room_code": code, "user_id": user_id})
logger.warning("重连超时", extra={"player_id": player_id})
logger.error("数据库连接失败", exc_info=True)
```

#### 前端日志规范
- 开发环境使用 `console.log/warn/error`
- 生产环境应禁用或最小化控制台输出
- WebSocket 连接状态变化必须记录日志

### 指标监控

- 监控端点：`/monitoring/metrics` (Prometheus 格式)、`/monitoring/metrics/json` (JSON 格式)
- 健康检查：`/monitoring/health`、`/monitoring/readiness`、`/monitoring/liveness`
- 核心指标：
  - `active_games` - 进行中的游戏数量 (gauge)
  - `waiting_rooms` - 等待中的房间数量 (gauge)
  - `total_players` - 总玩家数 (gauge)
  - `guest_players` - 访客玩家数 (gauge)
  - `completed_games_total` - 已完成游戏总数 (counter)
  - `uptime_seconds` - 应用运行时间 (counter)

### 错误处理

#### 异常层次结构
```
APIError (基类)
├── NotFoundError (404)
│   ├── RoomNotFoundError
│   └── SessionNotFoundError
├── BadRequestError (400)
│   └── InvalidGameActionError
├── UnauthorizedError (401)
│   └── SessionExpiredError
├── ForbiddenError (403)
├── ConflictError (409)
│   ├── RoomFullError
│   ├── GameAlreadyStartedError
│   └── DuplicateJoinError
├── RateLimitError (429)
└── AIAgentError (500)
```

#### 错误响应格式
```json
{
  "error": "错误消息",
  "code": "ERROR_CODE",
  "details": {}
}
```

#### 错误处理原则
- 业务异常使用自定义 APIError 子类
- 异常必须包含明确的错误码和用户友好的消息
- 数据库/外部服务错误需要捕获并转换为适当的 APIError
- 异步操作超时需要妥善处理并记录日志
- 前端需要统一处理 API 错误响应并展示给用户

### 测试要求

#### 后端测试
- 测试目录结构：`tests/unit/`、`tests/integration/`、`tests/performance/`
- 测试命名：`test_*.py` 文件，`test_*` 函数，`Test*` 类
- 异步测试使用 `pytest-asyncio`，配置 `asyncio_mode = auto`
- 覆盖率报告：终端、HTML、XML 三种格式
- 标记分类：`@pytest.mark.unit`、`@pytest.mark.integration`、`@pytest.mark.slow`

```bash
# 运行全部测试
pytest

# 仅运行单元测试
pytest tests/unit/

# 带覆盖率报告
pytest --cov=src --cov-report=html
```

#### 前端测试
- 单元测试：Vitest + Vue Test Utils
- E2E 测试：Playwright
- 测试目录：`tests/unit/`、`tests/integration/`、`tests/e2e/`

```bash
# 运行单元测试
pnpm test

# 运行 E2E 测试
pnpm test:e2e

# 覆盖率报告
pnpm test:coverage
```

### 代码质量

#### 后端 Ruff 配置
- 行长度限制：100 字符
- 目标版本：Python 3.11
- 启用规则：E (pycodestyle errors), W (warnings), F (pyflakes), I (isort), B (bugbear), C4 (comprehensions)
- 忽略规则：E501 (行长度由格式化器处理), B008 (允许函数调用作为默认参数)

```bash
# 代码检查
ruff check src/

# 代码格式化
ruff format src/
```

#### 前端 ESLint + Prettier
```bash
# 代码检查和修复
pnpm lint

# 代码格式化
pnpm format
```
