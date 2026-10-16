<script setup lang="ts">
import { computed } from "vue";
import { Monitor, User } from "@element-plus/icons-vue";
import type { MatchSeat } from "../../services/api";

const props = defineProps<{
  seat: MatchSeat;
  actorLabel: string;
  isMine: boolean;
  isWaiting: boolean;
  /** The seat's latest line in the shared transcript, or null when it has not spoken. */
  bubble: string | null;
  /** What this reader may see of the seat's persona, already formatted; empty when unknown. */
  personaLine: string;
}>();

const out = computed(() => props.seat.status !== "active");
const statusLabel = computed(() => {
  switch (props.seat.status) {
    case "active":
      return "在场";
    case "eliminated":
      return "出局";
    case "disconnected":
      return "掉线";
    default:
      return "已结束";
  }
});
</script>

<template>
  <el-tooltip :content="personaLine" :disabled="personaLine === ''" placement="top">
    <div
      class="seat"
      data-testid="seat"
      :class="{
        'is-mine': isMine,
        'is-waiting': isWaiting,
        'is-out': out,
        'is-ai': seat.control === 'ai',
      }"
    >
      <div class="node">
        <div class="face">
          <el-icon :size="22">
            <Monitor v-if="seat.control === 'ai'" />
            <User v-else />
          </el-icon>
          <i class="led" aria-hidden="true"></i>
        </div>
        <div class="label">
          <span class="key mono">{{ seat.key }}</span>
          <span v-if="isMine" class="mine">我</span>
        </div>
      </div>

      <div class="meta">
        <span class="status">{{ statusLabel }}</span>
        <span v-if="seat.persona?.gender" class="control">{{ seat.persona.gender }}</span>
        <span v-if="seat.control === 'ai'" class="control">AI</span>
        <span v-else-if="actorLabel" class="control" :title="actorLabel">{{ actorLabel }}</span>
        <span v-if="isWaiting" class="waiting">等待行动</span>
      </div>

      <p v-if="bubble" class="bubble" :class="{ 'is-mine': isMine }" :title="bubble">
        {{ bubble }}
      </p>
    </div>
  </el-tooltip>
</template>

<style scoped>
.seat {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3xs);
  width: 104px;
  text-align: center;
}

.node {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3xs);
  padding: var(--space-xs) var(--space-sm);
  background: var(--surface-glass);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  backdrop-filter: blur(8px);
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    box-shadow var(--motion-fast) var(--ease-standard);
}

.seat.is-mine .node {
  border-color: var(--border-accent);
  box-shadow: var(--glow-accent);
}

.seat.is-waiting .node {
  border-color: var(--warn);
  box-shadow: 0 0 0 3px rgba(255, 176, 32, 0.16);
}

.seat.is-out .node {
  opacity: 0.55;
}

.seat.is-out .face {
  filter: grayscale(1);
}

.face {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  color: var(--accent);
  background: var(--surface-raised);
  border-radius: var(--radius-sm);
}

.seat.is-ai .face {
  color: var(--accent-secondary);
}

.led {
  position: absolute;
  right: -3px;
  bottom: -3px;
  width: 8px;
  height: 8px;
  background: var(--success);
  border: 1px solid var(--bg);
  border-radius: var(--radius-full);
}

.seat.is-out .led {
  background: var(--danger);
}

.label {
  display: flex;
  align-items: center;
  gap: var(--space-3xs);
}

.key {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--fg);
}

.mine {
  font-size: var(--text-xs);
  color: var(--accent);
}

.meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-3xs);
  font-size: var(--text-xs);
  color: var(--meta);
}

.waiting {
  color: var(--warn);
}

.bubble {
  display: -webkit-box;
  max-width: 100%;
  padding: var(--space-2xs) var(--space-xs);
  font-size: var(--text-sm);
  line-height: var(--leading-tight);
  color: var(--fg-2);
  background: var(--surface-raised);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-sm);
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  overflow: hidden;
}

.bubble.is-mine {
  border-color: var(--border-accent);
}
</style>
