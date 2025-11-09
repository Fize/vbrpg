# VBRPG 演示指南

## 🎉 服务已启动

### 📍 访问地址

- **前端界面**: http://localhost:5173
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs (Swagger UI)
- **健康检查**: http://localhost:8000/health

### 🎮 演示功能

#### 1. 游戏库
- 浏览可用的游戏类型
- 当前支持的游戏：犯罪现场（Crime Scene）

#### 2. 创建房间
- 选择游戏类型
- 设置房间名称和人数限制
- 获取房间代码（用于邀请其他玩家）

#### 3. 加入房间
- 使用 6 位房间代码加入游戏
- 查看房间内的玩家列表
- 等待游戏开始

#### 4. 房间大厅
- 查看所有玩家
- 房主可以开始游戏
- 其他玩家可以离开房间

### 🔧 技术栈

**后端**:
- FastAPI (异步 Web 框架)
- Socket.IO (实时通信)
- SQLite + Alembic (数据库)
- Python 3.12

**前端**:
- Vue 3 + TypeScript
- Vite (构建工具)
- Element-Plus (UI 组件)
- Pinia (状态管理)
- Socket.IO Client

### 📊 测试状态

- 单元测试: 21/22 通过 (95%)
- 集成测试: 7/13 通过 (54%)
- 模型测试: 34/34 通过 (100%)
- **总体**: 62/69 通过 (90%)

### 🚀 快速启动命令

```bash
# 手动启动后端（如需重启）
cd backend
uv run uvicorn main:socket_app --host 0.0.0.0 --port 8000

# 手动启动前端（如需重启）
cd frontend
npm run dev
```

### 🔍 API 端点示例

```bash
# 健康检查
curl http://localhost:8000/health

# 获取游戏类型列表
curl http://localhost:8000/api/v1/game-types

# 创建房间（需要认证）
curl -X POST http://localhost:8000/api/v1/rooms \
  -H "Content-Type: application/json" \
  -d '{"game_type_slug": "crime-scene", "room_name": "测试房间", "max_players": 6}'
```

### 📝 注意事项

1. **认证系统**: 当前使用简化的认证机制（开发环境）
2. **数据持久化**: SQLite 数据库位于 `backend/data/vbrpg.db`
3. **实时通信**: Socket.IO 已配置，支持实时房间更新
4. **CORS**: 已配置允许 localhost:5173 和 localhost:3000

### 🐛 已知限制

- AI 代理功能未完全实现
- 部分复杂游戏流程测试未通过
- 生产环境配置需要进一步优化

### 🛠️ 开发工具

- **数据库迁移**: `cd backend && uv run alembic upgrade head`
- **种子数据**: `cd backend && uv run python -m scripts.seed_data`
- **运行测试**: `cd backend && uv run pytest`
- **代码格式化**: `cd backend && uv run ruff check .`

### 📱 前端路由

- `/` - 首页/游戏库
- `/room/:code` - 游戏房间（根据房间代码）
- 更多路由可在 `frontend/src/router/index.ts` 查看

---

**提示**: 按 `Ctrl+C` 在对应终端停止服务
