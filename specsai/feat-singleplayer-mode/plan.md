# VBRPG 单人游戏模式 - 技术设计文档

## 1. 概述

本文档描述将 VBRPG 从多人在线桌游平台改造为单人游戏模式的技术设计方案，包含数据库从 SQLite 迁移到 MySQL 的变更。

## 2. 技术选型

### 2.1 数据库迁移：SQLite → MySQL

**变更原因**：用户明确要求使用 MySQL 替换 SQLite

**技术栈**：
- **数据库**：MySQL 8.0+
- **异步驱动**：aiomysql（替换 aiosqlite）
- **ORM**：SQLAlchemy 2.0+（保持不变）
- **迁移工具**：Alembic（保持不变）

**配置变更**：
- `DATABASE_URL` 格式：`mysql+aiomysql://user:password@host:port/database`
- 移除 SQLite 特有配置（`check_same_thread`、`PRAGMA` 语句）
- 启用 MySQL 连接池（替换 `NullPool`）

### 2.2 保持不变的技术栈

以下技术栈保持现有实现，无需变更：
- FastAPI 异步 Web 框架
- python-socketio WebSocket 通信
- LangChain + OpenAI AI 决策
- Pydantic 数据验证
- pytest 测试框架

## 3. 架构设计

### 3.1 数据库连接层变更

**文件**：`backend/src/database.py`

```
变更前 (SQLite)                    变更后 (MySQL)
─────────────────────────────────────────────────────────
aiosqlite 驱动                  →  aiomysql 驱动
NullPool 连接池                 →  AsyncAdaptedQueuePool
check_same_thread=False         →  移除
PRAGMA 配置                     →  移除
```

**连接池配置**：
- `pool_size`: 5（默认连接数）
- `max_overflow`: 10（最大溢出连接数）
- `pool_recycle`: 3600（连接回收时间，秒）

### 3.2 数据模型变更

**需要调整的字段类型**：

| 模型 | 字段 | SQLite 类型 | MySQL 类型 |
|------|------|-------------|------------|
| GameState | game_data | Text | Text (LONGTEXT) |
| GameSession | final_state | Text | Text (LONGTEXT) |
| PlayerProfile | ui_preferences | Text | Text |

**JSON 存储说明**：
- SQLite 中 JSON 存储为 TEXT
- MySQL 中继续使用 TEXT（LONGTEXT），不使用 MySQL 的 JSON 类型以保持兼容性

### 3.3 移除的功能模块

#### 3.3.1 用户认证模块

**移除的组件**：
- `SessionMiddleware`（`src/utils/config.py`）
- `SessionSecurity`（`src/utils/config.py`）
- 用户注册/登录 API 端点

**保留的组件**：
- `Session` 模型（用于临时会话标识，但不再用于身份验证）

#### 3.3.2 多人房间功能

**移除的功能**：
- 房间码分享/加入功能
- 多玩家加入房间
- 房间所有权转移
- 断线重连等待机制

**简化的功能**：
- 房间创建后自动填充 AI 玩家
- 房间仅支持单个人类用户

### 3.4 新增功能模块

#### 3.4.1 角色选择模块

**新增字段**（`GameRoom` 模型）：
- `user_role`: 用户选择的角色（`spectator` 或具体角色 ID）
- `is_spectator_mode`: 是否为旁观者模式

**业务逻辑**：
1. 创建房间时，根据 `GameType` 确定玩家数量
2. 用户选择旁观者或参与角色
3. 剩余角色全部填充 AI 玩家
4. 选择确认后不可更改

#### 3.4.2 游戏控制模块

**新增字段**（`GameState` 模型）：
- `is_paused`: 已存在，保持不变

**新增 API 端点**：
- `POST /api/games/{room_code}/pause` - 暂停游戏
- `POST /api/games/{room_code}/resume` - 恢复游戏
- `POST /api/games/{room_code}/stop` - 停止游戏

**权限控制**：
- 旁观者：仅可暂停/恢复/停止
- 参与者：可进行游戏操作 + 暂停/恢复/停止

### 3.5 简化的房间创建流程

```
┌─────────────────────────────────────────────────────────────┐
│                     单人游戏创建流程                          │
├─────────────────────────────────────────────────────────────┤
│  1. 用户选择游戏类型                                          │
│     ↓                                                        │
│  2. 系统创建房间（无房间码分享）                               │
│     ↓                                                        │
│  3. 获取可用角色列表                                          │
│     ↓                                                        │
│  4. 用户选择：旁观者 / 参与角色                               │
│     ↓                                                        │
│  5. 系统自动填充 AI 玩家                                      │
│     ↓                                                        │
│  6. 游戏立即开始                                              │
└─────────────────────────────────────────────────────────────┘
```

## 4. API 变更设计

### 4.1 移除的 API

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 |
| POST | `/api/auth/logout` | 用户登出 |
| POST | `/api/rooms/{code}/join` | 加入房间 |
| GET | `/api/rooms/{code}/share` | 获取分享链接 |

### 4.2 修改的 API

| 方法 | 端点 | 变更说明 |
|------|------|----------|
| POST | `/api/rooms` | 移除认证要求，新增角色选择参数 |
| GET | `/api/rooms/{code}` | 移除认证要求 |
| POST | `/api/rooms/{code}/start` | 简化为自动开始，移除人数检查 |

### 4.3 新增的 API

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/games/{game_type}/roles` | 获取游戏类型的可用角色列表 |
| POST | `/api/rooms/{code}/select-role` | 选择参与角色或旁观模式 |
| POST | `/api/games/{room_code}/pause` | 暂停游戏 |
| POST | `/api/games/{room_code}/resume` | 恢复游戏 |
| POST | `/api/games/{room_code}/stop` | 停止游戏 |

## 5. 数据模型变更

### 5.1 GameRoom 模型修改

```
新增字段：
- user_role: String(50)         # 用户选择的角色 ID 或 "spectator"
- is_spectator_mode: Boolean    # 是否为旁观者模式

移除字段：
- owner_id                      # 不再需要所有权概念
- created_by                    # 简化为匿名创建

保留但简化的字段：
- code                          # 保留用于内部标识，但不再用于分享
```

### 5.2 GameRoomParticipant 模型修改

```
简化的逻辑：
- session_id                    # 用于标识唯一用户（非认证）
- is_ai_agent                   # 除用户外全部为 AI
- replaced_by_ai                # 移除，不再有断线替补场景
```

### 5.3 移除的模型/表

无需移除现有模型，但以下功能将不再使用：
- `Player` 模型的用户注册功能（`is_guest=False` 场景）
- `PlayerProfile` 模型的统计功能（无持久用户）

## 6. 部署配置变更

### 6.1 Docker Compose 变更

新增 MySQL 服务：

```yaml
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: vbrpg
      MYSQL_USER: vbrpg
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"
    networks:
      - vbrpg
```

Backend 服务配置变更：

```yaml
backend:
  environment:
    - DATABASE_URL=mysql+aiomysql://vbrpg:${MYSQL_PASSWORD}@mysql:3306/vbrpg
```

### 6.2 环境变量变更

| 变量 | 说明 | 示例值 |
|------|------|--------|
| DATABASE_URL | MySQL 连接字符串 | `mysql+aiomysql://user:pass@host:3306/db` |
| MYSQL_ROOT_PASSWORD | MySQL root 密码 | 生产环境强密码 |
| MYSQL_PASSWORD | 应用数据库密码 | 生产环境强密码 |

### 6.3 依赖变更

**pyproject.toml 变更**：

```toml
# 移除
"aiosqlite>=0.19.0",

# 新增
"aiomysql>=0.2.0",
"cryptography>=41.0.0",  # MySQL SSL 支持
```

## 7. 迁移步骤

### 7.1 数据库迁移

1. 创建新的 Alembic 迁移脚本
2. 更新数据库连接配置
3. 执行数据库 Schema 迁移
4. 验证数据模型兼容性

### 7.2 代码变更顺序

1. **Phase 1**：数据库层变更
   - 更新 `database.py` 连接配置
   - 更新 `pyproject.toml` 依赖
   - 创建 Alembic 迁移脚本

2. **Phase 2**：移除认证功能
   - 移除 `SessionMiddleware`
   - 移除认证相关 API 端点
   - 简化请求处理流程

3. **Phase 3**：房间逻辑简化
   - 修改 `GameRoomService` 创建逻辑
   - 实现自动 AI 填充
   - 移除多人加入功能

4. **Phase 4**：新增功能
   - 实现角色选择 API
   - 实现游戏控制 API（暂停/恢复/停止）
   - 更新 WebSocket 事件处理

## 8. 测试策略

### 8.1 单元测试

- 数据库连接测试（MySQL）
- 房间创建流程测试
- 角色选择逻辑测试
- 游戏控制功能测试

### 8.2 集成测试

- 完整单人游戏流程测试
- AI 玩家自动填充测试
- 暂停/恢复/停止功能测试

### 8.3 测试环境

- 使用 Docker MySQL 容器
- 配置测试专用数据库

## 9. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| MySQL 连接池配置不当 | 性能问题 | 监控连接池使用情况，调整参数 |
| JSON 数据兼容性 | 数据解析错误 | 使用 TEXT 类型，保持 JSON 序列化方式不变 |
| 认证移除后的安全性 | 滥用风险 | 保留速率限制，监控异常请求 |
