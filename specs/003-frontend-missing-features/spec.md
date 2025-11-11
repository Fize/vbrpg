# Feature Specification: Frontend Missing Features Implementation

**Feature Branch**: `003-frontend-missing-features`  
**Created**: 2025-11-12  
**Status**: Draft  
**Input**: User description: "实现前端缺失功能：用户注册、玩家资料查看、房间列表筛选、游戏进行中功能、WebSocket事件处理完善、游戏逻辑实现"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - User Registration and Profile Management (Priority: P1)

玩家可以从游客账号升级为正式账号，设置完整的用户信息（用户名、邮箱、密码），并查看自己和其他玩家的公开资料。

**Why this priority**: 用户身份管理是平台的基础功能，必须先实现才能支持后续的游戏功能。没有完整的用户系统，玩家无法保存游戏进度和统计数据。

**Independent Test**: 可以通过创建游客账号，填写注册信息完成升级，然后查看个人资料和其他玩家资料来独立测试。即使其他功能未完成，这个功能也能独立提供用户管理价值。

**Acceptance Scenarios**:

1. **Given** 用户以游客身份登录，**When** 点击"升级账号"并填写用户名、邮箱、密码，**Then** 系统创建正式账号并显示成功消息
2. **Given** 用户输入已存在的用户名或邮箱，**When** 提交注册表单，**Then** 系统显示"用户名/邮箱已被使用"错误提示
3. **Given** 用户输入无效的邮箱格式，**When** 提交表单，**Then** 系统显示"请输入有效的邮箱地址"错误
4. **Given** 用户输入少于8个字符的密码，**When** 提交表单，**Then** 系统显示"密码至少需要8个字符"错误
5. **Given** 用户在游戏大厅中，**When** 点击其他玩家头像，**Then** 显示该玩家的公开资料（用户名、总游戏数、胜率等）
6. **Given** 用户查看自己的资料，**When** 访问个人中心，**Then** 显示完整的个人信息（包括邮箱等私密信息）

---

### User Story 2 - Room List Filtering (Priority: P2)

玩家可以浏览游戏房间列表，并通过状态（等待中/进行中/已完成）、游戏类型等条件筛选房间，快速找到想加入的房间。

**Why this priority**: 当平台有大量房间时，筛选功能能显著提升用户体验。这是一个增强功能，不影响核心游戏流程，但能提高用户满意度。

**Independent Test**: 可以通过创建多个不同状态和类型的房间，然后使用筛选器验证显示结果来独立测试。

**Acceptance Scenarios**:

1. **Given** 用户在房间列表页面，**When** 选择"等待中"状态筛选，**Then** 只显示状态为"Waiting"的房间
2. **Given** 用户在房间列表页面，**When** 选择特定游戏类型（如"犯罪现场"），**Then** 只显示该类型的房间
3. **Given** 用户同时应用多个筛选条件，**When** 点击筛选按钮，**Then** 显示同时满足所有条件的房间
4. **Given** 用户应用了筛选条件，**When** 点击"清除筛选"，**Then** 显示所有房间
5. **Given** 没有房间匹配筛选条件，**When** 应用筛选，**Then** 显示"未找到匹配的房间"提示信息

---

### User Story 3 - In-Game Chat System (Priority: P3)

玩家在游戏进行中可以通过聊天功能与其他玩家实时交流，讨论游戏策略或进行角色扮演对话。

**Why this priority**: 聊天增强了多人游戏的社交体验，但不是游戏核心机制。可以在基本游戏功能完成后再添加。

**Independent Test**: 可以通过创建房间、加入玩家，然后发送消息并验证其他玩家能实时接收来独立测试。

**Acceptance Scenarios**:

1. **Given** 用户在游戏房间中，**When** 在聊天框输入消息并按发送，**Then** 消息立即显示在聊天记录中，并广播给房间内所有玩家
2. **Given** 用户接收到新消息，**When** 消息到达，**Then** 聊天窗口自动滚动到最新消息
3. **Given** 用户输入空消息，**When** 尝试发送，**Then** 系统禁用发送按钮或显示提示
4. **Given** 用户输入超过字符限制的消息，**When** 继续输入，**Then** 系统显示剩余字符数提示
5. **Given** 用户断线重连，**When** 重新加入房间，**Then** 显示最近的聊天历史记录

---

### User Story 4 - Game Action Submission (Priority: P1)

玩家在游戏进行中可以提交游戏行动（调查、询问、指控等），系统处理行动并更新游戏状态。

**Why this priority**: 这是游戏的核心交互机制，没有行动系统就无法进行游戏。必须优先实现。

**Independent Test**: 可以通过启动游戏、轮到玩家回合时提交不同类型的行动，验证游戏状态更新来独立测试。

**Acceptance Scenarios**:

1. **Given** 轮到用户回合，**When** 选择"调查"行动并选择地点，**Then** 系统处理行动并显示调查结果
2. **Given** 轮到用户回合，**When** 选择"询问"行动并选择目标角色，**Then** 系统显示询问对话界面
3. **Given** 轮到用户回合，**When** 选择"指控"行动并提供证据，**Then** 系统验证指控并宣布游戏结果
4. **Given** 不是用户回合，**When** 尝试提交行动，**Then** 系统禁用行动按钮并显示"等待其他玩家"提示
5. **Given** 用户提交无效行动（如调查已调查过的地点），**When** 提交行动，**Then** 系统显示错误提示并允许重新选择
6. **Given** 用户行动超时，**When** 倒计时结束，**Then** 系统自动跳过该回合并通知所有玩家

---

### User Story 5 - Turn Timeout Warning (Priority: P2)

玩家在回合即将超时前收到明显的视觉和声音提示，避免因遗忘而错过回合。

**Why this priority**: 超时警告改善用户体验，减少因疏忽造成的挫败感，但不影响游戏基本运作。

**Independent Test**: 可以通过设置短超时时间、等待倒计时触发警告来独立测试。

**Acceptance Scenarios**:

1. **Given** 轮到用户回合且剩余时间少于30秒，**When** 倒计时进行，**Then** 显示红色闪烁的倒计时提示
2. **Given** 轮到用户回合且剩余10秒，**When** 倒计时进行，**Then** 播放提示音并显示"请尽快行动"警告
3. **Given** 用户在超时前提交行动，**When** 行动提交成功，**Then** 警告立即消失
4. **Given** 用户回合超时，**When** 倒计时结束，**Then** 显示"超时"提示并自动结束回合

---

### User Story 6 - WebSocket Event Handling Enhancement (Priority: P3)

系统正确处理所有 WebSocket 事件（大厅加入/离开确认、游戏状态更新、AI行动等），确保实时同步和良好的用户反馈。

**Why this priority**: 这是系统稳定性和用户体验的增强，但不是最小可用产品的必要条件。可以在核心功能完成后逐步完善。

**Independent Test**: 可以通过创建多人房间、执行各种操作，验证所有相关事件正确触发和处理来独立测试。

**Acceptance Scenarios**:

1. **Given** 用户加入大厅，**When** WebSocket 连接成功，**Then** 接收到"lobby_joined"确认消息
2. **Given** 游戏状态更新，**When** 收到"game_state_update"事件，**Then** 界面立即刷新显示最新状态
3. **Given** AI 玩家开始思考，**When** 收到"ai_thinking"事件，**Then** 显示"AI 正在思考..."加载动画
4. **Given** AI 玩家完成行动，**When** 收到"ai_action"事件，**Then** 显示 AI 行动详情并更新游戏状态
5. **Given** 当前回合改变，**When** 收到"turn_changed"事件，**Then** 高亮显示当前回合玩家并更新回合计数
6. **Given** 游戏结束，**When** 收到"game_ended"事件，**Then** 显示游戏结果界面包含获胜者信息

---

### User Story 7 - Crime Scene Game Core Logic (Priority: P1)

玩家可以玩完整的犯罪现场游戏，包括查看案件信息、调查地点、询问嫌疑人、收集线索、推理并指控凶手。

**Why this priority**: 这是平台的核心游戏内容，是用户使用平台的主要原因。必须实现才能提供完整的游戏体验。

**Independent Test**: 可以通过完整玩一局游戏，从开始到指控凶手结束，验证所有游戏机制正常工作来独立测试。

**Acceptance Scenarios**:

1. **Given** 游戏开始，**When** 玩家进入游戏界面，**Then** 显示案件背景、可调查地点列表、嫌疑人列表
2. **Given** 玩家调查地点，**When** 选择未调查的地点，**Then** 显示该地点的线索信息并标记为已调查
3. **Given** 玩家询问嫌疑人，**When** 选择嫌疑人和问题，**Then** 显示嫌疑人的回答并记录对话历史
4. **Given** 玩家收集了足够线索，**When** 选择"推理"功能，**Then** 显示已收集的所有线索和可能的推理方向
5. **Given** 玩家有充分证据，**When** 指控凶手并提供证据链，**Then** 系统验证指控是否正确并宣布游戏结果
6. **Given** 玩家指控错误，**When** 指控失败，**Then** 显示"指控失败"提示，玩家失去一次机会或失去回合
7. **Given** 玩家指控正确，**When** 指控成功，**Then** 显示胜利画面、案件真相、所有玩家统计数据

---

### Edge Cases

- 当用户在注册过程中断网会怎样？系统应保存部分填写的表单数据，重连后允许继续填写。
- 当多个玩家同时查看同一个玩家资料时会怎样？系统应正确处理并发请求，确保数据一致性。
- 当房间列表有数千个房间时筛选性能如何？系统应实现分页和懒加载，确保流畅体验。
- 当用户在聊天中发送恶意内容（脚本注入、超长文本）会怎样？系统应进行输入验证和内容过滤。
- 当用户回合超时但在最后一秒提交行动会怎样？系统应有明确的时间戳验证机制，避免竞态条件。
- 当 AI 玩家思考时间过长（LLM 超时）会怎样？系统应有超时机制和降级策略（使用预设行动）。
- 当玩家在游戏进行中断线并且超过重连宽限期会怎样？系统应将玩家替换为 AI，游戏继续进行。
- 当多个玩家同时指控不同的嫌疑人会怎样？系统应按回合顺序处理，只有轮到的玩家可以指控。
- 当所有玩家都指控错误且用完所有机会会怎样？游戏结束，显示"无人解决案件"结果。

## Requirements *(mandatory)*

### Functional Requirements

#### User Account Management (P1)

- **FR-001**: 系统必须提供完整的用户注册界面，包含用户名、邮箱、密码输入字段
- **FR-002**: 系统必须验证用户名长度为3-20个字符，支持字母、数字、下划线和中文
- **FR-003**: 系统必须验证邮箱格式符合标准邮箱格式规范
- **FR-004**: 系统必须验证密码长度至少8个字符
- **FR-005**: 系统必须在用户名或邮箱已存在时显示明确的错误提示
- **FR-006**: 系统必须提供查看其他玩家公开资料的功能，显示用户名、总游戏数、胜率、创建时间
- **FR-007**: 系统必须区分公开资料和私密信息，只有玩家本人可以看到邮箱等私密信息
- **FR-008**: 系统必须在注册成功后自动登录用户，无需再次输入凭据

#### Room List Management (P2)

- **FR-009**: 系统必须提供房间列表筛选器，支持按状态（Waiting/In Progress/Completed）筛选
- **FR-010**: 系统必须提供按游戏类型筛选房间的功能
- **FR-011**: 系统必须支持同时应用多个筛选条件的组合查询
- **FR-012**: 系统必须提供"清除筛选"功能，一键恢复显示所有房间
- **FR-013**: 系统必须在没有匹配房间时显示友好的空状态提示
- **FR-014**: 系统必须修复离开房间接口，使用正确的 DELETE 方法调用后端 API
- **FR-015**: 系统必须在房间列表中显示每个房间的基本信息（房间代码、玩家数、游戏类型、状态）

#### In-Game Chat (P3)

- **FR-016**: 系统必须提供游戏内聊天界面，显示在游戏界面的固定位置
- **FR-017**: 系统必须实时广播聊天消息给房间内所有玩家
- **FR-018**: 系统必须在接收到新消息时自动滚动到聊天记录底部
- **FR-019**: 系统必须显示消息发送者的用户名和发送时间
- **FR-020**: 系统必须限制单条消息长度为500个字符以内
- **FR-021**: 系统必须阻止发送空消息
- **FR-022**: 系统必须在断线重连后加载最近的聊天历史（最多50条）

#### Game Actions (P1)

- **FR-023**: 系统必须提供清晰的行动选择界面，包括调查、询问、指控等行动类型
- **FR-024**: 系统必须只允许当前回合玩家提交行动
- **FR-025**: 系统必须在提交行动后立即通过 WebSocket 发送给服务器
- **FR-026**: 系统必须在行动处理期间显示加载状态
- **FR-027**: 系统必须在收到服务器响应后更新游戏状态
- **FR-028**: 系统必须验证行动的有效性（例如不能重复调查同一地点）
- **FR-029**: 系统必须在行动失败时显示明确的错误信息
- **FR-030**: 系统必须实现回合倒计时功能，显示剩余时间
- **FR-031**: 系统必须在回合超时时自动跳过当前玩家

#### Turn Timeout Warning (P2)

- **FR-032**: 系统必须在剩余时间少于30秒时显示黄色警告提示
- **FR-033**: 系统必须在剩余时间少于10秒时显示红色闪烁警告
- **FR-034**: 系统必须在剩余时间少于10秒时播放提示音（可静音）
- **FR-035**: 系统必须在行动提交后立即清除超时警告
- **FR-036**: 系统必须在超时后显示"超时"提示并自动进入下一回合

#### WebSocket Event Handling (P3)

- **FR-037**: 系统必须正确处理 lobby_joined 和 lobby_left 确认事件
- **FR-038**: 系统必须在收到 game_state_update 事件时更新完整的游戏状态
- **FR-039**: 系统必须在收到 turn_changed 事件时高亮当前回合玩家
- **FR-040**: 系统必须在收到 ai_thinking 事件时显示 AI 思考动画
- **FR-041**: 系统必须在收到 ai_action 事件时展示 AI 的行动详情
- **FR-042**: 系统必须在收到 game_ended 事件时显示游戏结果界面
- **FR-043**: 系统必须为所有 WebSocket 事件实现错误处理和重试机制

#### Crime Scene Game Logic (P1)

- **FR-044**: 系统必须在游戏开始时显示案件背景故事和基本信息
- **FR-045**: 系统必须显示所有可调查地点的列表，标记已调查和未调查状态
- **FR-046**: 系统必须显示所有嫌疑人的列表和基本信息
- **FR-047**: 系统必须在玩家调查地点后显示发现的线索
- **FR-048**: 系统必须记录玩家已收集的所有线索，可随时查看
- **FR-049**: 系统必须在玩家询问嫌疑人时显示对话界面和嫌疑人回答
- **FR-050**: 系统必须记录所有询问历史，可随时回顾
- **FR-051**: 系统必须提供推理界面，展示线索之间的关联
- **FR-052**: 系统必须提供指控界面，允许玩家选择嫌疑人并提供证据
- **FR-053**: 系统必须验证指控的正确性并给出即时反馈
- **FR-054**: 系统必须在游戏结束时显示完整的案件真相和解释
- **FR-055**: 系统必须记录每个玩家的行动历史和决策过程

### Key Entities

- **RegisteredPlayer**: 正式注册的玩家账号，包含用户名、邮箱（唯一）、加密密码、注册时间、游戏统计数据
- **PublicProfile**: 玩家的公开资料，包含用户名、总游戏数、胜局数、胜率、创建时间（不包含邮箱等私密信息）
- **RoomFilter**: 房间筛选条件，包含状态筛选（Waiting/In Progress/Completed）、游戏类型筛选、结果数量限制
- **ChatMessage**: 聊天消息，包含发送者ID、发送者用户名、消息内容、发送时间戳、房间代码
- **GameAction**: 游戏行动，包含行动类型（调查/询问/指控/移动等）、目标对象（地点/角色）、行动参数、时间戳
- **TurnTimer**: 回合计时器，包含剩余时间、总时间限制、警告阈值、超时回调
- **ClueItem**: 线索物品，包含线索描述、发现地点、重要性等级、与案件的关联
- **Suspect**: 嫌疑人，包含姓名、角色描述、关系网络、可询问的话题列表
- **Investigation**: 调查记录，包含已调查地点列表、已发现线索列表、询问历史、推理笔记
- **Accusation**: 指控，包含指控的嫌疑人、提供的证据列表、指控理由、验证结果

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 用户可以在2分钟内完成账号注册，包括填写所有信息和验证
- **SC-002**: 用户可以在3次点击内找到并加入符合条件的游戏房间（使用筛选功能）
- **SC-003**: 聊天消息从发送到其他玩家接收的延迟少于1秒
- **SC-004**: 用户在回合超时前30秒和10秒时能看到明显的视觉警告
- **SC-005**: 90%的游戏行动在3秒内得到服务器响应并更新界面
- **SC-006**: 用户可以在5分钟内理解犯罪现场游戏的基本玩法和目标
- **SC-007**: 完整的犯罪现场游戏从开始到结束可以在30-60分钟内完成
- **SC-008**: 所有 WebSocket 事件的处理不会导致界面卡顿或延迟超过500毫秒
- **SC-009**: 用户在查看其他玩家资料时等待时间少于1秒
- **SC-010**: 房间列表筛选结果在500毫秒内显示
- **SC-011**: 系统支持至少100个并发用户同时使用所有功能而不出现性能下降
- **SC-012**: 85%的新用户能在首次游戏中成功完成至少一次调查和询问行动

## Assumptions

- 后端 API 已完全实现并且稳定运行（基于前期分析，后端接口已完备）
- WebSocket 服务器能够稳定处理实时消息，无需额外的服务端修改
- 用户使用的浏览器支持现代 Web API（WebSocket、本地存储、通知等）
- LLM 服务（用于 AI 玩家）响应时间在5-10秒内，超时有降级机制
- 犯罪现场游戏的案件数据和剧本已经准备好，存储在后端数据库中
- 用户网络连接稳定，短暂断线后可以自动重连（已有重连机制）
- 聊天内容不需要实时审核，但需要基本的输入验证（防止注入攻击）
- 游戏回合时间限制默认为60秒，可在房间创建时配置（30-300秒）
- 玩家资料的隐私级别遵循 GDPR 等数据保护标准（邮箱等敏感信息不公开）
- 前端框架（Vue 3）和 UI 库（Element Plus）已配置完成，可直接使用

## Dependencies

- 后端 REST API 服务必须正常运行（特别是玩家注册、房间查询接口）
- WebSocket 服务器必须正常运行并支持所有定义的事件
- 后端游戏引擎（CrimeSceneEngine）必须能够处理游戏逻辑和状态管理
- LLM 服务（用于 AI 玩家思考和行动）必须可访问并响应及时
- 用户认证和会话管理系统必须正常工作
- 数据库必须包含至少一个完整的犯罪现场案件数据

## Out of Scope

- 移动端原生应用开发（仅实现响应式 Web 界面）
- 高级聊天功能（表情包、图片分享、语音聊天等）
- 游戏回放和录像功能
- 社交功能（好友系统、私信、组队等）
- 排行榜和竞技系统
- 自定义游戏剧本编辑器
- 多语言国际化支持（当前仅支持中文）
- 监控和管理后台界面（按用户要求已移除）
- 支付和会员系统
- 成就和奖励系统
- 游戏内导师引导系统

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently - e.g., "Can be fully tested by [specific action] and delivers [specific value]"]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate email addresses"]  
- **FR-003**: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004**: System MUST [data requirement, e.g., "persist user preferences"]
- **FR-005**: System MUST [behavior, e.g., "log all security events"]

*Example of marking unclear requirements:*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: [Measurable metric, e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002**: [Measurable metric, e.g., "System handles 1000 concurrent users without degradation"]
- **SC-003**: [User satisfaction metric, e.g., "90% of users successfully complete primary task on first attempt"]
- **SC-004**: [Business metric, e.g., "Reduce support tickets related to [X] by 50%"]
