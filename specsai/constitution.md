# AI-Powered Tabletop Game Platform (VBRPG) - 规约

## 技术栈

### 主要依赖

#### 后端
- **Python 3.11+** - 核心编程语言
- **FastAPI 0.109+** - 异步 Web 框架，提供 REST API 和自动文档生成
- **SQLAlchemy 2.0+** - 异步 ORM，配合 aiosqlite 使用
- **python-socketio 5.11+** - WebSocket 服务器 (Socket.IO 协议)
- **Alembic 1.13+** - 数据库迁移工具
- **LangChain 0.1+** - LLM 集成框架
- **langchain-openai 0.0.5+** - OpenAI API 集成
- **Pydantic 2.5+** - 数据验证和设置管理
- **pydantic-settings 2.1+** - 环境变量配置

#### 前端
- **Vue 3.4+** - 渐进式 JavaScript 框架 (Composition API)
- **Element Plus 2.5+** - Vue 3 UI 组件库
- **Pinia 2.1+** - Vue 状态管理
- **Vue Router 4.2+** - 客户端路由
- **Axios 1.6+** - HTTP 客户端
- **socket.io-client 4.6+** - WebSocket 客户端

#### 数据库
- **SQLite** - 嵌入式数据库 (WAL 模式，支持并发)

### 开发工具

#### 后端
- **pip / uv** - Python 依赖管理
- **python venv** - 虚拟环境管理
- **pytest 7.4+** - 单元测试和集成测试框架
- **pytest-asyncio 0.23+** - 异步测试支持
- **pytest-cov 4.1+** - 测试覆盖率报告
- **httpx 0.26+** - 异步 HTTP 测试客户端
- **Ruff 0.1+** - 代码检查和格式化工具

#### 前端
- **pnpm / npm** - Node.js 包管理
- **Vite 5.0+** - 前端构建和开发服务器
- **Vitest 1.2+** - 单元测试框架
- **@vue/test-utils 2.4+** - Vue 组件测试工具
- **Playwright 1.41+** - E2E 测试框架
- **ESLint 8.56+** - JavaScript/Vue 代码检查
- **Prettier 3.2+** - 代码格式化

## 项目开发要求

### 日志

#### 后端日志规范
- 使用 Python 标准库 `logging` 模块
- 通过 `src/utils/logging_config.py` 统一配置
- 日志格式: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- 日志级别通过环境变量 `LOG_LEVEL` 配置 (默认 INFO)
- 使用 `get_logger(__name__)` 获取模块级别的 logger
- 第三方库日志级别独立配置:
  - SQLAlchemy: WARNING
  - Uvicorn: INFO
  - SocketIO: INFO

```python
# 使用示例
from src.utils.logging_config import get_logger
logger = get_logger(__name__)

logger.info("操作成功", extra={"user_id": user_id})
logger.error("操作失败", exc_info=True)
```

#### 前端日志规范
- 使用 `console` 对象进行日志输出
- 开发环境使用 `console.log`, `console.warn`, `console.error`
- 生产环境通过构建配置移除非必要日志

### 指标监控

- 提供 `/monitoring/health` 健康检查端点
- 提供 `/monitoring/metrics` 指标端点 (Prometheus 格式)
- 监控指标包括:
  - `active_games` - 活跃游戏数
  - `waiting_rooms` - 等待中房间数
  - `total_players` - 总玩家数
  - `guest_players` - 访客玩家数
  - `completed_games` - 已完成游戏数
  - `uptime_seconds` - 应用运行时间

### 错误处理

#### 异常层级结构
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
  "error": "错误描述信息",
  "code": "ERROR_CODE",
  "details": {
    "field": "额外错误详情"
  }
}
```

#### 错误处理原则
- 所有自定义异常继承自 `APIError` 基类
- 异常类包含 `message`, `status_code`, `code`, `details` 属性
- 使用语义化的错误码 (如 `NOT_FOUND`, `BAD_REQUEST`, `RATE_LIMIT_EXCEEDED`)
- 在服务层抛出业务异常，由 API 层转换为 HTTP 响应
- 记录错误日志时包含完整的异常堆栈 (`exc_info=True`)

### 测试要求

#### 后端测试
- 测试文件放置在 `backend/tests/` 目录
- 测试文件命名: `test_*.py`
- 测试类命名: `Test*`
- 测试函数命名: `test_*`
- 使用 pytest markers 区分测试类型:
  - `@pytest.mark.unit` - 单元测试
  - `@pytest.mark.integration` - 集成测试
  - `@pytest.mark.slow` - 运行较慢的测试
- 测试覆盖率报告: HTML, XML, 终端输出

```bash
# 运行测试
pytest

# 运行特定标记的测试
pytest -m unit
pytest -m integration
```

#### 前端测试
- 单元测试: `frontend/tests/` + Vitest
- E2E 测试: `frontend/tests/` + Playwright

```bash
# 单元测试
pnpm test
pnpm test:coverage

# E2E 测试
pnpm test:e2e
```

### 代码质量

#### 后端 (Ruff)
- 行长度限制: 100 字符
- 目标 Python 版本: 3.11
- 启用规则:
  - E (pycodestyle errors)
  - W (pycodestyle warnings)
  - F (pyflakes)
  - I (isort)
  - B (flake8-bugbear)
  - C4 (flake8-comprehensions)

#### 前端 (ESLint + Prettier)
- ESLint 配合 eslint-plugin-vue 检查 Vue 代码
- Prettier 统一代码格式化

```bash
# 后端代码检查
ruff check .
ruff format .

# 前端代码检查和格式化
pnpm lint
pnpm format
```
