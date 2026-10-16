<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { Plus, Refresh } from "@element-plus/icons-vue";
import { api, apiRequestId, type GameCatalogueEntry, type MatchSummary } from "../services/api";
import { uiErrorMessage } from "../services/messages";
import { formatTime, isOpen, statusLabel, statusTag } from "../services/match-labels";
import { sessionState } from "../stores/session";

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
const creating = ref(false);
const createError = ref<string | null>(null);
const createRequestId = ref<string | null>(null);

const rowBusyId = ref<string | null>(null);
const rowError = ref<string | null>(null);
const rowRequestId = ref<string | null>(null);

const cancelTarget = ref<MatchSummary | null>(null);
const cancelError = ref<string | null>(null);
const cancelling = ref(false);

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

  creating.value = true;
  try {
    const created = await api.createMatch({
      gameId: createGame.value,
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

async function setStatus(instanceId: string, status: "running" | "paused"): Promise<void> {
  rowBusyId.value = instanceId;
  rowError.value = null;
  rowRequestId.value = null;
  try {
    await api.setMatchStatus(instanceId, status);
    await load();
  } catch (error) {
    rowError.value = uiErrorMessage(error);
    rowRequestId.value = apiRequestId(error);
  } finally {
    rowBusyId.value = null;
  }
}

async function confirmCancel(): Promise<void> {
  const target = cancelTarget.value;
  if (!target) return;
  cancelling.value = true;
  cancelError.value = null;
  try {
    await api.setMatchStatus(target.instanceId, "cancelled");
    cancelTarget.value = null;
    await load();
  } catch (error) {
    cancelError.value = uiErrorMessage(error);
  } finally {
    cancelling.value = false;
  }
}
</script>

<template>
  <section class="lobby">
    <header class="page-head">
      <h1>大厅</h1>
      <p class="page-sub">对局在这里开；进房间后按当前等待点行动。本阶段不做实时推送，房间页用刷新取最新记录。</p>
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

      <el-alert
        v-if="rowError"
        class="stack-sm"
        data-testid="lobby-row-error"
        type="error"
        :title="rowError"
        :closable="false"
        show-icon
      />

      <el-table v-loading="loading" :data="matches" empty-text="还没有对局" row-key="instanceId">
        <el-table-column label="游戏" min-width="140">
          <template #default="{ row }">{{ row.gameId }}@{{ row.gameVersion }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" effect="plain" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" min-width="160">
          <template #default="{ row }">
            <span class="mono">#{{ row.sequence }}</span>
            <span class="muted"> · {{ row.stepId }}</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="170">
          <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" min-width="280">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button
                type="primary"
                plain
                size="small"
                @click="router.push({ name: 'match', params: { instanceId: row.instanceId } })"
              >
                进入房间
              </el-button>
              <template v-if="isAdmin">
                <el-button
                  v-if="isOpen(row.status)"
                  size="small"
                  :disabled="rowBusyId === row.instanceId"
                  @click="setStatus(row.instanceId, 'paused')"
                >
                  暂停
                </el-button>
                <el-button
                  v-if="row.status === 'paused'"
                  size="small"
                  :disabled="rowBusyId === row.instanceId"
                  @click="setStatus(row.instanceId, 'running')"
                >
                  恢复
                </el-button>
                <el-button
                  v-if="row.status !== 'cancelled' && row.status !== 'completed'"
                  type="danger"
                  plain
                  size="small"
                  :disabled="rowBusyId === row.instanceId"
                  @click="cancelTarget = row"
                >
                  取消
                </el-button>
              </template>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <p class="hint">
        {{ isAdmin ? "管理员看到全部对局；其他账号只看到自己占席位的对局。" : "只显示你占席位的对局。" }}
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
              :label="`${game.gameId}@${game.version}`"
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
              <el-button text type="danger" :disabled="createSeats.length <= 1" @click="removeSeat(index)">
                移除
              </el-button>
            </div>
            <el-button text :icon="Plus" @click="addSeat">增加席位</el-button>
          </div>
        </el-form-item>
      </el-form>

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

    <el-dialog
      :model-value="cancelTarget !== null"
      title="取消对局"
      width="420px"
      @update:model-value="cancelTarget = null"
    >
      <p class="dialog-note">
        取消后该对局不再接受输入，记录保留。这是一次平台运维操作，会写入审计，不会写成游戏事件。
      </p>
      <p v-if="cancelError" class="field-error">{{ cancelError }}</p>
      <template #footer>
        <el-button @click="cancelTarget = null">返回</el-button>
        <el-button type="danger" :loading="cancelling" @click="confirmCancel">确认取消</el-button>
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

.row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2xs);
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

.dialog-note {
  font-size: var(--text-base);
  color: var(--fg-2);
}

.field-error {
  margin-top: var(--space-xs);
  font-size: var(--text-sm);
  color: var(--danger);
}

.stack-sm {
  margin-bottom: var(--space-sm);
}
</style>
