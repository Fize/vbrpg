<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ArrowLeft, Refresh } from "@element-plus/icons-vue";
import { api, apiRequestId, type GameAction, type MatchSeat } from "../services/api";
import { uiErrorMessage } from "../services/messages";
import {
  describePayload,
  isOpen,
  statusLabel,
  statusTag,
  wordText,
} from "../services/match-labels";
import { sessionState } from "../stores/session";
import ActionDock from "../components/match/ActionDock.vue";
import MatchLog from "../components/match/MatchLog.vue";
import PhaseCard from "../components/match/PhaseCard.vue";
import SeatRing from "../components/match/SeatRing.vue";

type Detail = Awaited<ReturnType<typeof api.readMatch>>;

const route = useRoute();
const instanceId = computed(() => String(route.params["instanceId"] ?? ""));

const detail = ref<Detail | null>(null);
const loading = ref(false);
const loadError = ref<string | null>(null);
const loadRequestId = ref<string | null>(null);

const actingOn = ref<string | null>(null);
const actionError = ref<string | null>(null);
const actionRequestId = ref<string | null>(null);
const dock = ref<InstanceType<typeof ActionDock> | null>(null);

const myUserId = computed(() => sessionState.user?.id ?? null);
const mySeat = computed(
  () => detail.value?.seats.find((seat) => seat.actorUserId === myUserId.value) ?? null,
);
const open = computed(() => detail.value !== null && isOpen(detail.value.summary.status));
const catalogue = computed(
  () => new Map((detail.value?.actions ?? []).map((action) => [action.name, action])),
);
const available = computed(() =>
  (detail.value?.view.availableActions ?? []).map((action) => ({
    actionId: action.actionId,
    spec: catalogue.value.get(action.actionId) ?? null,
  })),
);
const waitingParticipantIds = computed(() => detail.value?.waiting?.participantIds ?? []);
const waitingSeats = computed(() => waitingParticipantIds.value.map((id) => seatName(id)));
const publicEntries = computed(
  () => Object.entries(detail.value?.view.publicState ?? {}) as Array<[string, unknown]>,
);
const privateEntries = computed(() =>
  Object.entries(detail.value?.view.privateState ?? {}).map(([key, value]) => ({
    key: privateKey(key),
    value,
  })),
);
const myPersona = computed(() => mySeat.value?.persona ?? null);

/** One line per seat: a persona the reader may see, never including MBTI for someone else. */
function personaLine(persona: MatchSeat["persona"]): string {
  if (persona === null) return "";
  return [persona.mbti, persona.gender, persona.profession, persona.personality, persona.style]
    .filter((part): part is string => part !== undefined && part !== "")
    .join(" · ");
}

const aliveCount = computed(
  () => (detail.value?.seats ?? []).filter((seat) => seat.status === "active").length,
);
const roomActionNames = computed(
  () =>
    new Set(
      (detail.value?.actions ?? [])
        .filter((action: GameAction) => (action.audience ?? "room") === "room")
        .map((action) => action.name),
    ),
);
/** Each seat's most recent line in the shared transcript, which is what the table hears. */
const bubbles = computed(() => {
  const map: Record<string, string> = {};
  for (const row of detail.value?.record ?? []) {
    if (row.participantId !== null && roomActionNames.value.has(row.type)) {
      map[row.participantId] = describePayload({
        payload: row.payload,
        action: catalogue.value.get(row.type),
        words: detail.value?.game.words ?? {},
        seatName,
      });
    }
  }
  return map;
});

function seatName(participantId: string | null): string {
  if (participantId === null) return "平台";
  return (
    detail.value?.seats.find((seat) => seat.participantId === participantId)?.key ?? participantId
  );
}

/** Private keys are addressed as `name:<participantId>`; the name is what a reader needs. */
function privateKey(key: string): string {
  const id = mySeat.value?.participantId;
  const name =
    id !== undefined && key.endsWith(`:${id}`) ? key.slice(0, key.length - id.length - 1) : key;
  return detail.value?.game.words[name] ?? name;
}

function actorLabel(userId: string | null): string {
  return userId !== null && userId === myUserId.value ? "我" : "";
}

function valueText(value: unknown): string {
  return wordText(value, detail.value?.game.words ?? {}, seatName);
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

async function submit(payload: {
  actionId: string;
  values: Record<string, string>;
}): Promise<void> {
  const seat = mySeat.value;
  if (!seat) return;

  actionError.value = null;
  actionRequestId.value = null;
  actingOn.value = payload.actionId;
  try {
    // The payload is exactly what the game declared; the seat travels in `participantKey`.
    await api.submitMatchEvent(
      instanceId.value,
      { type: payload.actionId, participantKey: seat.key, payload: payload.values },
      crypto.randomUUID(),
    );
    dock.value?.reset(payload.actionId);
    await load();
  } catch (error) {
    actionError.value = uiErrorMessage(error);
    actionRequestId.value = apiRequestId(error);
  } finally {
    actingOn.value = null;
  }
}
</script>

<template>
  <section class="room">
    <header class="topbar">
      <el-button text :icon="ArrowLeft" @click="$router.push({ name: 'lobby' })">大厅</el-button>
      <span class="room-id mono" :title="instanceId">{{ instanceId.slice(0, 8) }}</span>
      <el-tag v-if="detail" :type="statusTag(detail.summary.status)" effect="plain" size="small">
        {{ statusLabel(detail.summary.status) }}
      </el-tag>
      <el-tag v-if="detail && mySeat" type="primary" effect="plain" size="small">
        我的席位 {{ mySeat.key }}
      </el-tag>
      <el-tag v-else-if="detail" type="info" effect="plain" size="small">观战中</el-tag>
      <el-button class="spacer" text :icon="Refresh" :loading="loading" @click="load"
        >刷新</el-button
      >
    </header>

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

    <div v-if="detail" class="layout">
      <aside class="column col-left">
        <PhaseCard
          :summary="detail.summary"
          :waiting-step-id="detail.waiting?.stepId ?? null"
          :waiting-seats="waitingSeats"
          :allowed-actions="detail.waiting?.actions ?? []"
          :public-entries="publicEntries"
          :seat-name="seatName"
          :game="detail.game"
          :actions="detail.actions"
        />

        <section v-if="mySeat" class="panel">
          <header class="panel-head">
            <span class="panel-title">我的席位</span>
            <span class="mono seat-key">{{ mySeat.key }}</span>
          </header>
          <pre v-if="detail.briefing" class="briefing">{{ detail.briefing }}</pre>
          <p v-else class="hint">这局没有给你单独的规则文本。</p>
        </section>

        <section v-if="mySeat" class="panel">
          <header class="panel-head">
            <span class="panel-title">只给你看的信息</span>
          </header>
          <el-descriptions v-if="privateEntries.length > 0" :column="1" border size="small">
            <el-descriptions-item
              v-for="entry in privateEntries"
              :key="entry.key"
              :label="entry.key"
            >
              {{ valueText(entry.value) }}
            </el-descriptions-item>
          </el-descriptions>
          <p v-else class="hint">当前没有单独的私有信息。</p>
        </section>

        <section v-if="myPersona" class="panel" data-testid="my-persona">
          <header class="panel-head">
            <span class="panel-title">我的人物卡</span>
          </header>
          <dl class="persona">
            <div>
              <dt>人格类型</dt>
              <dd class="mono">{{ myPersona.mbti }}</dd>
            </div>
            <div>
              <dt>性别</dt>
              <dd>{{ myPersona.gender }}</dd>
            </div>
            <div>
              <dt>职业</dt>
              <dd>{{ myPersona.profession }}</dd>
            </div>
            <div>
              <dt>性格</dt>
              <dd>{{ myPersona.personality }}</dd>
            </div>
            <div>
              <dt>说话风格</dt>
              <dd>{{ myPersona.style }}</dd>
            </div>
          </dl>
          <p class="hint">人格影响你怎么说话；MBTI 只有你自己知道。</p>
        </section>

        <ActionDock
          ref="dock"
          :available="available"
          :seats="detail.seats"
          :seated="mySeat !== null"
          :open="open"
          :busy-action-id="actingOn"
          :error="actionError"
          :request-id="actionRequestId"
          :status-text="statusLabel(detail.summary.status)"
          @submit="submit"
        />
      </aside>

      <main class="column col-center">
        <SeatRing
          :seats="detail.seats"
          :my-seat-key="mySeat?.key ?? null"
          :waiting-participant-ids="waitingParticipantIds"
          :bubbles="bubbles"
          :actor-label="actorLabel"
          :persona-line="personaLine"
        >
          <template #center>
            <span class="center-status">{{ statusLabel(detail.summary.status) }}</span>
            <span class="center-alive">
              <strong>{{ aliveCount }}</strong>
              <em>席在场</em>
            </span>
            <span class="center-waiting">
              {{ waitingSeats.length === 0 ? "不在等待输入" : `等 ${waitingSeats.join("、")}` }}
            </span>
          </template>
        </SeatRing>
      </main>

      <aside class="column col-right">
        <MatchLog
          :record="detail.record"
          :actions="detail.actions"
          :game="detail.game"
          :seat-name="seatName"
          :loading="loading"
          @refresh="load"
        />
      </aside>
    </div>

    <el-skeleton v-else :rows="6" animated />
  </section>
</template>

<style scoped>
.room {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  height: 100%;
}

.topbar {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding-bottom: var(--space-2xs);
  border-bottom: 1px solid var(--border-soft);
}

.spacer {
  margin-left: auto;
}

.room-id {
  font-size: var(--text-xs);
  color: var(--meta);
}

.layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr) 360px;
  align-items: start;
  gap: var(--space-md);
  flex: 1;
  min-height: 0;
}

.column {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  min-width: 0;
}

.col-center {
  align-items: center;
  justify-content: center;
  padding: var(--space-md) 0;
}

.col-right {
  min-height: 0;
  max-height: calc(100vh - var(--header-height) - 120px);
}

.panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  padding: var(--space-md);
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
}

.panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.panel-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--fg-2);
}

.seat-key {
  color: var(--accent);
}

.briefing {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
  color: var(--fg-2);
  white-space: pre-wrap;
}

.persona {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
  margin: 0;
  font-size: var(--text-sm);
}

.persona div {
  display: flex;
  gap: var(--space-xs);
}

.persona dt {
  flex: 0 0 72px;
  color: var(--meta);
}

.persona dd {
  margin: 0;
  color: var(--fg-2);
  overflow-wrap: anywhere;
}

.center-status {
  font-size: var(--text-xs);
  color: var(--muted);
}

.center-alive {
  display: flex;
  align-items: baseline;
  gap: var(--space-3xs);
}

.center-alive strong {
  font-size: var(--text-2xl);
  color: var(--accent);
}

.center-alive em {
  font-size: var(--text-xs);
  font-style: normal;
  color: var(--meta);
}

.center-waiting {
  font-size: var(--text-xs);
  color: var(--warn);
}

.hint {
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

@media (max-width: 1200px) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .col-right {
    max-height: none;
  }
}
</style>
