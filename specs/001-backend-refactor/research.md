# Research Findings: Backend Single User Refactor

**Branch**: 001-backend-refactor  
**Date**: 2025-11-26  
**Purpose**: Research findings to resolve technical context unknowns

## Technology Choices

### Python Version

**Decision**: Python 3.11

**Rationale**: 
- Python 3.11是目前最新的LTS版本，提供显著的性能提升
- 项目现有代码已经使用Python，保持技术栈一致性
- FastAPI和SQLAlchemy等主要依赖完全支持Python 3.11
- 适合本地开发环境，无需考虑兼容性问题

**Alternatives considered**: Python 3.10 (现有版本，但缺少性能优化), Python 3.12 (太新，可能有兼容性问题)

### Primary Dependencies

**Decision**: 
- **Web框架**: FastAPI (保持现有)
- **ORM**: SQLAlchemy (保持现有)
- **WebSocket**: python-socketio (保持现有)
- **AI库**: 保持现有的AI/ML依赖，移除认证相关依赖

**Rationale**: 
- FastAPI提供高性能异步API支持，适合游戏场景
- SQLAlchemy已与现有数据模型集成，简化迁移
- WebSocket支持实时游戏更新，符合需求
- 移除认证相关依赖（如OAuth2、JWT库）简化系统

**Alternatives considered**: 完全替换框架（工作量过大），仅保留核心依赖（可能影响现有游戏逻辑）

### Storage

**Decision**: SQLite

**Rationale**:
- 单用户本地开发环境，SQLite提供零配置、轻量级解决方案
- 现有代码已支持SQLite，迁移成本低
- 30天短期数据存储需求，SQLite完全满足
- 文件型数据库，便于开发和测试

**Alternatives considered**: PostgreSQL（过重，多用户场景更适合），内存数据库（无法持久化游戏历史）

### Testing Framework

**Decision**: pytest + pytest-asyncio

**Rationale**:
- pytest是Python生态的黄金标准，支持丰富的插件生态
- pytest-asyncio支持FastAPI异步应用的测试
- 现有测试框架已使用pytest，保持一致性
- 支持单元测试、集成测试和API契约测试

**Alternatives considered**: unittest（功能有限），第三方测试框架（增加学习成本）

### Target Platform

**Decision**: 本地开发环境

**Rationale**:
- 用户明确表示"本项目还在本地开发阶段"
- 无需考虑云端部署的多租户、弹性扩展等复杂问题
- 可以专注于单用户体验优化

## Architecture Considerations

### Session Management

**Decision**: 使用内存会话管理 + 简单会话ID

**Rationale**:
- 单用户场景下，复杂的会话管理是不必要的
- 可以使用简单的UUID作为会话标识符
- 会话数据可以存储在内存中，无需持久化

### API Design

**Decision**: RESTful API + 简化路径结构

**Rationale**:
- 遵循用户要求的"符合REST风格"
- 简化路径结构，移除多用户相关的复杂路由
- 使用标准HTTP状态码和方法

### Data Model Simplification

**Decision**: 移除Player表，使用Session概念

**Rationale**:
- 不需要持久化用户身份，移除Player表及相关认证字段
- 使用简单的Session概念代表当前用户会话
- 保留GameRoom、AIAgent、GameState等核心游戏实体

## Performance Optimization

### API Performance

**Decision**: 异步处理 + 响应缓存

**Rationale**:
- 使用FastAPI的异步特性处理游戏操作
- 对不变的游戏类型等数据实施缓存
- 优化数据库查询，移除复杂的多用户关联查询

### Resource Management

**Decision**: 连接池 + 定期清理

**Rationale**:
- 使用数据库连接池优化资源使用
- 实施定期清理机制，删除超过30天的游戏历史
- 限制AI对手数量，防止资源过度消耗

## Risk Mitigation

### Data Migration

**Decision**: 渐进式迁移 + 数据清理脚本

**Rationale**:
- 渐进式迁移可以减少风险，确保系统稳定性
- 创建数据清理脚本，移除多用户相关数据
- 保留核心游戏数据，确保AI对手功能不受影响

### Testing Strategy

**Decision**: 测试优先 + 覆盖率目标

**Rationale**:
- 测试优先的开发方法确保重构质量
- 设置80%以上的测试覆盖率目标
- 特别关注API端点的契约测试和游戏逻辑的集成测试

## Conclusion

基于研究结果，我们确定了技术栈选择和架构方向。主要决策是保持现有核心技术，简化用户模型和API结构，专注于单用户体验优化。这些决策将为Phase 1的设计工作提供坚实基础。