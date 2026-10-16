<script setup lang="ts">
import { computed } from "vue";
import type { MatchSummary } from "../../services/api";
import { stateValueText, statusLabel, statusTag } from "../../services/match-labels";

const props = defineProps<{
  summary: MatchSummary;
  waitingStepId: string | null;
  waitingSeats: string[];
  allowedActions: string[];
  publicEntries: Array<[string, unknown]>;
  seatName: (participantId: string) => string;
}>();

function valueText(value: unknown): string {
  return stateValueText(value, props.seatName);
}

/** Who the platform is waiting for, in seat names. */
const waitingText = computed(() =>
  props.waitingSeats.length === 0 ? "不在等待输入" : props.waitingSeats.join("、"),
);
</script>

<template>
  <section class="phase">
    <header class="head">
      <span class="title">当前阶段</span>
      <el-tag :type="statusTag(summary.status)" effect="plain" size="small">
        {{ statusLabel(summary.status) }}
      </el-tag>
    </header>

    <div class="step">
      <span class="step-id mono">{{ waitingStepId ?? summary.stepId }}</span>
      <span class="seq mono">#{{ summary.sequence }}</span>
    </div>

    <dl class="facts">
      <div class="fact">
        <dt>等待</dt>
        <dd :class="{ 'is-waiting': waitingSeats.length > 0 }">{{ waitingText }}</dd>
      </div>
      <div class="fact">
        <dt>本步允许的动作</dt>
        <dd>{{ allowedActions.length === 0 ? "无" : allowedActions.join("、") }}</dd>
      </div>
      <div class="fact">
        <dt>游戏</dt>
        <dd class="mono">{{ summary.gameId }}@{{ summary.gameVersion }}</dd>
      </div>
    </dl>

    <div v-if="publicEntries.length > 0" class="vars">
      <span class="vars-title">公开状态</span>
      <ul class="vars-list">
        <li v-for="entry in publicEntries" :key="entry[0]">
          <span class="var-key mono">{{ entry[0] }}</span>
          <span class="var-value">{{ valueText(entry[1]) }}</span>
        </li>
      </ul>
    </div>
    <p v-else class="empty">这局没有公开状态变量。</p>
  </section>
</template>

<style scoped>
.phase {
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

.step {
  display: flex;
  align-items: baseline;
  gap: var(--space-xs);
}

.step-id {
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--accent);
}

.seq {
  font-size: var(--text-sm);
  color: var(--meta);
}

.facts {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
  margin: 0;
}

.fact {
  display: flex;
  gap: var(--space-xs);
  font-size: var(--text-sm);
}

.fact dt {
  flex: 0 0 96px;
  color: var(--meta);
}

.fact dd {
  margin: 0;
  color: var(--fg-2);
  overflow-wrap: anywhere;
}

.fact dd.is-waiting {
  color: var(--warn);
}

.vars {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
  padding-top: var(--space-xs);
  border-top: 1px solid var(--border-soft);
}

.vars-title {
  font-size: var(--text-xs);
  color: var(--meta);
}

.vars-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3xs);
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: var(--text-sm);
}

.vars-list li {
  display: flex;
  gap: var(--space-xs);
}

.var-key {
  flex: 0 0 96px;
  color: var(--meta);
  overflow-wrap: anywhere;
}

.var-value {
  color: var(--fg-2);
  overflow-wrap: anywhere;
}

.empty {
  font-size: var(--text-sm);
  color: var(--meta);
}
</style>
