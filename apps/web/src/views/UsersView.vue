<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Plus, Refresh } from "@element-plus/icons-vue";
import { api, apiRequestId, type Role, type User } from "../services/api";
import { uiErrorMessage } from "../services/messages";

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

const resetTarget = ref<User | null>(null);
const resetValue = ref("");
const resetError = ref<string | null>(null);
const resetting = ref(false);

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
    loadError.value = uiErrorMessage(error);
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
    createError.value = "用户名至少 3 个字符。";
    return;
  }
  if (createPassword.value.length < 12) {
    createError.value = "临时密码至少 12 位。";
    return;
  }

  creating.value = true;
  try {
    const created = await api.createUser({
      username,
      temporaryPassword: createPassword.value,
      role: createRole.value,
    });
    // 临时密码在此消费，不保留在组件状态中。
    createUsername.value = "";
    createPassword.value = "";
    createRole.value = "user";
    createdNotice.value = `已创建「${created.username}」。临时密码不会再次显示，请立即交付给用户。`;
    await load();
  } catch (error) {
    createError.value = uiErrorMessage(error);
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
    rowError.value = uiErrorMessage(error);
    rowRequestId.value = apiRequestId(error);
  } finally {
    rowBusyId.value = null;
  }
}

async function toggleActive(user: User): Promise<void> {
  await runRowAction(user.id, () => api.updateUser(user.id, { active: !user.active }));
}

async function changeRole(user: User, role: Role): Promise<void> {
  await runRowAction(user.id, () => api.updateUser(user.id, { role }));
}

function openReset(user: User): void {
  resetTarget.value = user;
  resetValue.value = "";
  resetError.value = null;
}

async function confirmReset(): Promise<void> {
  const target = resetTarget.value;
  if (!target) return;
  if (resetValue.value.length < 12) {
    resetError.value = "临时密码至少 12 位。";
    return;
  }
  resetting.value = true;
  try {
    await runRowAction(target.id, () => api.updateUser(target.id, { resetPassword: resetValue.value }));
    if (rowError.value === null) {
      resetTarget.value = null;
      resetValue.value = "";
    }
  } finally {
    resetting.value = false;
  }
}
</script>

<template>
  <section class="users">
    <header class="page-head">
      <h1>用户管理</h1>
      <p class="page-sub">账号由管理员创建，无自助注册；新账号首次登录必须修改初始密码。</p>
    </header>

    <el-card class="panel" shadow="never">
      <template #header>
        <span class="panel-title">创建账号</span>
      </template>

      <el-form label-position="top" novalidate @submit.prevent="createUser">
        <div class="form-row">
          <el-form-item label="用户名">
            <el-input v-model="createUsername" autocomplete="off" placeholder="至少 3 个字符" />
          </el-form-item>
          <el-form-item label="临时密码">
            <el-input
              v-model="createPassword"
              type="password"
              autocomplete="new-password"
              placeholder="至少 12 位"
              show-password
            />
          </el-form-item>
          <el-form-item label="角色">
            <el-select v-model="createRole" class="role-select">
              <el-option label="普通用户" value="user" />
              <el-option label="管理员" value="admin" />
            </el-select>
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

      <p class="hint">临时密码只在创建时显示一次，不会写入日志或接口响应。</p>
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
        v-if="createdNotice"
        class="stack-sm"
        data-testid="created-notice"
        type="success"
        :title="createdNotice"
        :closable="false"
        show-icon
      />
    </el-card>

    <el-card class="panel" shadow="never">
      <template #header>
        <div class="panel-head">
          <span class="panel-title">账号列表</span>
          <el-button text :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
        </div>
      </template>

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

      <el-alert
        v-if="rowError"
        class="stack-sm"
        data-testid="row-error"
        type="error"
        :title="rowError"
        :closable="false"
        show-icon
      />
      <p v-if="rowRequestId" class="meta">请求编号 {{ rowRequestId }}</p>

      <el-table v-loading="loading" :data="users" empty-text="暂无账号">
        <el-table-column prop="username" label="用户名" min-width="140" />
        <el-table-column label="角色" width="110">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'warning' : 'info'" effect="plain" size="small">
              {{ row.role === "admin" ? "管理员" : "普通用户" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.active ? 'success' : 'danger'" effect="plain" size="small">
              {{ row.active ? "正常" : "已停用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="需改密" width="100">
          <template #default="{ row }">
            {{ row.mustChangePassword ? "是" : "否" }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="180">
          <template #default="{ row }">{{ formatDate(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" min-width="300">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button :disabled="rowBusyId === row.id" @click="toggleActive(row)">
                {{ row.active ? "停用" : "启用" }}
              </el-button>
              <el-button
                v-if="row.role === 'admin'"
                :disabled="rowBusyId === row.id"
                @click="changeRole(row, 'user')"
              >
                设为普通用户
              </el-button>
              <el-button
                v-else
                :disabled="rowBusyId === row.id"
                @click="changeRole(row, 'admin')"
              >
                设为管理员
              </el-button>
              <el-button :disabled="rowBusyId === row.id" @click="openReset(row)">
                重置密码
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      :model-value="resetTarget !== null"
      title="重置密码"
      width="420px"
      @update:model-value="resetTarget = null"
    >
      <p class="dialog-note">
        为「{{ resetTarget?.username }}」设置新的临时密码。提交后该账号的全部会话会被撤销。
      </p>
      <el-input
        v-model="resetValue"
        type="password"
        autocomplete="new-password"
        placeholder="至少 12 位"
        show-password
      />
      <p v-if="resetError" class="field-error">{{ resetError }}</p>
      <template #footer>
        <el-button @click="resetTarget = null">取消</el-button>
        <el-button type="primary" :loading="resetting" @click="confirmReset">确认重置</el-button>
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

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-title {
  font-size: var(--text-base);
  font-weight: 600;
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

.role-select {
  width: 140px;
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

.row-actions {
  display: flex;
  flex-wrap: wrap;
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
</style>
