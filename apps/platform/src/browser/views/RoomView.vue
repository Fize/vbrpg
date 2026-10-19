<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { CopyDocument, Plus, Refresh } from "@element-plus/icons-vue";
import {
  api,
  apiRequestId,
  type GameCatalogueEntry,
  type MatchSummary,
  type RoomDetail,
  type RoomSeat,
} from "../services/api";
import { copyText } from "../services/clipboard";
import { uiErrorMessage } from "../services/messages";
import { formatTime, isOpen, statusLabel, statusTag } from "../services/match-labels";

const route = useRoute();
const router = useRouter();
const roomId = computed(() => String(route.params["roomId"] ?? ""));

const room = ref<RoomDetail | null>(null);
const matches = ref<MatchSummary[]>([]);
const game = ref<GameCatalogueEntry | null>(null);
const loading = ref(false);
const loadError = ref<string | null>(null);
const loadRequestId = ref<string | null>(null);
const actionError = ref<string | null>(null);
const actionRequestId = ref<string | null>(null);
const busy = ref(false);
const copyState = ref<string | null>(null);
const closeOpen = ref(false);

/** Seat edits happen on a copy: the room keeps its own plan until the owner saves. */
const draftPlan = ref<Array<{ key: string; control: "human" | "ai" }>>([]);
const planDirty = ref(false);

const mySeat = computed(() => room.value?.seatPlan.find((seat) => seat.isMe) ?? null);
const playing = computed(() => room.value?.playing === true);
const openForChanges = computed(() => room.value?.status === "open" && !playing.value);
const seatRange = computed(() => game.value?.seats ?? { min: 1, max: 24 });
/** Words a game derives from a category are not the table's business, so they stay off the page. */
const derivedNames = computed(
  () =>
    new Set(
      (game.value?.setup ?? [])
        .filter((field) => field.from !== undefined)
        .map((field) => field.name),
    ),
);
const shownVariables = computed(() =>
  Object.entries(room.value?.variables ?? {}).filter(([key]) => !derivedNames.value.has(key)),
);
const blockers = computed(() => {
  const detail = room.value;
  if (!detail) return ["房间还没加载完"];
  if (detail.status !== "open") return ["房间已关闭"];
  if (playing.value) return ["这一局还没结束"];
  const empty = detail.seatPlan.filter((seat) => seat.control === "human" && seat.userId === null);
  if (empty.length > 0) return [`还有空席位：${empty.map((seat) => seat.key).join("、")}`];
  const unready = detail.seatPlan.filter((seat) => seat.control === "human" && !seat.ready);
  if (unready.length > 0) return [`还没准备：${unready.map((seat) => seat.key).join("、")}`];
  return [];
});

async function load(): Promise<void> {
  loading.value = true;
  loadError.value = null;
  loadRequestId.value = null;
  try {
    room.value = await api.readRoom(roomId.value);
    matches.value = await api.listRoomMatches(roomId.value);
    const games = await api.listGames();
    game.value = games.find((entry) => entry.gameId === room.value?.gameId) ?? null;
    draftPlan.value = (room.value?.seatPlan ?? []).map((seat) => ({
      key: seat.key,
      control: seat.control,
    }));
    planDirty.value = false;
  } catch (error) {
    loadError.value = uiErrorMessage(error);
    loadRequestId.value = apiRequestId(error);
  } finally {
    loading.value = false;
  }
}

onMounted(load);
watch(roomId, load);

async function run(action: () => Promise<unknown>): Promise<void> {
  busy.value = true;
  actionError.value = null;
  actionRequestId.value = null;
  try {
    await action();
    await load();
  } catch (error) {
    actionError.value = uiErrorMessage(error);
    actionRequestId.value = apiRequestId(error);
  } finally {
    busy.value = false;
  }
}

async function copyCode(): Promise<void> {
  if (room.value === null) return;
  copyState.value = (await copyText(room.value.code)) ? "已复制" : "复制失败，请手动选择";
}

async function joinRoom(): Promise<void> {
  await run(() => api.joinRoom(roomId.value));
}

async function toggleReady(): Promise<void> {
  await run(() => api.setRoomReady(roomId.value, !(mySeat.value?.ready ?? false)));
}

async function leaveRoom(): Promise<void> {
  await run(() => api.leaveRoom(roomId.value));
}

async function savePlan(): Promise<void> {
  await run(() => api.updateRoom(roomId.value, { seats: draftPlan.value }));
}

async function confirmClose(): Promise<void> {
  await run(async () => {
    await api.closeRoom(roomId.value);
    closeOpen.value = false;
  });
}

async function start(): Promise<void> {
  await run(async () => {
    const { summary } = await api.startRoom(roomId.value);
    await router.push({ name: "match", params: { instanceId: summary.instanceId } });
  });
}

function addSeat(): void {
  const index = draftPlan.value.length + 1;
  draftPlan.value = [...draftPlan.value, { key: `s${index}`, control: "human" }];
  planDirty.value = true;
}

function removeSeat(index: number): void {
  draftPlan.value = draftPlan.value.filter((_, position) => position !== index);
  planDirty.value = true;
}

function seatLabel(seat: RoomSeat): string {
  if (seat.control === "ai") return "AI 占位";
  if (seat.userId === null) return "空位";
  return seat.isMe ? "我" : (seat.username ?? seat.userId.slice(0, 8));
}
</script>

<template>
  <section class="room-page">
    <header class="page-head">
      <div class="head-line">
        <el-button text @click="router.push({ name: 'lobby' })">大厅</el-button>
        <h1>{{ room?.gameTitle ?? "房间" }}</h1>
        <el-tag
          v-if="room"
          :type="room.status === 'open' ? 'success' : 'danger'"
          effect="plain"
          size="small"
        >
          {{ room.status === "open" ? (room.playing ? "对局中" : "等开局") : "已关闭" }}
        </el-tag>
        <el-tag v-if="room?.playing" type="warning" effect="plain" size="small"
          >同一时间只有一局</el-tag
        >
        <el-button class="spacer" text :icon="Refresh" :loading="loading" @click="load"
          >刷新</el-button
        >
      </div>
      <p class="page-sub">
        <span class="room-code mono">{{ room?.code ?? "······" }}</span>
        <span class="muted">这是房间号，念给别人就能进来</span>
        <el-button text size="small" :icon="CopyDocument" @click="copyCode">复制</el-button>
        <span class="muted mono" :title="roomId">{{ roomId.slice(0, 8) }}</span>
      </p>
    </header>

    <el-alert
      v-if="loadError"
      class="stack-sm"
      data-testid="room-error"
      type="error"
      :title="loadError"
      :closable="false"
      show-icon
    />
    <p v-if="loadRequestId" class="meta">请求编号 {{ loadRequestId }}</p>
    <el-alert
      v-if="actionError"
      class="stack-sm"
      data-testid="room-action-error"
      type="error"
      :title="actionError"
      :closable="false"
      show-icon
    />
    <p v-if="actionRequestId" class="meta">请求编号 {{ actionRequestId }}</p>

    <div v-if="room" class="layout">
      <section class="panel grow">
        <header class="panel-head">
          <span class="panel-title">席位</span>
          <span class="muted">
            {{ room.humanSeats }} 个真人席位 · {{ room.aiSeats }} 个 AI 占位 · 游戏支持
            {{ seatRange.min }}–{{ seatRange.max }} 席
          </span>
        </header>

        <el-table :data="room.seatPlan" row-key="key" size="small" data-testid="room-seats">
          <el-table-column label="席位" width="90">
            <template #default="{ row }">
              <span class="mono">{{ row.key }}</span>
            </template>
          </el-table-column>
          <el-table-column label="类型" width="100">
            <template #default="{ row }">
              <el-tag :type="row.control === 'ai' ? 'warning' : 'info'" effect="plain" size="small">
                {{ row.control === "ai" ? "AI 占位" : "真人" }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="玩家" min-width="140">
            <template #default="{ row }">
              <span :class="{ muted: row.userId === null }">{{ seatLabel(row) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="准备" width="100">
            <template #default="{ row }">
              <span v-if="row.control === 'ai'" class="muted">不需要</span>
              <el-tag v-else-if="row.ready" type="success" effect="plain" size="small"
                >已准备</el-tag
              >
              <el-tag v-else-if="row.userId" type="info" effect="plain" size="small">未准备</el-tag>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
        </el-table>

        <p class="hint">
          AI
          只是占位：开局那一刻才真正生成席位、人格与词对。真人席位占满并全部准备后，房主才能开局。
        </p>
      </section>

      <section class="panel side">
        <header class="panel-head">
          <span class="panel-title">这一桌</span>
        </header>
        <dl class="facts">
          <div>
            <dt>游戏</dt>
            <dd>
              {{ room.gameTitle }}<span class="muted mono">@{{ room.gameVersion }}</span>
            </dd>
          </div>
          <div v-for="[key, value] in shownVariables" :key="key">
            <dt>{{ key }}</dt>
            <dd>{{ String(value) }}</dd>
          </div>
        </dl>

        <div class="actions">
          <el-button
            v-if="!mySeat && !playing && room.status === 'open'"
            type="primary"
            :loading="busy"
            @click="joinRoom"
          >
            坐下（占一个空位）
          </el-button>
          <template v-else-if="mySeat">
            <el-button type="primary" :loading="busy" :disabled="playing" @click="toggleReady">
              {{ mySeat.ready ? "取消准备" : "我准备好了" }}
            </el-button>
            <el-button :loading="busy" :disabled="playing" @click="leaveRoom"> 离开房间 </el-button>
          </template>
        </div>

        <template v-if="room.isOwner">
          <el-divider />
          <div class="actions">
            <el-button
              type="primary"
              data-testid="room-start"
              :loading="busy"
              :disabled="blockers.length > 0"
              @click="start"
            >
              开局
            </el-button>
            <el-button type="danger" plain :loading="busy" @click="closeOpen = true">
              关闭房间
            </el-button>
          </div>
          <p v-if="blockers.length > 0" class="hint" data-testid="room-blockers">
            还不能开局：{{ blockers.join("；") }}
          </p>
          <p v-else class="hint">条件齐了，开局会生成词对并给 AI 席位生成人格。</p>
        </template>
      </section>

      <section v-if="room.isOwner" class="panel grow">
        <header class="panel-head">
          <span class="panel-title">席位布局</span>
          <span class="muted">没有对局在跑时可以随意改；删掉真人席位会请出坐在上面的人</span>
        </header>
        <div class="plan">
          <div v-for="(seat, index) in draftPlan" :key="index" class="plan-row">
            <el-input v-model="seat.key" class="key-input" />
            <el-select v-model="seat.control" class="control-select">
              <el-option label="真人" value="human" />
              <el-option label="AI 占位" value="ai" />
            </el-select>
            <el-button text type="danger" @click="removeSeat(index)">移除</el-button>
          </div>
          <el-button text :icon="Plus" :disabled="!openForChanges" @click="addSeat"
            >增加席位</el-button
          >
        </div>
        <el-button
          class="stack-sm"
          type="primary"
          plain
          data-testid="room-save-plan"
          :loading="busy"
          :disabled="!planDirty || !openForChanges"
          @click="savePlan"
        >
          保存布局
        </el-button>
      </section>

      <section class="panel grow">
        <header class="panel-head">
          <span class="panel-title">历届对局</span>
          <span class="muted">同一张桌子可以连开多局，同一时间只有一局</span>
        </header>
        <el-table :data="matches" row-key="instanceId" size="small" empty-text="还没有对局">
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="statusTag(row.status)" effect="plain" size="small">
                {{ statusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="进度" width="140">
            <template #default="{ row }">
              <span class="mono">#{{ row.sequence }}</span>
              <span class="muted"> · {{ row.stepId }}</span>
            </template>
          </el-table-column>
          <el-table-column label="开始时间" min-width="170">
            <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button
                size="small"
                :type="isOpen(row.status) ? 'primary' : 'default'"
                @click="router.push({ name: 'match', params: { instanceId: row.instanceId } })"
              >
                {{ isOpen(row.status) ? "进入" : "回看" }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </div>

    <el-skeleton v-else :rows="5" animated />

    <el-dialog v-model="closeOpen" title="关闭房间" width="420px">
      <p class="dialog-note">关闭后房间不再显示在可加入的列表里，历届对局的记录仍然保留。</p>
      <template #footer>
        <el-button @click="closeOpen = false">返回</el-button>
        <el-button type="danger" :loading="busy" @click="confirmClose"> 确认关闭 </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.page-head {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
  margin-bottom: var(--space-lg);
}

.head-line {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.head-line h1 {
  font-size: var(--text-xl);
  font-weight: 600;
}

.spacer {
  margin-left: auto;
}

.page-sub {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  font-size: var(--text-xs);
  color: var(--meta);
}

.room-code {
  font-size: var(--text-md);
  font-weight: 600;
  color: var(--accent);
  letter-spacing: 0.16em;
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  align-items: start;
  gap: var(--space-md);
}

.grow {
  grid-column: 1;
}

.side {
  grid-column: 2;
  grid-row: 1 / span 3;
}

.panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  padding: var(--space-md);
  margin-bottom: var(--space-md);
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
}

.panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-sm);
}

.panel-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--fg-2);
}

.facts {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
  margin: 0;
  font-size: var(--text-sm);
}

.facts div {
  display: flex;
  gap: var(--space-xs);
}

.facts dt {
  flex: 0 0 56px;
  color: var(--meta);
}

.facts dd {
  margin: 0;
  color: var(--fg-2);
  overflow-wrap: anywhere;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
}

.plan {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.plan-row {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.key-input {
  width: 110px;
}

.control-select {
  width: 130px;
}

.hint {
  font-size: var(--text-sm);
  color: var(--muted);
}

.meta {
  font-size: var(--text-xs);
  color: var(--meta);
}

.mono {
  font-family: var(--font-mono);
}

.muted {
  color: var(--muted);
}

.dialog-note {
  font-size: var(--text-base);
  color: var(--fg-2);
}

.stack-sm {
  margin-bottom: var(--space-sm);
}

@media (max-width: 1100px) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .side {
    grid-column: 1;
    grid-row: auto;
  }
}
</style>
