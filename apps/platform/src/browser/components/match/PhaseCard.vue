<script setup lang="ts">
import { computed } from "vue";
import type { GameAction, GameVocabulary, MatchSummary } from "../../services/api";
import {
  eventLabel,
  statusLabel,
  statusTag,
  stepLabel,
  wordText,
} from "../../services/match-labels";

const props = defineProps<{
  summary: MatchSummary;
  waitingStepId: string | null;
  waitingSeats: string[];
  allowedActions: string[];
  publicEntries: Array<[string, unknown]>;
  seatName: (participantId: string) => string;
  game: GameVocabulary;
  actions: GameAction[];
}>();

function valueText(value: unknown): string {
  return wordText(value, props.game.words, props.seatName);
}

function keyText(key: string): string {
  return props.game.words[key] ?? key;
}

interface Table {
  columns: string[];
  rows: string[][];
}

/**
 * A list of same-shaped objects is a table, not a sentence: a per-seat report read as one comma
 * list repeats every column name and hides the comparison the table exists for.
 */
function tableOf(value: unknown): Table | null {
  if (!Array.isArray(value) || value.length === 0) return null;
  const records = value.filter(
    (item): item is Record<string, unknown> =>
      typeof item === "object" && item !== null && !Array.isArray(item),
  );
  if (records.length !== value.length) return null;
  const [first] = records;
  if (first === undefined) return null;
  const columns = Object.keys(first);
  if (records.some((record) => Object.keys(record).length !== columns.length)) return null;
  return {
    columns,
    rows: records.map((record) => columns.map((column) => valueText(record[column]))),
  };
}

const publicRows = computed(() =>
  props.publicEntries.map(([key, value]) => ({
    key,
    label: keyText(key),
    table: tableOf(value),
    text: valueText(value),
  })),
);

/** The actions this step allows, in the game's own words. */
const allowedText = computed(() =>
  props.allowedActions.length === 0
    ? "无"
    : props.allowedActions
        .map((name) => eventLabel(props.actions, props.game.words, name))
        .join("、"),
);

const stepText = computed(() => stepLabel(props.game, props.waitingStepId ?? props.summary.stepId));

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
      <span class="step-id">{{ stepText }}</span>
      <span class="seq mono">#{{ summary.sequence }}</span>
    </div>

    <dl class="facts">
      <div class="fact">
        <dt>等待</dt>
        <dd :class="{ 'is-waiting': waitingSeats.length > 0 }">{{ waitingText }}</dd>
      </div>
      <div class="fact">
        <dt>本步允许的动作</dt>
        <dd>{{ allowedText }}</dd>
      </div>
      <div class="fact">
        <dt>游戏</dt>
        <dd>
          {{ game.title }}<span class="version mono">@{{ summary.gameVersion }}</span>
        </dd>
      </div>
    </dl>

    <div v-if="publicEntries.length > 0" class="vars">
      <span class="vars-title">公开状态</span>
      <ul class="vars-list">
        <li v-for="entry in publicRows" :key="entry.key">
          <span class="var-key">{{ entry.label }}</span>
          <span v-if="entry.table === null" class="var-value">{{ entry.text }}</span>
          <table v-else class="var-table">
            <thead>
              <tr>
                <th v-for="column in entry.table.columns" :key="column">{{ keyText(column) }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in entry.table.rows" :key="index">
                <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
              </tr>
            </tbody>
          </table>
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

.version {
  font-size: var(--text-xs);
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

.var-table {
  margin-top: var(--space-2xs);
  border-collapse: collapse;
  font-size: var(--text-sm);
  color: var(--fg-2);
}

.var-table th,
.var-table td {
  padding: 2px var(--space-xs);
  text-align: left;
  border-bottom: 1px solid var(--border-soft);
  white-space: nowrap;
}

.var-table th {
  color: var(--fg);
  font-weight: 600;
}

.empty {
  font-size: var(--text-sm);
  color: var(--meta);
}
</style>
