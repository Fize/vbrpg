<script setup lang="ts">
import { computed } from "vue";
import type { MatchSeat } from "../../services/api";
import SeatNode from "./SeatNode.vue";

/** Beyond this many seats a ring stops being readable: fall back to a grid. */
const RING_LIMIT = 12;
const RADIUS = 40;

const props = defineProps<{
  seats: MatchSeat[];
  mySeatKey: string | null;
  waitingParticipantIds: string[];
  bubbles: Record<string, string>;
  actorLabel: (userId: string | null) => string;
}>();

const ring = computed(() => props.seats.length <= RING_LIMIT);

function angleOf(index: number): number {
  return (2 * Math.PI * index) / Math.max(props.seats.length, 1) - Math.PI / 2;
}

function nodeStyle(index: number): Record<string, string> {
  const angle = angleOf(index);
  return {
    left: `${50 + RADIUS * Math.cos(angle)}%`,
    top: `${50 + RADIUS * Math.sin(angle)}%`,
    transform: "translate(-50%, -50%)",
  };
}

const spokes = computed(() =>
  props.seats.map((seat, index) => {
    const angle = angleOf(index);
    return {
      id: seat.participantId,
      x: 50 + RADIUS * Math.cos(angle),
      y: 50 + RADIUS * Math.sin(angle),
      active: seat.status === "active",
    };
  }),
);
</script>

<template>
  <div class="ring-wrap">
    <div v-if="ring" class="table">
      <div class="ring ring-outer" aria-hidden="true"></div>
      <div class="ring ring-inner" aria-hidden="true"></div>
      <svg class="spokes" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <line
          v-for="spoke in spokes"
          :key="spoke.id"
          x1="50"
          y1="50"
          :x2="spoke.x"
          :y2="spoke.y"
          :class="{ 'is-out': !spoke.active }"
        />
      </svg>

      <div class="center-slot">
        <slot name="center" />
      </div>

      <div v-for="(seat, index) in seats" :key="seat.participantId" class="slot" :style="nodeStyle(index)">
        <SeatNode
          :seat="seat"
          :actor-label="actorLabel(seat.actorUserId)"
          :is-mine="seat.key === mySeatKey"
          :is-waiting="waitingParticipantIds.includes(seat.participantId)"
          :bubble="bubbles[seat.participantId] ?? null"
        />
      </div>
    </div>

    <div v-else class="grid">
      <SeatNode
        v-for="seat in seats"
        :key="seat.participantId"
        :seat="seat"
        :actor-label="actorLabel(seat.actorUserId)"
        :is-mine="seat.key === mySeatKey"
        :is-waiting="waitingParticipantIds.includes(seat.participantId)"
        :bubble="bubbles[seat.participantId] ?? null"
      />
    </div>
  </div>
</template>

<style scoped>
.ring-wrap {
  display: flex;
  justify-content: center;
  width: 100%;
}

.table {
  position: relative;
  width: min(100%, 560px);
  aspect-ratio: 1;
}

.ring {
  position: absolute;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-soft);
  pointer-events: none;
}

.ring-outer {
  inset: 8%;
  border-color: var(--border);
}

.ring-inner {
  inset: 28%;
  border-style: dashed;
}

.spokes {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.spokes line {
  stroke: var(--border-accent);
  stroke-width: 0.2;
  opacity: 0.5;
}

.spokes line.is-out {
  stroke: var(--muted);
  opacity: 0.25;
}

.center-slot {
  position: absolute;
  top: 50%;
  left: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2xs);
  width: 34%;
  padding: var(--space-sm);
  text-align: center;
  background: var(--surface-glass);
  border: 1px solid var(--border-accent);
  border-radius: var(--radius-full);
  aspect-ratio: 1;
  transform: translate(-50%, -50%);
  backdrop-filter: blur(10px);
  box-shadow: var(--glow-brand);
}

.slot {
  position: absolute;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: var(--space-md);
  width: 100%;
  padding: var(--space-sm);
}
</style>
