<script setup lang="ts">
import { onMounted, ref } from "vue";
import StateBlock from "../components/StateBlock.vue";
import {
  api,
  apiErrorMessage,
  apiRequestId,
  type Role,
  type User,
} from "../services/api";

const users = ref<User[]>([]);
const loading = ref(false);
const loadError = ref<string | null>(null);
const loadRequestId = ref<string | null>(null);

const createUsername = ref("");
const createPassword = ref("");
const createRole = ref<Role>("user");
const creating = ref(false);
const createError = ref<string | null>(null);
const createRequestId = ref<string | null>(null);
const createdNotice = ref<string | null>(null);

const rowBusyId = ref<string | null>(null);
const rowError = ref<string | null>(null);
const rowRequestId = ref<string | null>(null);

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

async function load(): Promise<void> {
  loading.value = true;
  loadError.value = null;
  loadRequestId.value = null;
  try {
    users.value = await api.listUsers();
  } catch (error) {
    loadError.value = apiErrorMessage(error);
    loadRequestId.value = apiRequestId(error);
  } finally {
    loading.value = false;
  }
}

onMounted(load);

async function createUser(): Promise<void> {
  createError.value = null;
  createRequestId.value = null;
  createdNotice.value = null;

  const username = createUsername.value.trim();
  if (username.length < 3) {
    createError.value = "Username must be at least 3 characters.";
    return;
  }
  if (createPassword.value.length < 12) {
    createError.value = "Temporary password must be at least 12 characters.";
    return;
  }

  creating.value = true;
  try {
    const created = await api.createUser({
      username,
      temporaryPassword: createPassword.value,
      role: createRole.value,
    });
    // The temporary password is consumed here and never kept in component state.
    createUsername.value = "";
    createPassword.value = "";
    createRole.value = "user";
    createdNotice.value = `Created "${created.username}". The temporary password is never displayed again — deliver it to the user now.`;
    await load();
  } catch (error) {
    createError.value = apiErrorMessage(error);
    createRequestId.value = apiRequestId(error);
  } finally {
    creating.value = false;
  }
}

async function runRowAction(userId: string, action: () => Promise<User>): Promise<void> {
  rowBusyId.value = userId;
  rowError.value = null;
  rowRequestId.value = null;
  try {
    await action();
    await load();
  } catch (error) {
    rowError.value = apiErrorMessage(error);
    rowRequestId.value = apiRequestId(error);
  } finally {
    rowBusyId.value = null;
  }
}

async function toggleActive(user: User): Promise<void> {
  if (user.active && !window.confirm(`Disable "${user.username}"? Their sessions will be revoked.`)) {
    return;
  }
  await runRowAction(user.id, () => api.updateUser(user.id, { active: !user.active }));
}

async function changeRole(user: User, role: Role): Promise<void> {
  await runRowAction(user.id, () => api.updateUser(user.id, { role }));
}

async function resetPassword(user: User): Promise<void> {
  const next = window.prompt(`New temporary password for "${user.username}" (at least 12 characters):`);
  if (next === null) return;
  if (next.length < 12) {
    rowError.value = "Temporary password must be at least 12 characters.";
    return;
  }
  if (!window.confirm(`Reset the password for "${user.username}"? All sessions will be revoked.`)) {
    return;
  }
  await runRowAction(user.id, () => api.updateUser(user.id, { resetPassword: next }));
}
</script>

<template>
  <section class="users-view">
    <h1>Users</h1>

    <form class="create-card" novalidate @submit.prevent="createUser">
      <h2>Create user</h2>
      <div class="create-fields">
        <label>
          Username
          <input v-model="createUsername" type="text" autocomplete="off" />
        </label>
        <label>
          Temporary password
          <input v-model="createPassword" type="password" autocomplete="new-password" />
        </label>
        <label>
          Role
          <select v-model="createRole">
            <option value="user">user</option>
            <option value="admin">admin</option>
          </select>
        </label>
        <button type="submit" :disabled="creating">
          {{ creating ? "Creating…" : "Create" }}
        </button>
      </div>
      <p class="hint">Temporary password must be at least 12 characters.</p>
      <p v-if="createError" class="form-error" role="alert">{{ createError }}</p>
      <p v-if="createRequestId" class="request-id">requestId: {{ createRequestId }}</p>
      <p v-if="createdNotice" class="created-notice" role="status">{{ createdNotice }}</p>
    </form>

    <p v-if="rowError" class="form-error" role="alert">{{ rowError }}</p>
    <p v-if="rowRequestId" class="request-id">requestId: {{ rowRequestId }}</p>

    <StateBlock
      :loading="loading"
      :error="loadError"
      :request-id="loadRequestId"
      :empty="users.length === 0"
      loading-text="Loading users…"
      empty-text="No users yet."
    >
      <table class="users-table">
        <thead>
          <tr>
            <th>Username</th>
            <th>Role</th>
            <th>Active</th>
            <th>Must change password</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>{{ user.username }}</td>
            <td>{{ user.role }}</td>
            <td>{{ user.active ? "yes" : "no" }}</td>
            <td>{{ user.mustChangePassword ? "yes" : "no" }}</td>
            <td>{{ formatDate(user.createdAt) }}</td>
            <td class="actions">
              <button type="button" :disabled="rowBusyId === user.id" @click="toggleActive(user)">
                {{ user.active ? "Disable" : "Enable" }}
              </button>
              <button
                v-if="user.role === 'admin'"
                type="button"
                :disabled="rowBusyId === user.id"
                @click="changeRole(user, 'user')"
              >
                Make user
              </button>
              <button
                v-else
                type="button"
                :disabled="rowBusyId === user.id"
                @click="changeRole(user, 'admin')"
              >
                Make admin
              </button>
              <button type="button" :disabled="rowBusyId === user.id" @click="resetPassword(user)">
                Reset password
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </StateBlock>
  </section>
</template>

<style scoped>
.users-view h1 {
  margin-bottom: 1rem;
}

.create-card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  margin-bottom: 1.5rem;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.create-card h2 {
  margin: 0;
  font-size: 1rem;
}

.create-fields {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 0.75rem;
}

label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.85rem;
}

input,
select {
  padding: 0.4rem;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
}

button {
  padding: 0.45rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  background: #f8fafc;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.hint {
  margin: 0;
  font-size: 0.8rem;
  color: #64748b;
}

.form-error {
  margin: 0;
  font-size: 0.85rem;
  color: #b91c1c;
}

.created-notice {
  margin: 0;
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  background: #dcfce7;
  color: #166534;
}

.request-id {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.75rem;
  color: #64748b;
}

.users-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
}

.users-table th,
.users-table td {
  padding: 0.5rem 0.6rem;
  border: 1px solid #e2e8f0;
  text-align: left;
  font-size: 0.85rem;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
</style>
