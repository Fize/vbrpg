<script setup lang="ts">
defineProps<{
  loading?: boolean;
  error?: string | null;
  requestId?: string | null;
  empty?: boolean;
  loadingText?: string;
  emptyText?: string;
}>();
</script>

<template>
  <div v-if="loading" class="state-block" role="status">
    <p>{{ loadingText ?? "Loading…" }}</p>
  </div>
  <div v-else-if="error" class="state-block state-block-error" role="alert">
    <p>{{ error }}</p>
    <p v-if="requestId" class="request-id">requestId: {{ requestId }}</p>
  </div>
  <div v-else-if="empty" class="state-block">
    <p>{{ emptyText ?? "Nothing here yet." }}</p>
  </div>
  <slot v-else />
</template>

<style scoped>
.state-block {
  padding: 1rem;
  border: 1px dashed #94a3b8;
  border-radius: 6px;
  color: #475569;
  background: #f8fafc;
}

.state-block-error {
  border-color: #dc2626;
  border-style: solid;
  color: #991b1b;
  background: #fef2f2;
}

.state-block p {
  margin: 0;
}

.request-id {
  margin-top: 0.25rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.75rem;
  color: #64748b;
}
</style>
