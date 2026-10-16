# 房间与对局：全局模型（方案）

现状的错处：平台把「建房」直接做成了「建对局」——`POST /v1/instances` 一次同时选定游戏、占席位、
发牌、开始。房间本该是**先于任何一局存在、且是全局概念**的东西：先有房间，房间里才决定玩什么，
人来了、准备好了，才开这一局。

## 1. 两个概念

| | 房间 room | 对局 match |
| --- | --- | --- |
| 是什么 | 一张桌子：玩哪个游戏、几个席、谁在、谁准备好 | 这一局的运行态与记录 |
| 存在时间 | 长期存在：可以连开多局，**同一时间只有一局**在跑 | 从开局到结束 |
| 席位 | 真人成员（带准备状态）+ **AI 占位** | 真人席位（绑定账号）+ **真实生成的 AI 席位** |
| 游戏状态 | 没有 | `initialState` 发牌之后的完整状态 |
| 记录 | 只有这一桌的历届对局引用 | `game_events` |

关键点：**AI 在房间里只是占位，只有真的开局才生成**。房间里不存在 AI 的 participant，也没有人格、
没有 prompt、不会消耗任何模型调用。

## 2. 数据

```sql
create table rooms (
  id text primary key,
  game_id text not null,            -- 建房间时就定死，之后不能改
  game_version text not null,
  owner_user_id text not null references users (id),
  -- 房间自己的生命周期。「有没有对局在跑」不存这里：它由 current_instance_id 的状态派生，
  -- 否则两处会各说各话。
  status text not null check (status in ('open', 'closed', 'cancelled')),
  seat_plan jsonb not null,          -- [{key, control}]，真人席位与 AI 占位的顺序；空闲时可改
  persona_public boolean not null default false,
  variables jsonb not null default '{}'::jsonb,  -- 创建参数（如分类）
  current_instance_id text references game_instances (id), -- 最近一局；终局后只作历史
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  closed_at timestamptz
);

-- 历届对局靠这一列反查：一间房可以开多局，每局都记得自己属于哪张桌子。
alter table game_instances add column room_id text references rooms (id);
create index game_instances_room_idx on game_instances (room_id, created_at desc);

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
| `PATCH` | `/v1/rooms/:id` | 房主改席位布局 / 是否公开人格 / 创建参数；**只在没有对局在跑时允许**，否则 409 |
| `POST` | `/v1/rooms/:id/start` | 房主开局：校验 → 生成词对（若游戏要）→ 建实例与席位 → 记为 `current_instance_id` |
| `POST` | `/v1/rooms/:id/cancel` | 房主关闭房间（不是取消某一局） |
| `GET` | `/v1/rooms/:id/matches` | 这一桌打过的每一局（按时间倒序） |

开局校验：所有真人席位都有人、且**全部已准备**；AI 占位不参与准备。允许「只有房主一人 + AI 占位」开局，
这是 AI 陪玩的主场景。开局成功的一次调用才可能花模型调用（词对生成），因此**限流挂在开局上**（而非建房）。

## 4.1 四条已定的规则与它们的后果

1. **可以连开多局，同一时间只有一局在跑。**
   - 「有没有对局在跑」= `current_instance_id` 指向的那一局状态不是 `completed`/`cancelled`。房间表不存这个，
     读的时候派生（一次 join），避免两处状态打架。
   - 一局结束后房间自动回到「可开局」：成员与席位都不变，**准备状态在开局时清零**（准备是对"下一局"的表态，
     打完一局再点一次更诚实；也顺手处理了有人离开没人在意的情况）。
   - 每局都是独立的对局记录，靠 `game_instances.room_id` 反查；`GET /v1/rooms/:id/matches` 给出历届。
2. **没有对局在跑时可以随意改布局。** 席位增删、真人/AI 占位互换、公开人格、创建参数都能改，
   唯一约束是落在游戏的 `minSeats`–`maxSeats` 内。被删掉的真人席位上的成员会**被移出房间**（可以再占别的空位）；
   新增的席位是空位。有对局在跑时任何修改都 409 `ROOM_BUSY`。
3. **房主离开 → 移交给下一个在座真人**；没有其他真人就关闭房间。移交只影响房间，不影响正在跑的对局。
4. **允许单人开局**（房主 + AI 占位）。

对局进行中有人离开：**允许**（房间成员变了），但那一局里他的席位不动——现在没有缺席处理机制（计时、
代为行动都还没有），这一局会停在等他。这是已知边界，等计时那件事做的时候一起解决。

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

已定（2026-10-16）：

1. **可以连开多局，同一时间只有一局**；一局结束后房间回到可开局状态。
2. **没有对局时可以随意改**（席位布局、公开人格、创建参数），有对局在跑时不允许改。
3. **房主离开移交给下一个在座真人**；没有别人则关闭房间。
4. **允许单人开局**（房主 + AI 占位）。

## 8. 任务

- [x] `R-01` 迁移：`rooms`（含 `current_instance_id`）+ `room_members` + `game_instances.room_id`。
- [x] `R-02` 契约：`GameModule.minSeats/minSeats` + 建房时校验 + `seats` 声明进游戏目录（界面据此限制）。
- [ ] `R-03` 房间服务与接口：建房 / 列表 / 详情 / 改布局 / 加入 / 准备 / 离开 / 开局 / 关闭 / 历届对局，
  含权限（房主、在座）与「有对局在跑」的派生判断。
- [ ] `R-04` 开局：校验 → 生成词对 → 建实例与席位（真人绑账号、AI 生成）→ 房间转 `started`；限流挪到开局。
- [ ] `R-05` 界面：`/rooms/:id` 两形态（未开局 = 席位表与准备 + 房主的布局编辑；局间 = 上一局结果与「再来一局」）、
  大厅的房间列表、建房对话框只定游戏与席位。
- [ ] `R-06` 测试：真库用例（占位不生成、准备门槛、单人开局、房主移交、席位越界、**连开两局**、跑局中改布局被拒）、
  路由用例、e2e（建房 → 加入 → 准备 → 开局 → 打完 → 再来一局）。
