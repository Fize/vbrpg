<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { Plus, Refresh } from "@element-plus/icons-vue";
import {
  api,
  apiRequestId,
  type GameCatalogueEntry,
  type MatchSummary,
  type RoomSummary,
} from "../services/api";
import { uiErrorMessage } from "../services/messages";
import { formatTime, statusLabel, statusTag } from "../services/match-labels";
import { sessionState } from "../stores/session";

/** Suggestions for the category field; the creator can type anything else. */
const CATEGORIES = [
  "水果",
  "食物",
  "动物",
  "日用品",
  "职业",
  "交通工具",
  "影视作品",
  "地方小吃",
  "运动",
  "电子产品",
];

interface SeatDraft {
  control: "human" | "ai";
}

const router = useRouter();
const user = computed(() => sessionState.user);
const isAdmin = computed(() => user.value?.role === "admin");
const roleLabel = computed(() => (isAdmin.value ? "管理员" : "普通用户"));

const rooms = ref<RoomSummary[]>([]);
const matches = ref<MatchSummary[]>([]);
const games = ref<GameCatalogueEntry[]>([]);
const loading = ref(false);
const loadError = ref<string | null>(null);
const loadRequestId = ref<string | null>(null);
const rowBusyId = ref<string | null>(null);

const createOpen = ref(false);
const createGame = ref("");
const createSeats = ref<SeatDraft[]>([
  { control: "human" },
  { control: "human" },
  { control: "ai" },
]);
/** Whether the table sees each other's personas; the platform deals one to every seat anyway. */
const createPersonaPublic = ref(false);
/** Whatever the selected game asks for at creation, keyed by the game's own field names. */
const createValues = ref<Record<string, string>>({});

const selectedGame = computed(() => games.value.find((game) => game.gameId === createGame.value));
const derivedCount = computed(
  () => (selectedGame.value?.setup ?? []).filter((field) => field.from !== undefined).length,
);
/** A game may offer two ways to get its words: type both, or name a category and let the model do it. */
const wordFields = computed(() =>
  (selectedGame.value?.setup ?? []).filter(
    (field) => field.from === undefined && field.kind === "word",
  ),
);
const askedFields = computed(() =>
  (selectedGame.value?.setup ?? []).filter(
    (field) => field.from === undefined && field.kind !== "word",
  ),
);
const seatBounds = computed(() => selectedGame.value?.seats ?? { min: 1, max: 24 });

watch(createGame, () => {
  createValues.value = {};
});

const creating = ref(false);
const createError = ref<string | null>(null);
const createRequestId = ref<string | null>(null);

async function load(): Promise<void> {
  loading.value = true;
  loadError.value = null;
  loadRequestId.value = null;
  try {
    rooms.value = await api.listRooms();
    matches.value = await api.listMatches();
  } catch (error) {
    loadError.value = uiErrorMessage(error);
    loadRequestId.value = apiRequestId(error);
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  await load();
  try {
    games.value = await api.listGames();
  } catch {
    // The catalogue is only needed to create a room; a failure here does not block the lists.
  }
});

function entryOf(gameId: string): GameCatalogueEntry | undefined {
  return games.value.find((game) => game.gameId === gameId);
}

/** The catalogue names the games and their steps; an unknown word stays as the API sent it. */
function gameTitle(gameId: string): string {
  return entryOf(gameId)?.title ?? gameId;
}

function stepName(row: { gameId: string; stepId: string }): string {
  return entryOf(row.gameId)?.steps[row.stepId] ?? row.stepId;
}

function openCreate(): void {
  createGame.value = games.value[0]?.gameId ?? "";
  createError.value = null;
  createRequestId.value = null;
  createOpen.value = true;
}

function addSeat(): void {
  if (createSeats.value.length >= seatBounds.value.max) return;
  createSeats.value.push({ control: "human" });
}

function removeSeat(index: number): void {
  createSeats.value.splice(index, 1);
}

async function submitCreate(): Promise<void> {
  createError.value = null;
  createRequestId.value = null;
  if (createGame.value.length === 0) {
    createError.value = "请选择游戏。";
    return;
  }
  const bounds = seatBounds.value;
  if (createSeats.value.length < bounds.min || createSeats.value.length > bounds.max) {
    createError.value = `${selectedGame.value?.title ?? "这个游戏"} 需要 ${bounds.min}–${bounds.max} 个席位。`;
    return;
  }
  if (createSeats.value.every((seat) => seat.control === "ai")) {
    createError.value = "至少要有一个真人席位。";
    return;
  }

  const variables: Record<string, string> = {};
  const filled = (name: string): string => (createValues.value[name] ?? "").trim();

  // Words are all-or-nothing: both typed, or neither (the category then drives the model).
  const typedWords = wordFields.value.filter((field) => filled(field.name) !== "");
  if (typedWords.length > 0 && typedWords.length < wordFields.value.length) {
    createError.value = "两个词要么都填，要么都留空（留空就按分类生成）。";
    return;
  }
  for (const field of wordFields.value) {
    if (typedWords.length > 0) variables[field.name] = filled(field.name);
  }
  if (typedWords.length === 0) {
    for (const field of askedFields.value) {
      const value = filled(field.name);
      if (value.length === 0) {
        createError.value = `请填写「${field.label}」或自己填两个词。`;
        return;
      }
      variables[field.name] = value;
    }
  }

  creating.value = true;
  try {
    const room = await api.createRoom({
      gameId: createGame.value,
      personaPublic: createPersonaPublic.value,
      ...(Object.keys(variables).length === 0 ? {} : { variables }),
      seats: createSeats.value.map((seat, index) => ({
        key: `s${index + 1}`,
        control: seat.control,
      })),
    });
    createOpen.value = false;
    await router.push({ name: "room", params: { roomId: room.roomId } });
  } catch (error) {
    createError.value = uiErrorMessage(error);
    createRequestId.value = apiRequestId(error);
  } finally {
    creating.value = false;
  }
}

/** Kept for the room list below: taking a seat from the lobby. */
async function join(roomId: string): Promise<void> {
  rowBusyId.value = roomId;
  loadError.value = null;
  try {
    await api.joinRoom(roomId);
    await router.push({ name: "room", params: { roomId } });
  } catch (error) {
    loadError.value = uiErrorMessage(error);
    loadRequestId.value = apiRequestId(error);
  } finally {
    rowBusyId.value = null;
  }
}
</script>

<template>
  <section class="lobby">
    <header class="page-head">
      <h1>大厅</h1>
      <p class="page-sub">
        对局在这里开；进房间后按当前等待点行动。本阶段不做实时推送，房间页用刷新取最新记录。
      </p>
    </header>

    <el-card class="panel" shadow="never" data-testid="room-list">
      <template #header>
        <div class="panel-head">
          <span class="panel-title">房间</span>
          <span class="muted">先有房间，人进来准备，房主开局才生成对局与 AI 席位</span>
        </div>
      </template>

      <el-table :data="rooms" row-key="roomId" size="small" empty-text="还没有房间">
        <el-table-column label="游戏" min-width="160">
          <template #default="{ row }">
            {{ gameTitle(row.gameId) }}
            <span class="muted mono">@{{ row.gameVersion }}</span>
          </template>
        </el-table-column>
        <el-table-column label="席位" width="150">
          <template #default="{ row }">
            <span class="mono">{{ row.humanSeats }}</span> 真人
            <span class="muted"> · </span>
            <span class="mono">{{ row.aiSeats }}</span> AI 占位
          </template>
        </el-table-column>
        <el-table-column label="人数" width="180">
          <template #default="{ row }">
            已坐 {{ row.takenSeats }}/{{ row.humanSeats }} · 已准备 {{ row.readySeats }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="130">
          <template #default="{ row }">
            <el-tag v-if="row.status !== 'open'" type="danger" effect="plain" size="small"
              >已关闭</el-tag
            >
            <el-tag v-else-if="row.playing" type="warning" effect="plain" size="small"
              >对局中</el-tag
            >
            <el-tag v-else type="success" effect="plain" size="small">等开局</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="我的席位" width="110">
          <template #default="{ row }">
            <span v-if="row.mySeatKeys.length > 0" class="mono">{{
              row.mySeatKeys.join("、")
            }}</span>
            <span v-else class="muted">未加入</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="180">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button
                v-if="
                  row.mySeatKeys.length === 0 &&
                  row.status === 'open' &&
                  !row.playing &&
                  row.takenSeats < row.humanSeats
                "
                type="primary"
                :loading="rowBusyId === row.roomId"
                size="small"
                @click="join(row.roomId)"
              >
                坐下
              </el-button>
              <el-button
                size="small"
                @click="router.push({ name: 'room', params: { roomId: row.roomId } })"
              >
                {{ row.mySeatKeys.length > 0 ? "进入房间" : "查看" }}
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <p class="hint">开放中的房间谁都能坐下；同一张桌子可以连开多局，同一时间只有一局在跑。</p>
    </el-card>

    <el-card class="panel" shadow="never">
      <template #header>
        <div class="panel-head">
          <span class="panel-title">对局</span>
          <div class="panel-actions">
            <el-button text :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
            <el-button type="primary" :icon="Plus" @click="openCreate">新建房间</el-button>
          </div>
        </div>
      </template>

      <el-alert
        v-if="loadError"
        class="stack-sm"
        data-testid="lobby-error"
        type="error"
        :title="loadError"
        :closable="false"
        show-icon
      />
      <p v-if="loadRequestId" class="meta">请求编号 {{ loadRequestId }}</p>

      <el-table v-loading="loading" :data="matches" empty-text="还没有对局" row-key="instanceId">
        <el-table-column label="游戏" min-width="160">
          <template #default="{ row }">
            {{ gameTitle(row.gameId) }}
            <span class="muted mono">@{{ row.gameVersion }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" effect="plain" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="我的席位" width="130">
          <template #default="{ row }">
            <el-tag v-if="row.mySeatKeys.length > 0" type="primary" effect="plain" size="small">
              {{ row.mySeatKeys.join("、") }}
            </el-tag>
            <span v-else class="muted">旁观</span>
          </template>
        </el-table-column>
        <el-table-column label="进度" min-width="150">
          <template #default="{ row }">
            <span class="mono">#{{ row.sequence }}</span>
            <span class="muted"> · {{ stepName(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="170">
          <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              :type="row.mySeatKeys.length > 0 ? 'primary' : 'default'"
              :plain="row.mySeatKeys.length === 0"
              size="small"
              @click="router.push({ name: 'match', params: { instanceId: row.instanceId } })"
            >
              {{ row.mySeatKeys.length > 0 ? "进入房间" : "旁观" }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <p class="hint">
        大厅里的每一局都能进：占席位的进去行动，没有席位的进去旁观，看到的是同一份记录。
        <template v-if="isAdmin"> 对局的暂停、恢复与取消在「对局运维」里，不在这里。 </template>
      </p>
    </el-card>

    <el-card class="panel" shadow="never">
      <template #header>
        <span class="panel-title">我的账号</span>
      </template>

      <el-descriptions v-if="user" :column="2" border>
        <el-descriptions-item label="用户名">{{ user.username }}</el-descriptions-item>
        <el-descriptions-item label="角色">
          <el-tag :type="isAdmin ? 'warning' : 'info'" effect="plain" size="small">
            {{ roleLabel }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="账号状态">
          <el-tag :type="user.active ? 'success' : 'danger'" effect="plain" size="small">
            {{ user.active ? "正常" : "已停用" }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ formatTime(user.createdAt) }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-dialog v-model="createOpen" title="新建房间" width="620px">
      <el-form label-position="top">
        <el-form-item label="游戏">
          <el-select v-model="createGame" class="full" placeholder="选择游戏">
            <el-option
              v-for="game in games"
              :key="game.gameId"
              :label="`${game.title}（${game.version}）`"
              :value="game.gameId"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="席位">
          <div class="seat-editor">
            <div v-for="(seat, index) in createSeats" :key="index" class="seat-row">
              <span class="seat-index mono">s{{ index + 1 }}</span>
              <el-select v-model="seat.control" class="seat-control">
                <el-option label="真人" value="human" />
                <el-option label="AI" value="ai" />
              </el-select>
              <span v-if="seat.control === 'human'" class="seat-note muted">
                开局前由真人坐下（房主先坐）
              </span>
              <span v-else class="seat-note muted">开局时才生成，现在是占位</span>
              <el-button
                text
                type="danger"
                :disabled="createSeats.length <= 1"
                @click="removeSeat(index)"
              >
                移除
              </el-button>
            </div>
            <el-button text :icon="Plus" @click="addSeat">增加席位</el-button>
          </div>
        </el-form-item>
      </el-form>

      <el-form-item v-for="field in askedFields" :key="field.name" :label="field.label">
        <el-select
          v-if="field.kind === 'category'"
          v-model="createValues[field.name]"
          class="category-select"
          filterable
          allow-create
          default-first-option
          :placeholder="field.description"
        >
          <el-option v-for="name in CATEGORIES" :key="name" :label="name" :value="name" />
        </el-select>
        <el-input
          v-else
          :model-value="createValues[field.name] ?? ''"
          :placeholder="field.description"
          @update:model-value="
            (value: string) => (createValues = { ...createValues, [field.name]: value })
          "
        />
      </el-form-item>
      <el-form-item v-if="wordFields.length > 0" label="自己出词（可选）">
        <div class="word-row">
          <el-input
            v-for="field in wordFields"
            :key="field.name"
            class="word-input"
            :model-value="createValues[field.name] ?? ''"
            :placeholder="field.label"
            @update:model-value="
              (value: string) => (createValues = { ...createValues, [field.name]: value })
            "
          />
        </div>
      </el-form-item>

      <p v-if="derivedCount > 0" class="hint" data-testid="word-source">
        开局时由平台的模型按分类给出一对词，直接发到席位上，不会先显示给别人看。
        <template v-if="wordFields.length > 0">
          也可以自己填这两个词（都填就用自己的；自己填的会被全桌看到，所以只建议旁观者来填）。
        </template>
      </p>

      <el-form-item label="公开人格">
        <el-switch v-model="createPersonaPublic" />
        <span class="hint inline">
          打开后全桌能看到彼此的职业、性格与说话风格；性别始终公开，MBTI 始终只有自己可见。
        </span>
      </el-form-item>
      <p class="hint">
        房间先存在：选好游戏与席位布局，人进房准备，房主开局时才生成对局与 AI 席位。 席位数量必须是
        {{ seatBounds.min }}–{{ seatBounds.max }} 个。
      </p>
      <el-alert
        v-if="createError"
        class="stack-sm"
        data-testid="create-match-error"
        type="error"
        :title="createError"
        :closable="false"
        show-icon
      />
      <p v-if="createRequestId" class="meta">请求编号 {{ createRequestId }}</p>

      <template #footer>
        <el-button @click="createOpen = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">建房</el-button>
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

.page-sub {
  font-size: var(--text-base);
  color: var(--muted);
}

.panel {
  margin-bottom: var(--space-md);
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-actions {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.panel-title {
  font-size: var(--text-base);
  font-weight: 600;
}

.seat-editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  width: 100%;
}

.seat-row {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.seat-index {
  width: 32px;
  color: var(--muted);
}

.seat-control {
  width: 110px;
}

.seat-user {
  flex: 1;
}

.seat-note {
  flex: 1;
  font-size: var(--text-sm);
}

.full {
  width: 100%;
}

.row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2xs);
}

.hint.inline {
  margin: 0 0 0 var(--space-xs);
  font-size: var(--text-sm);
  color: var(--muted);
}

.pair-row {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  width: 100%;
}

.category-select {
  width: 200px;
}

.word-row {
  display: flex;
  gap: var(--space-xs);
  width: 100%;
}

.word-input {
  flex: 1;
}

.field-error {
  margin-top: var(--space-2xs);
  font-size: var(--text-sm);
  color: var(--danger);
}

.mono {
  font-family: var(--font-mono);
}

.muted {
  color: var(--muted);
}

.hint {
  margin-top: var(--space-sm);
  font-size: var(--text-sm);
  color: var(--muted);
}

.meta {
  font-size: var(--text-xs);
  color: var(--meta);
}

.stack-sm {
  margin-bottom: var(--space-sm);
}
</style>
