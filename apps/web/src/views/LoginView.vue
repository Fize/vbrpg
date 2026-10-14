<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError, apiErrorMessage, apiRequestId } from "../services/api";
import { login } from "../stores/session";

const router = useRouter();

const username = ref("");
const password = ref("");
const usernameError = ref<string | null>(null);
const passwordError = ref<string | null>(null);
const formError = ref<string | null>(null);
const requestId = ref<string | null>(null);
const submitting = ref(false);

function validate(): boolean {
  usernameError.value = username.value.trim().length === 0 ? "Username is required." : null;
  passwordError.value = password.value.length === 0 ? "Password is required." : null;
  return usernameError.value === null && passwordError.value === null;
}

async function submit(): Promise<void> {
  formError.value = null;
  requestId.value = null;
  if (!validate()) return;

  submitting.value = true;
  try {
    const user = await login(username.value.trim(), password.value);
    await router.push(user.mustChangePassword ? { name: "change-password" } : { name: "lobby" });
  } catch (error) {
    // The API returns one generic message for every credential failure, so the
    // UI must never add detail that hints whether the username exists.
    formError.value = apiErrorMessage(error);
    requestId.value = apiRequestId(error);
    if (error instanceof ApiError && error.code === "RATE_LIMITED") {
      formError.value = "Too many attempts. Please wait a moment and try again.";
    }
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <section class="login-view">
    <h1>Sign in</h1>
    <form class="card" novalidate @submit.prevent="submit">
      <label for="login-username">Username</label>
      <input
        id="login-username"
        v-model="username"
        type="text"
        autocomplete="username"
        :aria-invalid="usernameError !== null"
      />
      <p v-if="usernameError" class="field-error">{{ usernameError }}</p>

      <label for="login-password">Password</label>
      <input
        id="login-password"
        v-model="password"
        type="password"
        autocomplete="current-password"
        :aria-invalid="passwordError !== null"
      />
      <p v-if="passwordError" class="field-error">{{ passwordError }}</p>

      <p v-if="formError" class="form-error" role="alert">{{ formError }}</p>
      <p v-if="requestId" class="request-id">requestId: {{ requestId }}</p>

      <button type="submit" :disabled="submitting">
        {{ submitting ? "Signing in…" : "Sign in" }}
      </button>
    </form>
  </section>
</template>

<style scoped>
.login-view {
  max-width: 360px;
  margin: 3rem auto;
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

.field-error,
.form-error {
  margin: 0;
  font-size: 0.85rem;
  color: #b91c1c;
}

.request-id {
  margin: 0;
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
