<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { Refresh } from "@element-plus/icons-vue";
import { api, apiRequestId, type GameCatalogueEntry, type MatchSummary } from "../services/api";
import { uiErrorMessage } from "../services/messages";
import { formatTime, isOpen, statusLabel, statusTag } from "../services/match-labels";

const router = useRouter();

const matches = ref<MatchSummary[]>([]);
const games = ref<GameCatalogueEntry[]>([]);

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
const loading = ref(false);
const loadError = ref<string | null>(null);
const loadRequestId = ref<string | null>(null);

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
    games.value = await api.listGames();
  } catch (error) {
    loadError.value = uiErrorMessage(error);
    loadRequestId.value = apiRequestId(error);
  } finally {
    loading.value = false;
  }
}

onMounted(load);

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
  <section class="matches-admin">
    <header class="page-head">
      <h1>对局运维</h1>
      <p class="page-sub">
        平台层的对局生命周期：暂停、恢复、取消。改的是状态并写审计，不写成游戏事件，也不进对局记录。
      </p>
    </header>

    <el-card class="panel" shadow="never">
      <template #header>
        <div class="panel-head">
          <span class="panel-title">全部对局</span>
          <el-button text :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
        </div>
      </template>

      <el-alert
        v-if="loadError"
        class="stack-sm"
        data-testid="admin-matches-error"
        type="error"
        :title="loadError"
        :closable="false"
        show-icon
      />
      <p v-if="loadRequestId" class="meta">请求编号 {{ loadRequestId }}</p>

      <el-alert
        v-if="rowError"
        class="stack-sm"
        data-testid="admin-matches-row-error"
        type="error"
        :title="rowError"
        :closable="false"
        show-icon
      />
      <p v-if="rowRequestId" class="meta">请求编号 {{ rowRequestId }}</p>

      <el-table v-loading="loading" :data="matches" empty-text="还没有对局" row-key="instanceId">
        <el-table-column label="对局" min-width="300">
          <template #default="{ row }">
            <div class="mono instance">{{ row.instanceId }}</div>
            <div class="muted small">{{ gameTitle(row.gameId) }}@{{ row.gameVersion }}</div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" effect="plain" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="150">
          <template #default="{ row }">
            <span class="mono">#{{ row.sequence }}</span>
            <span class="muted"> · {{ stepName(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="170">
          <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" min-width="300">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button
                size="small"
                @click="router.push({ name: 'match', params: { instanceId: row.instanceId } })"
              >
                查看
              </el-button>
              <el-button
                size="small"
                :disabled="!isOpen(row.status) || rowBusyId === row.instanceId"
                @click="setStatus(row.instanceId, 'paused')"
              >
                暂停
              </el-button>
              <el-button
                size="small"
                :disabled="row.status !== 'paused' || rowBusyId === row.instanceId"
                @click="setStatus(row.instanceId, 'running')"
              >
                恢复
              </el-button>
              <el-button
                size="small"
                type="danger"
                plain
                :disabled="row.status === 'completed' || row.status === 'cancelled'"
                @click="cancelTarget = row"
              >
                取消
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <p class="hint">
        只有管理员进得来这一页。管理员在别处就是一个普通玩家：在对局里占席位、能旁观，看不到这一页的按钮。
      </p>
    </el-card>

    <el-dialog
      :model-value="cancelTarget !== null"
      title="取消对局"
      width="460px"
      @update:model-value="cancelTarget = null"
    >
      <p class="dialog-note">
        取消后该对局不再接受输入，记录与旁观入口保留。这是一次平台运维操作，会写入审计，不会写成游戏事件。
      </p>
      <p class="mono instance">{{ cancelTarget?.instanceId }}</p>
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

.panel-title {
  font-size: var(--text-base);
  font-weight: 600;
}

.row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2xs);
}

.instance {
  font-size: var(--text-sm);
  word-break: break-all;
}

.small {
  font-size: var(--text-xs);
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

.field-error {
  margin-top: var(--space-xs);
  font-size: var(--text-sm);
  color: var(--danger);
}

.stack-sm {
  margin-bottom: var(--space-sm);
}
</style>
