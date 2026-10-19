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

const rooms = ref<RoomSummary[]>([]);
const games = ref<GameCatalogueEntry[]>([]);
const loading = ref(false);
const loadError = ref<string | null>(null);
const loadRequestId = ref<string | null>(null);
const rowBusyId = ref<string | null>(null);
/** A room's matches are read only when somebody opens that room's history. */
const roomMatches = ref<Record<string, MatchSummary[]>>({});
const expanded = ref<Record<string, boolean>>({});

const joinCode = ref("");
const joiningByCode = ref(false);
const joinError = ref<string | null>(null);

const createOpen = ref(false);
const createGame = ref("");
const createSeats = ref<SeatDraft[]>([
  { control: "human" },
  { control: "human" },
  { control: "ai" },
]);
const createValues = ref<Record<string, string>>({});

const selectedGame = computed(() => games.value.find((game) => game.gameId === createGame.value));
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
const derivedCount = computed(
  () => (selectedGame.value?.setup ?? []).filter((field) => field.from !== undefined).length,
);
const seatBounds = computed(() => selectedGame.value?.seats ?? { min: 1, max: 24 });

const creating = ref(false);
const createError = ref<string | null>(null);
const createRequestId = ref<string | null>(null);

watch(createGame, () => {
  createValues.value = {};
});

/** Open rooms first, then the ones I am already in, newest first within each group. */
const sortedRooms = computed(() =>
  [...rooms.value].sort((left, right) => {
    const mine = Number(right.mySeatKeys.length > 0) - Number(left.mySeatKeys.length > 0);
    if (mine !== 0) return mine;
    return right.createdAt.localeCompare(left.createdAt);
  }),
);

function openRoomsOf(gameId: string): number {
  return rooms.value.filter(
    (room) => room.gameId === gameId && room.status === "open" && !room.playing,
  ).length;
}

async function load(): Promise<void> {
  loading.value = true;
  loadError.value = null;
  loadRequestId.value = null;
  try {
    rooms.value = await api.listRooms();
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
    // The catalogue is only needed to create a room; a failure here does not block the list.
  }
});

async function toggleHistory(roomId: string): Promise<void> {
  expanded.value = { ...expanded.value, [roomId]: !expanded.value[roomId] };
  if (!expanded.value[roomId] || roomMatches.value[roomId] !== undefined) return;
  try {
    roomMatches.value = { ...roomMatches.value, [roomId]: await api.listRoomMatches(roomId) };
  } catch (error) {
    loadError.value = uiErrorMessage(error);
    loadRequestId.value = apiRequestId(error);
  }
}

async function join(roomId: string): Promise<void> {
  rowBusyId.value = roomId;
  joinError.value = null;
  try {
    await api.joinRoom(roomId);
    await router.push({ name: "room", params: { roomId } });
  } catch (error) {
    joinError.value = uiErrorMessage(error);
  } finally {
    rowBusyId.value = null;
  }
}

async function joinWithCode(): Promise<void> {
  const code = joinCode.value.trim().toUpperCase();
  if (code.length !== 6) {
    joinError.value = "房间号是 6 位。";
    return;
  }
  joiningByCode.value = true;
  joinError.value = null;
  try {
    const room = await api.joinRoomByCode(code);
    await router.push({ name: "room", params: { roomId: room.roomId } });
  } catch (error) {
    joinError.value = uiErrorMessage(error);
  } finally {
    joiningByCode.value = false;
  }
}

function openCreate(gameId: string): void {
  createGame.value = gameId;
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
</script>

<template>
  <section class="lobby">
    <header class="page-head">
      <h1>游戏大厅</h1>
      <p class="page-sub">选一款游戏开一桌，或者用房间号加入朋友的桌子。</p>
    </header>

    <el-alert
      v-if="loadError"
      class="stack-sm"
      data-testid="lobby-error"
      type="error"
      :title="loadError"
      :closable="false"
      show-icon
    />
    <el-alert
      v-if="joinError"
      class="stack-sm"
      data-testid="join-error"
      type="error"
      :title="joinError"
      :closable="false"
      show-icon
    />
    <p v-if="loadRequestId" class="meta">请求编号 {{ loadRequestId }}</p>

    <div class="games">
      <article v-for="game in games" :key="game.gameId" class="game-card">
        <span class="game-mark" aria-hidden="true">[AI]</span>
        <h2 class="game-name">{{ game.title }}</h2>
        <p class="game-meta">
          {{ game.seats.min }}–{{ game.seats.max }} 席 ·
          <span v-if="openRoomsOf(game.gameId) > 0">{{ openRoomsOf(game.gameId) }} 桌在等人</span>
          <span v-else>暂时没有空桌</span>
        </p>
        <el-button type="primary" :icon="Plus" @click="openCreate(game.gameId)">创建房间</el-button>
      </article>

      <article class="game-card join-card">
        <span class="game-mark" aria-hidden="true">#</span>
        <h2 class="game-name">用房间号加入</h2>
        <p class="game-meta">6 位房间号，不含 0/O/1/I</p>
        <div class="join-row">
          <el-input
            v-model="joinCode"
            maxlength="6"
            placeholder="例如 3532E3"
            class="code-input mono"
            @keyup.enter="joinWithCode"
          />
          <el-button :loading="joiningByCode" @click="joinWithCode">加入</el-button>
        </div>
      </article>
    </div>

    <section class="panel" data-testid="room-list">
      <header class="panel-head">
        <span class="panel-title">房间</span>
        <el-button text :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
      </header>

      <el-empty
        v-if="sortedRooms.length === 0"
        :image-size="70"
        description="还没有房间，开一桌试试"
      />

      <div class="room-cards">
        <article v-for="room in sortedRooms" :key="room.roomId" class="room-card">
          <header class="room-head">
            <span class="room-code mono" :title="room.roomId">{{ room.code }}</span>
            <span class="room-game">{{ room.gameTitle }}</span>
            <el-tag v-if="room.status !== 'open'" type="danger" effect="plain" size="small"
              >已关闭</el-tag
            >
            <el-tag v-else-if="room.playing" type="warning" effect="plain" size="small"
              >对局中</el-tag
            >
            <el-tag v-else type="success" effect="plain" size="small">等开局</el-tag>
            <span class="room-seats muted">
              {{ room.seats }} 席（{{ room.humanSeats }} 真人 + {{ room.aiSeats }} AI）
            </span>
            <span v-if="room.mySeatKeys.length > 0" class="room-mine mono">
              我在 {{ room.mySeatKeys.join("、") }}
            </span>
          </header>

          <p class="room-line">
            <span v-if="room.humanSeats > 0">已坐 {{ room.takenSeats }}/{{ room.humanSeats }}</span>
            <span v-if="room.readySeats > 0"> · 已准备 {{ room.readySeats }}</span>
            <span v-if="room.status === 'open' && !room.playing" class="muted">
              · 房主开局时才生成对局与 AI 席位
            </span>
          </p>

          <div class="room-actions">
            <el-button
              v-if="
                room.mySeatKeys.length === 0 &&
                room.status === 'open' &&
                !room.playing &&
                room.takenSeats < room.humanSeats
              "
              type="primary"
              :loading="rowBusyId === room.roomId"
              size="small"
              @click="join(room.roomId)"
            >
              坐下
            </el-button>
            <el-button
              size="small"
              @click="router.push({ name: 'room', params: { roomId: room.roomId } })"
            >
              {{ room.mySeatKeys.length > 0 ? "进入房间" : "查看" }}
            </el-button>
            <el-button
              v-if="room.currentInstanceId"
              text
              size="small"
              @click="toggleHistory(room.roomId)"
            >
              {{ expanded[room.roomId] ? "收起对局" : "这一桌的对局" }}
            </el-button>
          </div>

          <!-- A room's matches belong to the room: they are shown here, not in a list of their own. -->
          <ul v-if="room.currentInstanceId" class="room-matches">
            <li v-if="room.playing" class="room-match">
              <el-tag type="warning" effect="plain" size="small">进行中</el-tag>
              <el-button
                text
                size="small"
                @click="
                  router.push({ name: 'match', params: { instanceId: room.currentInstanceId } })
                "
              >
                进入这一局
              </el-button>
            </li>
            <template v-else-if="expanded[room.roomId]">
              <li
                v-for="match in roomMatches[room.roomId] ?? []"
                :key="match.instanceId"
                class="room-match"
              >
                <el-tag :type="statusTag(match.status)" effect="plain" size="small">
                  {{ statusLabel(match.status) }}
                </el-tag>
                <span class="muted mono">#{{ match.sequence }} · {{ match.stepId }}</span>
                <span class="muted">{{ formatTime(match.createdAt) }}</span>
                <el-button
                  text
                  size="small"
                  @click="router.push({ name: 'match', params: { instanceId: match.instanceId } })"
                >
                  回看
                </el-button>
              </li>
            </template>
            <li v-else class="room-match muted">上一局已结束，可以「这一桌的对局」看记录</li>
          </ul>
        </article>
      </div>
    </section>

    <el-dialog v-model="createOpen" title="创建房间" width="620px">
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
      </el-form>

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

.games {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.game-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-2xs);
  padding: var(--space-md);
  background: var(--surface-glass);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  backdrop-filter: blur(8px);
}

.game-mark {
  font-family: var(--font-mono);
  font-size: var(--text-lg);
  color: var(--accent);
}

.game-name {
  font-size: var(--text-lg);
  font-weight: 600;
}

.game-meta {
  font-size: var(--text-sm);
  color: var(--muted);
}

.join-row {
  display: flex;
  gap: var(--space-xs);
  width: 100%;
  margin-top: var(--space-2xs);
}

.code-input {
  width: 140px;
}

.code-input :deep(input) {
  letter-spacing: 0.18em;
  text-transform: uppercase;
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
  align-items: center;
  justify-content: space-between;
}

.panel-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--fg-2);
}

.room-cards {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.room-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
  padding: var(--space-sm) var(--space-md);
  background: var(--surface-warm);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
}

.room-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-xs);
}

.room-code {
  font-size: var(--text-md);
  font-weight: 600;
  color: var(--accent);
  letter-spacing: 0.16em;
}

.room-game {
  font-weight: 600;
}

.room-seats,
.room-line {
  font-size: var(--text-sm);
  color: var(--fg-2);
}

.room-mine {
  font-size: var(--text-sm);
  color: var(--accent);
}

.room-line {
  margin: 0;
}

.room-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
}

.room-matches {
  display: flex;
  flex-direction: column;
  gap: var(--space-3xs);
  margin: 0;
  padding: var(--space-2xs) 0 0;
  list-style: none;
  border-top: 1px dashed var(--border-soft);
}

.room-match {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  font-size: var(--text-sm);
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

.seat-note {
  flex: 1;
  font-size: var(--text-sm);
}

.word-row {
  display: flex;
  gap: var(--space-xs);
  width: 100%;
}

.word-input {
  flex: 1;
}

.full {
  width: 100%;
}

.category-select {
  width: 200px;
}

.hint {
  font-size: var(--text-sm);
  color: var(--muted);
}

.hint.inline {
  margin: 0 0 0 var(--space-xs);
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

.stack-sm {
  margin-bottom: var(--space-sm);
}
</style>
