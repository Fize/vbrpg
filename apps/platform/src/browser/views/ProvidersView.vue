<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Plus, Refresh } from "@element-plus/icons-vue";
import {
  api,
  apiRequestId,
  type ConnectionTestResult,
  type UpdateProviderInput,
} from "../services/api";
import { uiErrorMessage } from "../services/messages";

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

/** Provider-side failure codes, in the reader's language. */
const ERROR_CODE_LABELS: Record<string, string> = {
  timeout: "超时",
  dns_rejected: "域名不可用",
  tls_error: "证书错误",
  unauthorized: "密钥被拒绝",
  rate_limited: "触发限流",
  provider_error: "供应商返回错误",
  invalid_response: "响应无法解析",
};

function errorCodeLabel(code: string): string {
  return ERROR_CODE_LABELS[code] ?? code;
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

/** One confirmation dialog serves both provider and model deletion. */
interface DeleteTarget {
  kind: "provider" | "model";
  id: string;
  label: string;
  busy: boolean;
  error: string | null;
  requestId: string | null;
}

const deleteTarget = ref<DeleteTarget | null>(null);

function askDeleteProvider(draft: ProviderDraft): void {
  deleteTarget.value = {
    kind: "provider",
    id: draft.id,
    label: draft.name,
    busy: false,
    error: null,
    requestId: null,
  };
}

function askDeleteModel(draft: ProviderDraft, model: ModelDraft): void {
  deleteTarget.value = {
    kind: "model",
    id: model.id,
    label: `${draft.name} / ${model.displayName || model.modelId}`,
    busy: false,
    error: null,
    requestId: null,
  };
}

async function confirmDelete(): Promise<void> {
  const target = deleteTarget.value;
  if (!target) return;
  target.busy = true;
  target.error = null;
  try {
    if (target.kind === "provider") {
      await api.deleteProvider(target.id);
    } else {
      await api.deleteProviderModel(target.id);
    }
    deleteTarget.value = null;
    await load();
  } catch (error) {
    target.busy = false;
    target.error = uiErrorMessage(error);
    target.requestId = apiRequestId(error);
  }
}

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
    loadError.value = uiErrorMessage(error);
    loadRequestId.value = apiRequestId(error);
  } finally {
    loading.value = false;
  }
}

onMounted(load);

// 重新加载会替换草稿，因此状态提示按 id 回填。
function setMessage(providerId: string, text: string): void {
  const target = drafts.value.find((draft) => draft.id === providerId);
  if (target) target.message = text;
}

async function createProvider(): Promise<void> {
  createError.value = null;
  createRequestId.value = null;
  createNotice.value = null;

  if (newName.value.trim().length === 0) {
    createError.value = "请填写名称。";
    return;
  }
  if (newBaseUrl.value.trim().length === 0) {
    createError.value = "请填写接口地址。";
    return;
  }
  if (newApiKey.value.length === 0) {
    createError.value = "请填写 API 密钥。";
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
    // 凭据只写不读，立即从组件状态中清除。
    newApiKey.value = "";
    createNotice.value = `已创建 Provider「${created.name}」。密钥只写不读，无法再次查看。`;
    await load();
  } catch (error) {
    createError.value = uiErrorMessage(error);
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
    setMessage(providerId, `已保存「${updated.name}」。`);
  } catch (error) {
    draft.error = uiErrorMessage(error);
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
    draft.error = uiErrorMessage(error);
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
    draft.error = "模型 ID 与显示名都必须填写。";
    return;
  }
  draft.busy = true;
  try {
    await api.createProviderModel(providerId, { modelId, displayName, enabled: true });
    await load();
    setMessage(providerId, `已添加模型「${modelId}」。`);
  } catch (error) {
    draft.error = uiErrorMessage(error);
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
    setMessage(providerId, `已保存模型「${displayName}」。`);
  } catch (error) {
    draft.error = uiErrorMessage(error);
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
    setMessage(providerId, `模型「${model.modelId}」已${nextEnabled ? "启用" : "停用"}。`);
  } catch (error) {
    draft.error = uiErrorMessage(error);
    draft.requestId = apiRequestId(error);
  } finally {
    draft.busy = false;
  }
}
</script>

<template>
  <section class="providers">
    <header class="page-head">
      <h1>模型服务</h1>
      <p class="page-sub">
        平台统一维护供应商凭据：密钥只写不读，不会出现在接口响应、页面或日志中。
      </p>
    </header>

    <el-card class="panel" shadow="never">
      <template #header>
        <span class="panel-title">新增供应商</span>
      </template>

      <el-form label-position="top" novalidate @submit.prevent="createProvider">
        <div class="form-row">
          <el-form-item label="名称">
            <el-input v-model="newName" autocomplete="off" placeholder="例如 primary" />
          </el-form-item>
          <el-form-item label="接口地址">
            <el-input
              v-model="newBaseUrl"
              autocomplete="off"
              placeholder="https://api.example.com/v1"
            />
          </el-form-item>
          <el-form-item label="API 密钥">
            <el-input
              v-model="newApiKey"
              type="password"
              autocomplete="new-password"
              placeholder="sk-…"
              show-password
            />
          </el-form-item>
          <el-button
            type="primary"
            native-type="submit"
            :icon="Plus"
            :loading="creating"
            class="form-submit"
          >
            创建
          </el-button>
        </div>
      </el-form>

      <p class="hint">接口地址必须是 https 端点；仅允许公网地址，内网与回环地址会被拒绝。</p>
      <el-alert
        v-if="createError"
        class="stack-sm"
        data-testid="create-error"
        type="error"
        :title="createError"
        :closable="false"
        show-icon
      />
      <p v-if="createRequestId" class="meta">请求编号 {{ createRequestId }}</p>
      <el-alert
        v-if="createNotice"
        class="stack-sm"
        data-testid="create-notice"
        type="success"
        :title="createNotice"
        :closable="false"
        show-icon
      />
    </el-card>

    <div class="list-toolbar">
      <span class="panel-title">已配置的供应商</span>
      <el-button text :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
    </div>

    <el-alert
      v-if="loadError"
      class="stack-sm"
      data-testid="load-error"
      type="error"
      :title="loadError"
      :closable="false"
      show-icon
    />
    <p v-if="loadRequestId" class="meta">请求编号 {{ loadRequestId }}</p>

    <el-empty v-if="!loading && drafts.length === 0" description="尚未配置 Provider" />

    <el-card v-for="draft in drafts" :key="draft.id" class="panel provider" shadow="never">
      <template #header>
        <div class="provider-head">
          <el-input v-model="draft.name" class="provider-name" autocomplete="off" />
          <el-switch v-model="draft.enabled" active-text="启用" inactive-text="停用" />
          <el-tag :type="draft.secretConfigured ? 'success' : 'info'" effect="plain" size="small">
            {{ draft.secretConfigured ? "密钥已配置" : "未配置密钥" }}
          </el-tag>
        </div>
      </template>

      <div class="field-grid">
        <label class="field">
          <span class="field-label">接口地址</span>
          <el-input v-model="draft.baseUrl" autocomplete="off" />
        </label>
        <label class="field">
          <span class="field-label">替换密钥</span>
          <el-input
            v-model="draft.apiKey"
            type="password"
            autocomplete="new-password"
            :placeholder="draft.secretConfigured ? '••••••' : '填写 API 密钥'"
            show-password
          />
        </label>
      </div>

      <div class="provider-actions">
        <el-button :loading="draft.busy" @click="saveProvider(draft)">保存</el-button>
        <el-button :loading="draft.busy" @click="testConnection(draft)">测试连接</el-button>
        <el-button type="danger" plain :disabled="draft.busy" @click="askDeleteProvider(draft)">
          删除供应商
        </el-button>
      </div>

      <p v-if="draft.testResult" class="test-result" data-testid="test-result">
        <el-tag :type="draft.testResult.ok ? 'success' : 'danger'" effect="plain" size="small">
          {{ draft.testResult.ok ? "连接正常" : "连接失败" }}
        </el-tag>
        <span class="test-detail">
          {{ draft.testResult.latencyMs }} ms ·
          {{
            draft.testResult.errorCode === null
              ? "没有报错"
              : `失败原因 ${errorCodeLabel(draft.testResult.errorCode)}`
          }}
        </span>
      </p>
      <el-alert
        v-if="draft.message"
        class="stack-sm"
        type="success"
        :title="draft.message"
        :closable="false"
        show-icon
      />
      <el-alert
        v-if="draft.error"
        class="stack-sm"
        data-testid="row-error"
        type="error"
        :title="draft.error"
        :closable="false"
        show-icon
      />
      <p v-if="draft.requestId" class="meta">请求编号 {{ draft.requestId }}</p>

      <h3 class="section-title">模型</h3>
      <el-table :data="draft.models" empty-text="尚未配置模型" size="small">
        <el-table-column label="模型 ID" min-width="180">
          <template #default="{ row }">
            <el-input v-model="row.modelId" autocomplete="off" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="显示名" min-width="180">
          <template #default="{ row }">
            <el-input v-model="row.displayName" autocomplete="off" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" effect="plain" size="small">
              {{ row.enabled ? "启用" : "停用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button :disabled="draft.busy" @click="saveModel(draft, row)"> 保存 </el-button>
              <el-button :disabled="draft.busy" @click="toggleModel(draft, row)">
                {{ row.enabled ? "停用" : "启用" }}
              </el-button>
              <el-button
                type="danger"
                plain
                :disabled="draft.busy"
                @click="askDeleteModel(draft, row)"
              >
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="add-model">
        <label class="field">
          <span class="field-label">模型 ID</span>
          <el-input v-model="draft.newModelId" autocomplete="off" size="small" />
        </label>
        <label class="field">
          <span class="field-label">显示名</span>
          <el-input v-model="draft.newModelDisplayName" autocomplete="off" size="small" />
        </label>
        <el-button :disabled="draft.busy" @click="addModel(draft)">添加模型</el-button>
      </div>
    </el-card>

    <el-dialog
      :model-value="deleteTarget !== null"
      :title="deleteTarget?.kind === 'provider' ? '删除供应商' : '删除模型'"
      width="420px"
      @update:model-value="deleteTarget = null"
    >
      <p class="dialog-note">
        <template v-if="deleteTarget?.kind === 'provider'">
          永久删除「{{
            deleteTarget?.label
          }}」及其密钥。供应商下还有模型时删除会被拒绝，请先删除模型。
        </template>
        <template v-else> 永久删除模型「{{ deleteTarget?.label }}」。 </template>
      </p>
      <p v-if="deleteTarget?.error" class="field-error">
        {{ deleteTarget.error
        }}<span v-if="deleteTarget?.requestId"> （{{ deleteTarget.requestId }}）</span>
      </p>
      <template #footer>
        <el-button @click="deleteTarget = null">取消</el-button>
        <el-button type="danger" :loading="deleteTarget?.busy" @click="confirmDelete">
          确认删除
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.page-head {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
  margin-bottom: var(--space-lg);
}

.page-sub {
  font-size: var(--text-base);
  color: var(--muted);
}

.panel {
  margin-bottom: var(--space-md);
}

.panel-title {
  font-size: var(--text-base);
  font-weight: 600;
}

.list-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-sm);
}

.form-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: var(--space-md);
}

.form-row :deep(.el-form-item) {
  margin-bottom: 0;
}

.form-submit {
  margin-bottom: 1px;
}

.hint {
  margin-top: var(--space-sm);
  font-size: var(--text-sm);
  color: var(--muted);
}

.meta {
  margin-top: var(--space-2xs);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--meta);
}

.stack-sm {
  margin-top: var(--space-sm);
}

.provider-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-md);
}

.provider-name {
  width: 220px;
}

.field-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-md);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
}

.field-label {
  font-size: var(--text-sm);
  color: var(--fg-2);
}

.field-grid .field {
  flex: 1 1 260px;
}

.provider-actions {
  display: flex;
  gap: var(--space-xs);
  margin-top: var(--space-md);
}

.test-result {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  margin-top: var(--space-sm);
}

.test-detail {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--muted);
}

.section-title {
  margin: var(--space-lg) 0 var(--space-sm);
  font-size: var(--text-base);
}

.row-actions {
  display: flex;
  gap: var(--space-2xs);
}

.dialog-note {
  margin-bottom: var(--space-sm);
  font-size: var(--text-base);
  color: var(--fg-2);
}

.field-error {
  margin-top: var(--space-2xs);
  font-size: var(--text-sm);
  color: var(--danger);
}

.add-model {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: var(--space-sm);
  margin-top: var(--space-md);
}

.add-model .field {
  flex: 1 1 180px;
}
</style>
