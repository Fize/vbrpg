<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { Plus, Refresh } from "@element-plus/icons-vue";
import { api, apiRequestId, type GameCatalogueEntry, type MatchSummary } from "../services/api";
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
  username: string;
}

const router = useRouter();
const user = computed(() => sessionState.user);
const isAdmin = computed(() => user.value?.role === "admin");
const roleLabel = computed(() => (isAdmin.value ? "管理员" : "普通用户"));

const matches = ref<MatchSummary[]>([]);
const games = ref<GameCatalogueEntry[]>([]);
const loading = ref(false);
const loadError = ref<string | null>(null);
const loadRequestId = ref<string | null>(null);

const createOpen = ref(false);
const createGame = ref("");
const createSeats = ref<SeatDraft[]>([
  { control: "human", username: "" },
  { control: "human", username: "" },
  { control: "ai", username: "" },
]);
/** Whether the table sees each other's personas; the platform deals one to every seat anyway. */
const createPersonaPublic = ref(false);
/** Whatever the selected game asks for at creation, keyed by the game's own field names. */
const createValues = ref<Record<string, string>>({});

const selectedGame = computed(() => games.value.find((game) => game.gameId === createGame.value));
/** Fields with `from` are filled by the platform's model, so the creator is never asked for them. */
const setupFields = computed(() =>
  (selectedGame.value?.setup ?? []).filter((field) => field.from === undefined),
);
const derivedCount = computed(
  () => (selectedGame.value?.setup ?? []).filter((field) => field.from !== undefined).length,
);

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
    // The catalogue is only needed to create a match; a failure here does not block the list.
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
  createSeats.value.push({ control: "human", username: "" });
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
  if (createSeats.value.length === 0) {
    createError.value = "至少需要一个席位。";
    return;
  }
  const variables: Record<string, string> = {};
  for (const field of setupFields.value) {
    const value = (createValues.value[field.name] ?? "").trim();
    if (value.length === 0) {
      createError.value = `请填写「${field.label}」。`;
      return;
    }
    variables[field.name] = value;
  }

  creating.value = true;
  try {
    const created = await api.createMatch({
      gameId: createGame.value,
      personaPublic: createPersonaPublic.value,
      ...(setupFields.value.length === 0 ? {} : { variables }),
      seats: createSeats.value.map((seat, index) => ({
        key: `s${index + 1}`,
        control: seat.control,
        ...(seat.control === "human" && seat.username.trim().length > 0
          ? { username: seat.username.trim() }
          : {}),
      })),
    });
    createOpen.value = false;
    await router.push({ name: "match", params: { instanceId: created.instanceId } });
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
      <h1>大厅</h1>
      <p class="page-sub">
        对局在这里开；进房间后按当前等待点行动。本阶段不做实时推送，房间页用刷新取最新记录。
      </p>
    </header>

    <el-card class="panel" shadow="never">
      <template #header>
        <div class="panel-head">
          <span class="panel-title">对局列表</span>
          <div class="panel-actions">
            <el-button text :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
            <el-button type="primary" :icon="Plus" @click="openCreate">新建对局</el-button>
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

    <el-dialog v-model="createOpen" title="新建对局" width="620px">
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
              <el-input
                v-if="seat.control === 'human'"
                v-model="seat.username"
                class="seat-user"
                placeholder="留空表示自己占该席位"
              />
              <span v-else class="seat-note muted">由平台按供应商默认模型驱动</span>
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

      <el-form-item v-for="field in setupFields" :key="field.name" :label="field.label">
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
      <p v-if="derivedCount > 0" class="hint">
        开局时由平台的模型按分类给出一对词，直接发到席位上，不会先显示给别人看。
      </p>

      <el-form-item label="公开人格">
        <el-switch v-model="createPersonaPublic" />
        <span class="hint inline">
          打开后全桌能看到彼此的职业、性格与说话风格；性别始终公开，MBTI 始终只有自己可见。
        </span>
      </el-form-item>
      <p class="hint">席位数量与角色由游戏在开局时判定；不符合规则的开局会被游戏拒绝并给出原因。</p>
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
        <el-button type="primary" :loading="creating" @click="submitCreate">开局</el-button>
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
  width: 160px;
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
