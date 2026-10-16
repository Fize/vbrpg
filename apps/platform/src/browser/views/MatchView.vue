<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ArrowLeft, Refresh } from "@element-plus/icons-vue";
import { api, apiRequestId, type GameAction, type MatchRecordRow } from "../services/api";
import { uiErrorMessage } from "../services/messages";
import {
  eventLabel,
  formatTime,
  isOpen,
  payloadText,
  statusLabel,
  statusTag,
} from "../services/match-labels";
import { sessionState } from "../stores/session";

type SeatArg = { name: string; description: string; kind: "seat" | null };

const route = useRoute();
const instanceId = computed(() => String(route.params["instanceId"] ?? ""));

const detail = ref<Awaited<ReturnType<typeof api.readMatch>> | null>(null);
const loading = ref(false);
const loadError = ref<string | null>(null);
const loadRequestId = ref<string | null>(null);
const activeTab = ref("room");

const actingOn = ref<string | null>(null);
const actionError = ref<string | null>(null);
const actionRequestId = ref<string | null>(null);
const values = ref<Record<string, Record<string, string>>>({});

const statusBusy = ref(false);
const statusError = ref<string | null>(null);
const cancelOpen = ref(false);

const myUserId = computed(() => sessionState.user?.id ?? null);
const isAdmin = computed(() => sessionState.user?.role === "admin");
/** The seat this console acts as: the same one the projection was built for. */
const mySeat = computed(
  () => detail.value?.seats.find((seat) => seat.actorUserId === myUserId.value) ?? null,
);
const open = computed(() => detail.value !== null && isOpen(detail.value.summary.status));
const catalogue = computed(
  () => new Map((detail.value?.actions ?? []).map((action) => [action.name, action])),
);
const myActions = computed(() =>
  (detail.value?.view?.availableActions ?? []).map((available) => ({
    actionId: available.actionId,
    spec: catalogue.value.get(available.actionId) ?? null,
  })),
);
const waitingSeats = computed(() =>
  (detail.value?.waiting?.participantIds ?? []).map((id) => seatName(id)),
);
const waitingActions = computed(() => detail.value?.waiting?.actions ?? []);
const roomTypes = computed(() =>
  (detail.value?.actions ?? [])
    .filter((action: GameAction) => (action.audience ?? "room") === "room")
    .map((action) => action.name),
);
const transcript = computed(
  () => (detail.value?.record ?? []).filter((row) => roomTypes.value.includes(row.type)),
);
const publicEntries = computed(() => Object.entries(detail.value?.view?.publicState ?? {}));
const privateEntries = computed(() =>
  Object.entries(detail.value?.view?.privateState ?? {}).map(([key, value]) => ({
    key: privateKey(key),
    value,
  })),
);

function seatName(participantId: string | null): string {
  if (participantId === null) return "平台";
  return detail.value?.seats.find((seat) => seat.participantId === participantId)?.key ?? participantId;
}

/** Private keys are addressed as `name:<participantId>`; only the name is worth showing. */
function privateKey(key: string): string {
  const id = mySeat.value?.participantId;
  if (id === undefined || !key.endsWith(`:${id}`)) return key;
  return key.slice(0, key.length - id.length - 1);
}

function valueText(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value);
}

function payloadField(row: MatchRecordRow, key: string): string {
  const value = row.payload[key];
  if (value === undefined || value === null) return "";
  return typeof value === "string" ? value : JSON.stringify(value);
}

function toolCalls(row: MatchRecordRow): Array<{ name: string; arguments: string }> {
  const raw = row.payload["toolCalls"];
  if (!Array.isArray(raw)) return [];
  const calls: Array<{ name: string; arguments: string }> = [];
  for (const item of raw) {
    if (typeof item !== "object" || item === null) continue;
    const call = item as Record<string, unknown>;
    calls.push({ name: String(call["name"] ?? ""), arguments: String(call["arguments"] ?? "") });
  }
  return calls;
}

function usageText(row: MatchRecordRow): string {
  if (row.usage === null) return "—";
  return `${row.usage.modelId} · ${row.usage.promptTokens}/${row.usage.completionTokens}/${row.usage.totalTokens}`;
}

function argFields(spec: GameAction | null): SeatArg[] {
  if (!spec?.args) return [];
  return Object.entries(spec.args).map(([name, arg]) => ({
    name,
    description: arg.description,
    kind: arg.kind === "seat" ? "seat" : null,
  }));
}

function valueOf(actionId: string, name: string): string {
  return values.value[actionId]?.[name] ?? "";
}

function setValue(actionId: string, name: string, value: string): void {
  values.value = { ...values.value, [actionId]: { ...(values.value[actionId] ?? {}), [name]: value } };
}

async function load(): Promise<void> {
  loading.value = true;
  loadError.value = null;
  loadRequestId.value = null;
  try {
    detail.value = await api.readMatch(instanceId.value);
  } catch (error) {
    loadError.value = uiErrorMessage(error);
    loadRequestId.value = apiRequestId(error);
  } finally {
    loading.value = false;
  }
}

onMounted(load);
watch(instanceId, load);

async function submit(actionId: string, spec: GameAction | null) {
  const seat = mySeat.value;
  if (!seat) {
    actionError.value = "你不是这局的席位，不能行动。";
    return;
  }
  const payload: Record<string, string> = {};
  for (const field of argFields(spec)) {
    const raw = valueOf(actionId, field.name).trim();
    if (raw.length === 0) {
      actionError.value = `请填写「${field.description}」。`;
      return;
    }
    payload[field.name] = raw;
  }

  actionError.value = null;
  actionRequestId.value = null;
  actingOn.value = actionId;
  try {
    // The payload is exactly what the game declared; the seat travels in `participantKey`.
    await api.submitMatchEvent(
      instanceId.value,
      { type: actionId, participantKey: seat.key, payload },
      crypto.randomUUID(),
    );
    values.value = { ...values.value, [actionId]: {} };
    await load();
  } catch (error) {
    actionError.value = uiErrorMessage(error);
    actionRequestId.value = apiRequestId(error);
  } finally {
    actingOn.value = null;
  }
}

async function setStatus(status: "running" | "paused" | "cancelled"): Promise<void> {
  statusBusy.value = true;
  statusError.value = null;
  try {
    await api.setMatchStatus(instanceId.value, status);
    cancelOpen.value = false;
    await load();
  } catch (error) {
    statusError.value = uiErrorMessage(error);
  } finally {
    statusBusy.value = false;
  }
}
</script>

<template>
  <section class="match">
    <header class="page-head">
      <div class="head-line">
        <el-button text :icon="ArrowLeft" @click="$router.push({ name: 'lobby' })">大厅</el-button>
        <h1>对局</h1>
        <el-tag v-if="detail" :type="statusTag(detail.summary.status)" effect="plain" size="small">
          {{ statusLabel(detail.summary.status) }}
        </el-tag>
        <el-button class="head-refresh" text :icon="Refresh" :loading="loading" @click="load">
          刷新
        </el-button>
      </div>
      <p class="page-sub mono">{{ instanceId }}</p>
    </header>

    <el-card class="panel" shadow="never">
      <el-alert
        v-if="loadError"
        class="stack-sm"
        data-testid="match-error"
        type="error"
        :title="loadError"
        :closable="false"
        show-icon
      />
      <p v-if="loadRequestId" class="meta">请求编号 {{ loadRequestId }}</p>

      <el-tabs v-if="detail" v-model="activeTab">
        <el-tab-pane label="房间" name="room">
          <el-descriptions class="stack" :column="2" border>
            <el-descriptions-item label="游戏">
              {{ detail.summary.gameId }}@{{ detail.summary.gameVersion }}
            </el-descriptions-item>
            <el-descriptions-item label="进度">
              <span class="mono">#{{ detail.summary.sequence }}</span>
              <span class="muted"> · {{ detail.summary.stepId }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="我的席位">
              <span v-if="mySeat" class="mono">{{ mySeat.key }}</span>
              <span v-else class="muted">无席位（管理员视角）</span>
            </el-descriptions-item>
            <el-descriptions-item label="当前等待点">
              <template v-if="detail.waiting">
                <span class="mono">{{ detail.waiting.stepId }}</span>
                <span class="muted">
                  · 等待 {{ waitingSeats.length === 0 ? "任何人" : waitingSeats.join("、") }}
                  <template v-if="waitingActions.length > 0"> · 可行动作 {{ waitingActions.join("、") }}</template>
                </span>
              </template>
              <span v-else class="muted">不在等待任何输入</span>
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ formatTime(detail.summary.createdAt) }}
            </el-descriptions-item>
            <el-descriptions-item label="记录行数">{{ detail.record.length }}</el-descriptions-item>
          </el-descriptions>

          <el-table class="stack" :data="detail.seats" row-key="participantId" size="small">
            <el-table-column label="席位" width="110">
              <template #default="{ row }">
                <span class="mono">{{ row.key }}</span>
              </template>
            </el-table-column>
            <el-table-column label="控制" width="90">
              <template #default="{ row }">
                <el-tag :type="row.control === 'ai' ? 'warning' : 'info'" effect="plain" size="small">
                  {{ row.control === "ai" ? "AI" : "真人" }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="row.status === 'active' ? 'success' : 'info'" effect="plain" size="small">
                  {{ row.status === "active" ? "在场" : row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="账号" min-width="150">
              <template #default="{ row }">
                <span v-if="row.actorUserId === null" class="muted">—</span>
                <span v-else-if="row.actorUserId === myUserId">我</span>
                <span v-else class="mono">{{ row.actorUserId.slice(0, 8) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="等待中" width="110">
              <template #default="{ row }">
                <span v-if="detail.waiting?.participantIds.includes(row.participantId)">是</span>
                <span v-else class="muted">—</span>
              </template>
            </el-table-column>
          </el-table>

          <el-card v-if="detail.briefing" class="stack inner" shadow="never">
            <template #header>
              <span class="panel-title">规则与你的处境</span>
            </template>
            <pre class="briefing">{{ detail.briefing }}</pre>
          </el-card>

          <div class="split">
            <el-card class="inner" shadow="never">
              <template #header>
                <span class="panel-title">只给你看的信息</span>
              </template>
              <el-descriptions v-if="privateEntries.length > 0" :column="1" border>
                <el-descriptions-item v-for="entry in privateEntries" :key="entry.key" :label="entry.key">
                  {{ valueText(entry.value) }}
                </el-descriptions-item>
              </el-descriptions>
              <el-empty v-else :image-size="60" description="当前没有单独的私有信息" />
            </el-card>

            <el-card class="inner" shadow="never">
              <template #header>
                <span class="panel-title">公开状态</span>
              </template>
              <el-descriptions :column="1" border>
                <el-descriptions-item v-for="entry in publicEntries" :key="entry[0]" :label="entry[0]">
                  {{ valueText(entry[1]) }}
                </el-descriptions-item>
              </el-descriptions>
            </el-card>
          </div>

          <el-card class="stack inner" shadow="never" data-testid="my-actions">
            <template #header>
              <span class="panel-title">我的动作</span>
            </template>

            <el-alert
              v-if="actionError"
              class="stack-sm"
              data-testid="action-error"
              type="error"
              :title="actionError"
              :closable="false"
              show-icon
            />
            <p v-if="actionRequestId" class="meta">请求编号 {{ actionRequestId }}</p>

            <template v-if="!open">
              <p class="hint">对局状态为「{{ statusLabel(detail.summary.status) }}」，不接受输入。</p>
            </template>
            <template v-else-if="myActions.length === 0">
              <p class="hint">现在轮不到你，刷新看别人的动作。</p>
            </template>
            <template v-else>
              <div v-for="action in myActions" :key="action.actionId" class="action">
                <div class="action-head">
                  <span class="action-title mono">{{ action.actionId }}</span>
                  <span class="muted">{{ action.spec?.description }}</span>
                </div>
                <div class="action-fields">
                  <div v-for="field in argFields(action.spec)" :key="field.name" class="action-field">
                    <el-select
                      v-if="field.kind === 'seat'"
                      :model-value="valueOf(action.actionId, field.name)"
                      :placeholder="field.description"
                      class="field-input"
                      @update:model-value="(value: string) => setValue(action.actionId, field.name, value)"
                    >
                      <el-option
                        v-for="seat in detail.seats"
                        :key="seat.participantId"
                        :label="`${seat.key}${seat.status === 'active' ? '' : `（${seat.status}）`}`"
                        :value="seat.participantId"
                      />
                    </el-select>
                    <el-input
                      v-else
                      :model-value="valueOf(action.actionId, field.name)"
                      :placeholder="field.description"
                      class="field-input"
                      @update:model-value="(value: string) => setValue(action.actionId, field.name, value)"
                    />
                  </div>
                  <el-button
                    type="primary"
                    :loading="actingOn === action.actionId"
                    @click="submit(action.actionId, action.spec)"
                  >
                    提交
                  </el-button>
                </div>
              </div>
            </template>
          </el-card>

          <el-card class="stack inner" shadow="never">
            <template #header>
              <div class="panel-head">
                <span class="panel-title">发言记录</span>
                <el-button text :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
              </div>
            </template>
            <el-empty v-if="transcript.length === 0" :image-size="60" description="还没有公开发言" />
            <ul v-else class="transcript">
              <li v-for="row in transcript" :key="row.eventId">
                <span class="mono transcript-seat">{{ seatName(row.participantId) }}</span>
                <span class="transcript-text">{{ payloadText(row.payload) }}</span>
              </li>
            </ul>
          </el-card>

          <el-card v-if="isAdmin" class="stack inner" shadow="never" data-testid="admin-ops">
            <template #header>
              <span class="panel-title">管理员运维</span>
            </template>
            <el-alert
              v-if="statusError"
              class="stack-sm"
              type="error"
              :title="statusError"
              :closable="false"
              show-icon
            />
            <div class="row-actions">
              <el-button :disabled="!open || statusBusy" @click="setStatus('paused')">暂停</el-button>
              <el-button :disabled="detail.summary.status !== 'paused' || statusBusy" @click="setStatus('running')">
                恢复
              </el-button>
              <el-button
                type="danger"
                plain
                :disabled="!open && detail.summary.status !== 'paused'"
                :loading="statusBusy"
                @click="cancelOpen = true"
              >
                取消对局
              </el-button>
            </div>
            <p class="hint">暂停、恢复与取消只改平台状态并写审计，不写成游戏事件；记录里能看出是谁在什么时候动的。</p>
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="记录" name="record">
          <p class="hint">
            按 <span class="mono">sequence</span> 的完整记录：模型调用行带思考与用量，逐行展开可看原始 JSON。
          </p>
          <el-table :data="detail.record" row-key="eventId" size="small" data-testid="record-table">
            <el-table-column type="expand">
              <template #default="{ row }">
                <pre class="raw">{{ JSON.stringify(row, null, 2) }}</pre>
              </template>
            </el-table-column>
            <el-table-column label="#" width="70">
              <template #default="{ row }">
                <span class="mono">#{{ row.sequence }}</span>
              </template>
            </el-table-column>
            <el-table-column label="事件" width="140">
              <template #default="{ row }">{{ eventLabel(row.type) }}</template>
            </el-table-column>
            <el-table-column label="席位" width="100">
              <template #default="{ row }">
                <span class="mono">{{ seatName(row.participantId) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="步骤" width="120">
              <template #default="{ row }">
                <span class="mono muted">{{ row.stepId ?? "—" }}</span>
              </template>
            </el-table-column>
            <el-table-column label="内容" min-width="320">
              <template #default="{ row }">
                <template v-if="row.type === 'aiCall'">
                  <div v-if="payloadField(row, 'content')" class="record-line">
                    {{ payloadField(row, "content") }}
                  </div>
                  <div v-for="(call, index) in toolCalls(row)" :key="index" class="record-line mono">
                    → {{ call.name }}({{ call.arguments }})
                  </div>
                  <el-collapse v-if="payloadField(row, 'reasoning')" class="reasoning">
                    <el-collapse-item title="模型思考">
                      <pre class="raw">{{ payloadField(row, "reasoning") }}</pre>
                    </el-collapse-item>
                  </el-collapse>
                </template>
                <template v-else-if="row.type === 'vote'">
                  → <span class="mono">{{ seatName(payloadField(row, "target")) }}</span>
                </template>
                <template v-else>{{ payloadText(row.payload) }}</template>
              </template>
            </el-table-column>
            <el-table-column label="用量 in/out/总" min-width="230">
              <template #default="{ row }">
                <span class="mono muted">{{ usageText(row) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="时间" width="180">
              <template #default="{ row }">{{ formatTime(row.occurredAtMs) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
      <el-skeleton v-else :rows="4" animated />
    </el-card>

    <el-dialog
      v-model="cancelOpen"
      title="取消对局"
      width="420px"
    >
      <p class="dialog-note">
        取消后该对局不再接受输入，记录保留。这是平台运维操作，会写入审计，不会写成游戏事件。
      </p>
      <template #footer>
        <el-button @click="cancelOpen = false">返回</el-button>
        <el-button type="danger" :loading="statusBusy" @click="setStatus('cancelled')">确认取消</el-button>
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

.head-refresh {
  margin-left: auto;
}

.page-sub {
  font-size: var(--text-sm);
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

.stack {
  margin-bottom: var(--space-md);
}

.stack-sm {
  margin-bottom: var(--space-sm);
}

.inner {
  margin-bottom: var(--space-md);
  background: var(--surface-warm);
}

.split {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-md);
}

.briefing {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
  white-space: pre-wrap;
  color: var(--fg-2);
}

.action {
  padding-bottom: var(--space-sm);
  margin-bottom: var(--space-sm);
  border-bottom: 1px solid var(--border-soft);
}

.action:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.action-head {
  display: flex;
  align-items: baseline;
  gap: var(--space-xs);
  margin-bottom: var(--space-xs);
}

.action-title {
  font-weight: 600;
}

.action-fields {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.field-input {
  flex: 1;
}

.transcript {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  margin: 0;
  padding: 0;
  list-style: none;
}

.transcript-seat {
  margin-right: var(--space-xs);
  color: var(--accent);
}

.transcript-text {
  font-size: var(--text-base);
}

.record-line {
  font-size: var(--text-base);
  white-space: pre-wrap;
}

.reasoning {
  margin-top: var(--space-2xs);
}

.raw {
  margin: 0;
  padding: var(--space-xs);
  overflow-x: auto;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
  color: var(--fg-2);
  background: var(--bg);
  border-radius: var(--radius-xs);
  white-space: pre-wrap;
  word-break: break-word;
}

.row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2xs);
}

.hint {
  margin-bottom: var(--space-sm);
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
</style>
