<script setup lang="ts">
import { onMounted, ref } from "vue";
import StateBlock from "../components/StateBlock.vue";
import {
  api,
  apiErrorMessage,
  apiRequestId,
  type ConnectionTestResult,
  type UpdateProviderInput,
} from "../services/api";

interface ModelDraft {
  id: string;
  modelId: string;
  displayName: string;
  enabled: boolean;
}

interface ProviderDraft {
  id: string;
  name: string;
  baseUrl: string;
  enabled: boolean;
  secretConfigured: boolean;
  apiKey: string;
  models: ModelDraft[];
  newModelId: string;
  newModelDisplayName: string;
  message: string | null;
  error: string | null;
  requestId: string | null;
  busy: boolean;
  testResult: ConnectionTestResult | null;
}

const drafts = ref<ProviderDraft[]>([]);
const loading = ref(false);
const loadError = ref<string | null>(null);
const loadRequestId = ref<string | null>(null);

const newName = ref("");
const newBaseUrl = ref("");
const newApiKey = ref("");
const creating = ref(false);
const createError = ref<string | null>(null);
const createRequestId = ref<string | null>(null);
const createNotice = ref<string | null>(null);

async function load(): Promise<void> {
  loading.value = true;
  loadError.value = null;
  loadRequestId.value = null;
  try {
    const providers = await api.listProviders();
    const previousTests = new Map(drafts.value.map((draft) => [draft.id, draft.testResult]));
    drafts.value = providers.map((provider) => ({
      id: provider.id,
      name: provider.name,
      baseUrl: provider.baseUrl,
      enabled: provider.enabled,
      secretConfigured: provider.secretConfigured,
      apiKey: "",
      models: provider.models.map((model) => ({
        id: model.id,
        modelId: model.modelId,
        displayName: model.displayName,
        enabled: model.enabled,
      })),
      newModelId: "",
      newModelDisplayName: "",
      message: null,
      error: null,
      requestId: null,
      busy: false,
      testResult: previousTests.get(provider.id) ?? null,
    }));
  } catch (error) {
    loadError.value = apiErrorMessage(error);
    loadRequestId.value = apiRequestId(error);
  } finally {
    loading.value = false;
  }
}

onMounted(load);

// Reloading replaces the drafts, so status messages are re-applied by id.
function setMessage(providerId: string, text: string): void {
  const target = drafts.value.find((draft) => draft.id === providerId);
  if (target) target.message = text;
}

async function createProvider(): Promise<void> {
  createError.value = null;
  createRequestId.value = null;
  createNotice.value = null;

  if (newName.value.trim().length === 0) {
    createError.value = "Name is required.";
    return;
  }
  if (newBaseUrl.value.trim().length === 0) {
    createError.value = "Base URL is required.";
    return;
  }
  if (newApiKey.value.length === 0) {
    createError.value = "API key is required.";
    return;
  }

  creating.value = true;
  try {
    const created = await api.createProvider({
      name: newName.value.trim(),
      baseUrl: newBaseUrl.value.trim(),
      apiKey: newApiKey.value,
    });
    newName.value = "";
    newBaseUrl.value = "";
    // Credentials are write-only; drop the value from component state at once.
    newApiKey.value = "";
    createNotice.value = `Provider "${created.name}" created. The API key is stored write-only and cannot be read back.`;
    await load();
  } catch (error) {
    createError.value = apiErrorMessage(error);
    createRequestId.value = apiRequestId(error);
  } finally {
    creating.value = false;
  }
}

async function saveProvider(draft: ProviderDraft): Promise<void> {
  const providerId = draft.id;
  draft.busy = true;
  draft.message = null;
  draft.error = null;
  draft.requestId = null;
  try {
    const patch: UpdateProviderInput = {
      name: draft.name.trim(),
      baseUrl: draft.baseUrl.trim(),
      enabled: draft.enabled,
    };
    if (draft.apiKey.length > 0) patch.apiKey = draft.apiKey;
    const updated = await api.updateProvider(providerId, patch);
    draft.apiKey = "";
    await load();
    setMessage(providerId, `Saved "${updated.name}".`);
  } catch (error) {
    draft.error = apiErrorMessage(error);
    draft.requestId = apiRequestId(error);
  } finally {
    draft.busy = false;
  }
}

async function testConnection(draft: ProviderDraft): Promise<void> {
  draft.busy = true;
  draft.message = null;
  draft.error = null;
  draft.requestId = null;
  try {
    draft.testResult = await api.testProvider(draft.id);
    draft.apiKey = "";
  } catch (error) {
    draft.error = apiErrorMessage(error);
    draft.requestId = apiRequestId(error);
  } finally {
    draft.busy = false;
  }
}

async function addModel(draft: ProviderDraft): Promise<void> {
  const providerId = draft.id;
  const modelId = draft.newModelId.trim();
  const displayName = draft.newModelDisplayName.trim();
  draft.message = null;
  draft.error = null;
  draft.requestId = null;
  if (modelId.length === 0 || displayName.length === 0) {
    draft.error = "Model id and display name are required.";
    return;
  }
  draft.busy = true;
  try {
    await api.createProviderModel(providerId, { modelId, displayName });
    await load();
    setMessage(providerId, `Added model "${modelId}".`);
  } catch (error) {
    draft.error = apiErrorMessage(error);
    draft.requestId = apiRequestId(error);
  } finally {
    draft.busy = false;
  }
}

async function saveModel(draft: ProviderDraft, model: ModelDraft): Promise<void> {
  const providerId = draft.id;
  const displayName = model.displayName.trim();
  draft.message = null;
  draft.error = null;
  draft.requestId = null;
  draft.busy = true;
  try {
    await api.updateProviderModel(model.id, {
      modelId: model.modelId.trim(),
      displayName,
    });
    await load();
    setMessage(providerId, `Saved model "${displayName}".`);
  } catch (error) {
    draft.error = apiErrorMessage(error);
    draft.requestId = apiRequestId(error);
  } finally {
    draft.busy = false;
  }
}

async function toggleModel(draft: ProviderDraft, model: ModelDraft): Promise<void> {
  const providerId = draft.id;
  const nextEnabled = !model.enabled;
  draft.message = null;
  draft.error = null;
  draft.requestId = null;
  draft.busy = true;
  try {
    await api.updateProviderModel(model.id, { enabled: nextEnabled });
    await load();
    setMessage(providerId, `Model "${model.modelId}" ${nextEnabled ? "enabled" : "disabled"}.`);
  } catch (error) {
    draft.error = apiErrorMessage(error);
    draft.requestId = apiRequestId(error);
  } finally {
    draft.busy = false;
  }
}
</script>

<template>
  <section class="providers-view">
    <h1>Providers</h1>

    <form class="create-card" novalidate @submit.prevent="createProvider">
      <h2>Create provider</h2>
      <div class="create-fields">
        <label>
          Name
          <input v-model="newName" type="text" autocomplete="off" />
        </label>
        <label>
          Base URL
          <input v-model="newBaseUrl" type="text" autocomplete="off" placeholder="https://…" />
        </label>
        <label>
          API key
          <input v-model="newApiKey" type="password" autocomplete="new-password" />
        </label>
        <button type="submit" :disabled="creating">
          {{ creating ? "Creating…" : "Create" }}
        </button>
      </div>
      <p class="hint">Base URL must be an https endpoint. The API key is write-only.</p>
      <p v-if="createError" class="form-error" role="alert">{{ createError }}</p>
      <p v-if="createRequestId" class="request-id">requestId: {{ createRequestId }}</p>
      <p v-if="createNotice" class="notice" role="status">{{ createNotice }}</p>
    </form>

    <StateBlock
      :loading="loading"
      :error="loadError"
      :request-id="loadRequestId"
      :empty="drafts.length === 0"
      loading-text="Loading providers…"
      empty-text="No providers configured yet."
    >
      <article v-for="draft in drafts" :key="draft.id" class="provider-card">
        <header class="provider-header">
          <label class="inline">
            Name
            <input v-model="draft.name" type="text" autocomplete="off" />
          </label>
          <label class="inline">
            <input v-model="draft.enabled" type="checkbox" />
            Enabled
          </label>
          <span class="badge" :class="{ configured: draft.secretConfigured }">
            {{ draft.secretConfigured ? "secret configured" : "no secret" }}
          </span>
        </header>

        <label>
          Base URL
          <input v-model="draft.baseUrl" type="text" autocomplete="off" />
        </label>

        <label>
          Replace API key
          <input
            v-model="draft.apiKey"
            type="password"
            autocomplete="new-password"
            :placeholder="draft.secretConfigured ? '••••••' : 'API key'"
          />
        </label>

        <div class="provider-actions">
          <button type="button" :disabled="draft.busy" @click="saveProvider(draft)">Save</button>
          <button type="button" :disabled="draft.busy" @click="testConnection(draft)">
            Test connection
          </button>
        </div>

        <p v-if="draft.testResult" class="test-result">
          Test: {{ draft.testResult.ok ? "ok" : "failed" }} · {{ draft.testResult.latencyMs }} ms ·
          errorCode: {{ draft.testResult.errorCode ?? "none" }}
        </p>
        <p v-if="draft.message" class="notice" role="status">{{ draft.message }}</p>
        <p v-if="draft.error" class="form-error" role="alert">{{ draft.error }}</p>
        <p v-if="draft.requestId" class="request-id">requestId: {{ draft.requestId }}</p>

        <h3>Models</h3>
        <p v-if="draft.models.length === 0" class="hint">No models configured.</p>
        <table v-else class="models-table">
          <thead>
            <tr>
              <th>Model id</th>
              <th>Display name</th>
              <th>Enabled</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="model in draft.models" :key="model.id">
              <td><input v-model="model.modelId" type="text" autocomplete="off" /></td>
              <td><input v-model="model.displayName" type="text" autocomplete="off" /></td>
              <td>{{ model.enabled ? "yes" : "no" }}</td>
              <td class="model-actions">
                <button type="button" :disabled="draft.busy" @click="saveModel(draft, model)">
                  Save
                </button>
                <button type="button" :disabled="draft.busy" @click="toggleModel(draft, model)">
                  {{ model.enabled ? "Disable" : "Enable" }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <div class="add-model">
          <label>
            New model id
            <input v-model="draft.newModelId" type="text" autocomplete="off" />
          </label>
          <label>
            Display name
            <input v-model="draft.newModelDisplayName" type="text" autocomplete="off" />
          </label>
          <button type="button" :disabled="draft.busy" @click="addModel(draft)">Add model</button>
        </div>
      </article>
    </StateBlock>
  </section>
</template>

<style scoped>
.providers-view h1 {
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

.create-card h2,
.provider-card h3 {
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

label.inline {
  flex-direction: row;
  align-items: center;
}

input {
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

.provider-card {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 1rem;
  margin-bottom: 1rem;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.provider-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 1rem;
}

.badge {
  padding: 0.2rem 0.5rem;
  border-radius: 999px;
  font-size: 0.75rem;
  background: #f1f5f9;
  color: #64748b;
}

.badge.configured {
  background: #dcfce7;
  color: #166534;
}

.provider-actions,
.model-actions {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.models-table {
  width: 100%;
  border-collapse: collapse;
}

.models-table th,
.models-table td {
  padding: 0.35rem 0.5rem;
  border: 1px solid #e2e8f0;
  text-align: left;
  font-size: 0.85rem;
}

.add-model {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 0.5rem;
}

.hint,
.test-result {
  margin: 0;
  font-size: 0.8rem;
  color: #64748b;
}

.form-error {
  margin: 0;
  font-size: 0.85rem;
  color: #b91c1c;
}

.notice {
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
</style>
