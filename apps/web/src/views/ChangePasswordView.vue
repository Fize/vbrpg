<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError, apiErrorMessage, apiRequestId } from "../services/api";
import { changePassword, sessionState } from "../stores/session";

const router = useRouter();

const currentPassword = ref("");
const newPassword = ref("");
const confirmPassword = ref("");
const currentError = ref<string | null>(null);
const newError = ref<string | null>(null);
const confirmError = ref<string | null>(null);
const formError = ref<string | null>(null);
const errorCode = ref<string | null>(null);
const requestId = ref<string | null>(null);
const submitting = ref(false);

const forced = sessionState.user?.mustChangePassword === true;

function validate(): boolean {
  currentError.value = currentPassword.value.length === 0 ? "Current password is required." : null;
  newError.value =
    newPassword.value.length < 12 ? "New password must be at least 12 characters." : null;
  confirmError.value =
    confirmPassword.value !== newPassword.value ? "Passwords do not match." : null;
  return currentError.value === null && newError.value === null && confirmError.value === null;
}

async function submit(): Promise<void> {
  formError.value = null;
  errorCode.value = null;
  requestId.value = null;
  if (!validate()) return;

  submitting.value = true;
  try {
    await changePassword(currentPassword.value, newPassword.value);
    router.push({ name: "lobby" });
  } catch (error) {
    formError.value = apiErrorMessage(error);
    requestId.value = apiRequestId(error);
    errorCode.value = error instanceof ApiError ? error.code : null;
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <section class="change-password-view">
    <h1>Change password</h1>
    <p v-if="forced" class="notice">You must set a new password before continuing.</p>
    <form class="card" novalidate @submit.prevent="submit">
      <label for="current-password">Current password</label>
      <input
        id="current-password"
        v-model="currentPassword"
        type="password"
        autocomplete="current-password"
      />
      <p v-if="currentError" class="field-error">{{ currentError }}</p>

      <label for="new-password">New password</label>
      <input id="new-password" v-model="newPassword" type="password" autocomplete="new-password" />
      <p class="hint">At least 12 characters.</p>
      <p v-if="newError" class="field-error">{{ newError }}</p>

      <label for="confirm-password">Confirm new password</label>
      <input
        id="confirm-password"
        v-model="confirmPassword"
        type="password"
        autocomplete="new-password"
      />
      <p v-if="confirmError" class="field-error">{{ confirmError }}</p>

      <p v-if="formError" class="form-error" role="alert">{{ formError }}</p>
      <p v-if="errorCode" class="error-code">code: {{ errorCode }}</p>
      <p v-if="requestId" class="request-id">requestId: {{ requestId }}</p>

      <button type="submit" :disabled="submitting">
        {{ submitting ? "Saving…" : "Save new password" }}
      </button>
    </form>
  </section>
</template>

<style scoped>
.change-password-view {
  max-width: 400px;
  margin: 3rem auto;
}

.notice {
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  background: #fef9c3;
  color: #854d0e;
}

.card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1.25rem;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

input {
  padding: 0.5rem;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
}

.hint,
.field-error,
.form-error,
.error-code,
.request-id {
  margin: 0;
  font-size: 0.85rem;
}

.hint {
  color: #64748b;
}

.field-error,
.form-error {
  color: #b91c1c;
}

.error-code,
.request-id {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.75rem;
  color: #64748b;
}

button {
  margin-top: 0.5rem;
  padding: 0.55rem;
  border: none;
  border-radius: 4px;
  background: #0f172a;
  color: #fff;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
