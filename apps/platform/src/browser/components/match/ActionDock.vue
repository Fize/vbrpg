<script setup lang="ts">
import { ref } from "vue";
import type { GameAction, MatchSeat } from "../../services/api";

interface Available {
  actionId: string;
  spec: GameAction | null;
}

const props = defineProps<{
  available: Available[];
  seats: MatchSeat[];
  /** Whether the caller holds a seat here; a watcher only gets a sentence. */
  seated: boolean;
  open: boolean;
  busyActionId: string | null;
  error: string | null;
  requestId: string | null;
  statusText: string;
}>();

const emit = defineEmits<{ submit: [payload: { actionId: string; values: Record<string, string> }] }>();

const values = ref<Record<string, Record<string, string>>>({});
const localError = ref<string | null>(null);

interface Field {
  name: string;
  description: string;
  seat: boolean;
}

function fieldsOf(spec: GameAction | null): Field[] {
  if (!spec?.args) return [];
  return Object.entries(spec.args).map(([name, arg]) => ({
    name,
    description: arg.description,
    seat: arg.kind === "seat",
  }));
}

function valueOf(actionId: string, name: string): string {
  return values.value[actionId]?.[name] ?? "";
}

function setValue(actionId: string, name: string, value: string): void {
  values.value = { ...values.value, [actionId]: { ...(values.value[actionId] ?? {}), [name]: value } };
}

function audienceOf(spec: GameAction | null): string {
  return (spec?.audience ?? "room") === "seat" ? "私密" : "公开";
}

function submit(action: Available): void {
  const filled: Record<string, string> = {};
  for (const field of fieldsOf(action.spec)) {
    const raw = valueOf(action.actionId, field.name).trim();
    if (raw.length === 0) {
      localError.value = `请填写「${field.description}」。`;
      return;
    }
    filled[field.name] = raw;
  }
  localError.value = null;
  emit("submit", { actionId: action.actionId, values: filled });
}

/** The page clears the form after a successful write. */
function reset(actionId: string): void {
  values.value = { ...values.value, [actionId]: {} };
}

defineExpose({ reset });
</script>

<template>
  <section class="dock" data-testid="my-actions">
    <header class="head">
      <span class="title">我的动作</span>
    </header>

    <el-alert
      v-if="error ?? localError"
      class="stack-sm"
      type="error"
      :title="error ?? localError ?? ''"
      :closable="false"
      show-icon
    />
    <p v-if="requestId" class="meta">请求编号 {{ requestId }}</p>

    <p v-if="!seated" class="hint">旁观没有动作可提交。</p>
    <p v-else-if="!open" class="hint">对局状态为「{{ statusText }}」，不接受输入。</p>
    <p v-else-if="available.length === 0" class="hint">现在轮不到你，刷新看别人的动作。</p>

    <template v-else>
      <div v-for="action in available" :key="action.actionId" class="action">
        <div class="action-head">
          <span class="action-name mono">{{ action.actionId }}</span>
          <el-tag
            size="small"
            effect="plain"
            :type="audienceOf(action.spec) === '私密' ? 'warning' : 'info'"
          >
            {{ audienceOf(action.spec) }}
          </el-tag>
        </div>
        <p class="action-desc">{{ action.spec?.description }}</p>

        <div class="action-fields">
          <div v-for="field in fieldsOf(action.spec)" :key="field.name" class="field">
            <el-select
              v-if="field.seat"
              :model-value="valueOf(action.actionId, field.name)"
              :placeholder="field.description"
              class="input"
              @update:model-value="(value: string) => setValue(action.actionId, field.name, value)"
            >
              <el-option
                v-for="seat in seats"
                :key="seat.participantId"
                :label="`${seat.key}${seat.status === 'active' ? '' : `（${seat.status}）`}`"
                :value="seat.participantId"
              />
            </el-select>
            <el-input
              v-else
              :model-value="valueOf(action.actionId, field.name)"
              :placeholder="field.description"
              class="input"
              @update:model-value="(value: string) => setValue(action.actionId, field.name, value)"
            />
          </div>
          <el-button
            type="primary"
            :loading="busyActionId === action.actionId"
            @click="submit(action)"
          >
            提交
          </el-button>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.dock {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  padding: var(--space-md);
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--fg-2);
}

.action {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid var(--border-soft);
}

.action:last-child {
  padding-bottom: 0;
  border-bottom: none;
}

.action-head {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.action-name {
  font-weight: 600;
  color: var(--fg);
}

.action-desc {
  font-size: var(--text-sm);
  color: var(--muted);
}

.action-fields {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.field {
  flex: 1;
}

.input {
  width: 100%;
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
</style>
