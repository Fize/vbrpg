<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { Bottom, Refresh } from "@element-plus/icons-vue";
import type { GameAction, GameVocabulary, MatchRecordRow } from "../../services/api";
import { buildLog, type LogKind } from "../../services/match-log";

const props = defineProps<{
  record: MatchRecordRow[];
  actions: GameAction[];
  game: GameVocabulary;
  seatName: (participantId: string | null) => string;
  loading: boolean;
}>();

const emit = defineEmits<{ refresh: [] }>();

/** Basic reads like a transcript; detailed adds the model's thinking, usage and raw rows. */
const level = ref<"basic" | "detailed">("basic");
const body = ref<HTMLElement | null>(null);
const pinned = ref(true);

const entries = computed(() =>
  buildLog({
    record: props.record,
    actions: props.actions,
    game: props.game,
    seatName: props.seatName,
  }),
);

const KIND_LABELS: Record<LogKind, string> = {
  speech: "发言",
  private: "私密",
  phase: "阶段",
  model: "模型",
  system: "系统",
};

function rawOf(entryId: string): string {
  const row = props.record.find((candidate) => candidate.eventId === entryId);
  return row === undefined ? "" : JSON.stringify(row, null, 2);
}

function scrollToBottom(): void {
  const element = body.value;
  if (element) element.scrollTop = element.scrollHeight;
  pinned.value = true;
}

function onScroll(): void {
  const element = body.value;
  if (!element) return;
  pinned.value = element.scrollHeight - element.scrollTop - element.clientHeight < 24;
}

// New rows arrive on refresh, not by push, so the panel keeps the reader where it left them.
watch(
  () => props.record.length,
  async () => {
    await nextTick();
    if (pinned.value) scrollToBottom();
  },
  { immediate: true },
);
</script>

<template>
  <section class="log" data-testid="match-log">
    <header class="head">
      <span class="title">记录</span>
      <div class="tools">
        <el-radio-group v-model="level" size="small">
          <el-radio-button value="basic" label="basic">基本</el-radio-button>
          <el-radio-button value="detailed" label="detailed">详细</el-radio-button>
        </el-radio-group>
        <el-button text :icon="Refresh" :loading="loading" @click="emit('refresh')">刷新</el-button>
      </div>
    </header>

    <div ref="body" class="body" @scroll="onScroll">
      <el-empty v-if="entries.length === 0" :image-size="60" description="还没有记录" />

      <article
        v-for="entry in entries"
        :key="entry.eventId"
        class="entry"
        :class="`kind-${entry.kind}`"
      >
        <div v-if="entry.kind === 'phase' || entry.kind === 'system'" class="marker">
          <span class="marker-label">{{ entry.label }}</span>
          <span class="marker-seq mono">#{{ entry.sequence }}</span>
        </div>

        <template v-else>
          <div class="line">
            <span class="seq mono">#{{ entry.sequence }}</span>
            <span class="seat mono">{{ entry.seat }}</span>
            <span class="kind">{{ KIND_LABELS[entry.kind] }}</span>
            <span class="label">{{ entry.label }}</span>
          </div>

          <p v-if="entry.kind !== 'model'" class="text">{{ entry.text }}</p>

          <template v-else>
            <div v-for="(call, index) in entry.model?.toolCalls ?? []" :key="index" class="call">
              <span class="call-name">{{ call.label }}</span>
              <span class="call-args">{{ call.text }}</span>
            </div>
            <p v-if="entry.model?.usage" class="usage">{{ entry.model.usage }}</p>
          </template>

          <template v-if="level === 'detailed'">
            <el-collapse v-if="entry.model?.reasoning" class="reasoning">
              <el-collapse-item title="模型思考">
                <pre class="raw">{{ entry.model.reasoning }}</pre>
              </el-collapse-item>
            </el-collapse>
            <el-collapse class="raw-block">
              <el-collapse-item title="原始记录行">
                <pre class="raw">{{ rawOf(entry.eventId) }}</pre>
              </el-collapse-item>
            </el-collapse>
          </template>
        </template>
      </article>
    </div>

    <el-button
      v-if="!pinned"
      class="to-bottom"
      text
      size="small"
      :icon="Bottom"
      @click="scrollToBottom"
    >
      到底部
    </el-button>
  </section>
</template>

<style scoped>
.log {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: var(--space-md);
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-xs);
  padding-bottom: var(--space-xs);
  border-bottom: 1px solid var(--border-soft);
}

.title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--fg-2);
}

.tools {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.body {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  flex: 1;
  min-height: 240px;
  padding: var(--space-xs) var(--space-2xs) 0;
  overflow-y: auto;
}

.entry {
  display: flex;
  flex-direction: column;
  gap: var(--space-3xs);
  font-size: var(--text-sm);
}

.marker {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-xs);
  padding: var(--space-3xs) 0;
  color: var(--meta);
  border-top: 1px dashed var(--border-soft);
}

.marker-label {
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-tight);
}

.marker-seq {
  font-size: var(--text-xs);
  opacity: 0.7;
}

.line {
  display: flex;
  align-items: baseline;
  gap: var(--space-xs);
}

.seq {
  color: var(--meta);
  font-size: var(--text-xs);
}

.seat {
  color: var(--accent);
}

.kind {
  padding: 0 var(--space-3xs);
  font-size: var(--text-xs);
  color: var(--meta);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-xs);
}

.label {
  color: var(--muted);
  font-size: var(--text-xs);
}

.entry.kind-private .seat {
  color: var(--accent-secondary);
}

.text {
  color: var(--fg);
  overflow-wrap: anywhere;
}

.call {
  display: flex;
  gap: var(--space-xs);
  color: var(--fg-2);
  overflow-wrap: anywhere;
}

.call-name {
  flex: 0 0 auto;
  color: var(--accent);
}

.usage {
  font-size: var(--text-xs);
  color: var(--meta);
}

.reasoning,
.raw-block {
  --el-collapse-header-height: 28px;
  margin-top: var(--space-3xs);
}

.reasoning :deep(.el-collapse-item__header),
.raw-block :deep(.el-collapse-item__header) {
  font-size: var(--text-xs);
  color: var(--muted);
  background: transparent;
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

.to-bottom {
  position: absolute;
  right: var(--space-md);
  bottom: var(--space-md);
  background: var(--surface-raised);
}
</style>
