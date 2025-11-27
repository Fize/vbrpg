# Implementation Plan: Backend Single User Refactor

**Branch**: `001-backend-refactor` | **Date**: 2025-11-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-backend-refactor/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

本重构旨在将多用户游戏平台后端转换为单用户游戏体验，主要功能包括：
1. 简化用户身份为本地会话标识符
2. 保留并优化AI对手系统
3. 创建全新的简化REST API，移除多用户相关功能
4. 保留WebSocket用于实时游戏更新
5. 仅保留短期（30天）本地游戏历史记录

技术方法将包括：重构数据模型、移除认证系统、简化API端点、优化游戏流程。

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: FastAPI, SQLAlchemy, python-socketio, AI库(移除认证相关)  
**Storage**: SQLite  
**Testing**: pytest, pytest-asyncio  
**Target Platform**: 本地开发环境  
**Project Type**: Web后端应用  
**Performance Goals**: 50%响应时间提升，30秒内创建游戏 (从需求SC-001/SC-002)  
**Constraints**: 单用户本地体验，无认证系统，短期数据存储  
**Scale/Scope**: 单用户应用，支持多种游戏类型，AI对手数量因游戏类型而异

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**注意：当前项目缺少具体的宪法文件，使用通用评估标准**

### 通用评估标准

1. **测试优先**：必须先编写测试，然后实现功能
2. **简化原则**：移除不必要的复杂度，专注于单用户体验
3. **性能目标**：确保满足响应时间和代码精简目标
4. **API设计**：遵循REST原则，创建简化的API接口

### 评估结果

- [x] 测试策略确定 - 已确定使用pytest + pytest-asyncio
- [x] 架构简化方案明确 - 已确定移除多用户相关功能，简化数据模型
- [x] 性能目标可衡量 - 已设定50%响应时间提升、30秒内创建游戏等可量化目标
- [x] API设计符合REST原则 - 已设计全新的RESTful API结构

### Phase 1设计后评估

- [x] 数据模型简化完成 - 移除Player表，使用Session概念
- [x] API契约设计完成 - 设计了符合REST风格的API接口
- [x] WebSocket协议定义 - 实现了实时游戏更新的WebSocket事件
- [x] 快速入门指南完成 - 提供了完整的设置和使用说明
- [x] 任务分解完成 - 已生成48个具体任务，分为6个阶段

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
backend/
├── src/
│   ├── models/              # 简化的数据模型
│   ├── services/            # 业务逻辑服务
│   ├── api/                 # 新的简化API端点
│   └── websocket/           # WebSocket处理
├── tests/
│   ├── contract/            # API契约测试
│   ├── integration/         # 集成测试
│   └── unit/                # 单元测试
└── migrations/              # 数据库迁移

frontend/ (保持不变，但需适配新API)
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/
```

**Structure Decision**: 选用Web应用结构，后端重构为简化单用户模式，保持前端目录结构但需要适配新的API接口

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 保留WebSocket通信 | 实时游戏更新需要 | 单纯REST API无法提供实时游戏体验 |
| 保留AI系统 | 核心游戏功能 | 移除AI将使游戏失去主要价值 |
| 短期数据存储 | 用户需要查看近期游戏记录 | 完全无存储将影响用户体验 |
