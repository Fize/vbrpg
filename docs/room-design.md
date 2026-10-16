# 房间与对局：全局模型（方案）

现状的错处：平台把「建房」直接做成了「建对局」——`POST /v1/instances` 一次同时选定游戏、占席位、
发牌、开始。房间本该是**先于任何一局存在、且是全局概念**的东西：先有房间，房间里才决定玩什么，
人来了、准备好了，才开这一局。

## 1. 两个概念

| | 房间 room | 对局 match |
| --- | --- | --- |
| 是什么 | 一张桌子：玩哪个游戏、几个席、谁在、谁准备好 | 这一局的运行态与记录 |
| 存在时间 | 从建房到开局（开局后房间只留一个指向对局的引用） | 从开局到结束 |
| 席位 | 真人成员（带准备状态）+ **AI 占位** | 真人席位（绑定账号）+ **真实生成的 AI 席位** |
| 游戏状态 | 没有 | `initialState` 发牌之后的完整状态 |
| 记录 | 没有 | `game_events` |

关键点：**AI 在房间里只是占位，只有真的开局才生成**。房间里不存在 AI 的 participant，也没有人格、
没有 prompt、不会消耗任何模型调用。

## 2. 数据

```sql
create table rooms (
  id text primary key,
  game_id text not null,            -- 建房间时就定死，之后不能改
  game_version text not null,
  owner_user_id text not null references users (id),
  status text not null check (status in ('open', 'started', 'closed', 'cancelled')),
  seat_plan jsonb not null,          -- [{key, control}]，真人席位与 AI 占位的顺序
  persona_public boolean not null default false,
  variables jsonb not null default '{}'::jsonb,  -- 建房时给的创建参数（如分类）
  instance_id text references game_instances (id), -- 开局后指向这一局
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  closed_at timestamptz
);

create table room_members (
  id text primary key,
  room_id text not null references rooms (id) on delete cascade,
  user_id text not null references users (id),
  seat_key text not null,            -- seat_plan 里的一个真人席位
  seat integer not null,
  ready boolean not null default false,
  created_at timestamptz not null default now(),
  unique (room_id, user_id),         -- 一个人在一间房里只占一个席位
  unique (room_id, seat_key)
);
```

席位数量**由游戏的声明卡死**（见 §3），建房时就校验；房间里不存在超出游戏上限的桌子。

## 3. 契约：游戏声明自己的席位上下限

`GameModule` 增 `minSeats` / `maxSeats`（必填）。谁是卧底：`3 / 12`。
平台在**建房**时校验 `seat_plan` 的长度落在区间内，越界直接拒绝（`SEATS_OUT_OF_RANGE`），
界面也不允许超出（选择器按区间渲染）。

## 4. 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/v1/rooms` | 建房：`{gameId, seats: [{key, control}], personaPublic?, variables?}`；房主自动占第一个真人席位 |
| `GET` | `/v1/rooms` | 开放中的房间 + 我参与过的房间 |
| `GET` | `/v1/rooms/:id` | 房间详情：席位表（真人 → 账号与准备状态，AI → 占位）、我是否在座、局面 |
| `POST` | `/v1/rooms/:id/join` | 占一个空着的真人席位 |
| `POST` | `/v1/rooms/:id/ready` | `{ready: boolean}`，只对自己有效 |
| `POST` | `/v1/rooms/:id/leave` | 离开并空出席位；房主离开则移交给下一个真人，没有别人就关闭房间 |
| `POST` | `/v1/rooms/:id/start` | 房主开局：校验 → 生成词对（若游戏要）→ 建实例与席位 → 房间转 `started` |
| `POST` | `/v1/rooms/:id/cancel` | 房主取消房间 |

开局校验：所有真人席位都有人、且**全部已准备**；AI 占位不参与准备。允许「只有房主一人 + AI 占位」开局，
这是 AI 陪玩的主场景。开局成功的一次调用才可能花模型调用（词对生成），因此**限流挂在开局上**（而非建房）。

## 5. 界面

`/rooms/:id` 一个 URL 两种形态，房间是全局的，所以用户只需要记住一个地方：

- **未开局**：席位表（真人席位显示账号名与「已准备/未准备」；AI 席位显示「AI 占位」）、我的准备开关、
  房主的「开始」按钮（未满足条件时按钮禁用并说明差什么）、房间信息（游戏、席位范围、分类、是否公开人格）。
- **已开局**：就是现在的对局房间（席位环、日志、动作面板）。同一个 URL 直接把房间内容换成对局视图。

大厅：列表分成「开放中的房间」（可加入）与「我的对局」（进行中/已结束）。建房对话框只定游戏与席位布局
（受 §3 区间限制），不填玩家账号——人在房间里占位并准备。

## 6. 与现有代码的关系

- `POST /v1/instances` 不再由用户直接调用：它变成开局内部的一步（建房 → 开局）。接口保留给内部与测试，
  但控制台不再暴露。
- 词对生成（M6-07）从「创建对局」挪到「开局」；`matchCreateByUser` 限流改名 `roomStartByUser`。
- 人格在开局时发给每个席位（真人 + AI），所以房间页里没有 MBTI，只有账号名与准备状态。
- 已有的对局房间页、记录、观战逻辑全部复用，房间开局后就是把 `instance_id` 指向的那一局渲染出来。

## 7. 需要人来定的规则

1. **一间房只开一局**（开局后房间即结束，想再来一局就再建房）——建议如此，符合聚会玩法。
2. **席位布局建房时定死**（几个真人、几个 AI 占位），之后只能占空位、不能改布局——建议如此。
3. **房主离开**：移交给下一个在座真人；没有别人则关闭房间——建议如此。
4. **允许单人开局**（房主 + AI 占位）——建议允许。

## 8. 任务

- [ ] `R-01` 迁移：`rooms` + `room_members`（含状态与唯一约束）。
- [ ] `R-02` 契约：`GameModule.minSeats/minSeats` + 建房时校验 + `seats` 声明进游戏目录（界面据此限制）。
- [ ] `R-03` 房间服务与接口：建房 / 列表 / 详情 / 加入 / 准备 / 离开 / 开局 / 取消，含权限（房主、在座）。
- [ ] `R-04` 开局：校验 → 生成词对 → 建实例与席位（真人绑账号、AI 生成）→ 房间转 `started`；限流挪到开局。
- [ ] `R-05` 界面：`/rooms/:id` 两形态、大厅的房间列表、建房对话框只定游戏与席位。
- [ ] `R-06` 测试：真库用例（占位不生成、准备门槛、单人开局、房主移交、席位越界）、路由用例、e2e（建房→加入→准备→开局→对局）。
