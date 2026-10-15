<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { Lock } from "@element-plus/icons-vue";
import { ApiError, apiRequestId } from "../services/api";
import { uiErrorMessage } from "../services/messages";
import { changePassword } from "../stores/session";

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

function validate(): boolean {
  currentError.value = currentPassword.value.length === 0 ? "请输入当前密码" : null;
  newError.value = newPassword.value.length < 12 ? "新密码至少 12 位" : null;
  confirmError.value = confirmPassword.value !== newPassword.value ? "两次输入的新密码不一致" : null;
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
    formError.value = uiErrorMessage(error);
    requestId.value = apiRequestId(error);
    errorCode.value = error instanceof ApiError ? error.code : null;
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <section class="auth">
    <div class="auth-panel">
      <header class="auth-head">
        <span class="auth-mark">[AI]</span>
        <h1>修改密码</h1>
        <p class="auth-sub">修改后其他会话会被撤销。</p>
      </header>

      <el-form class="auth-form" label-position="top" novalidate @submit.prevent="submit">
        <el-form-item label="当前密码" :error="currentError ?? undefined">
          <el-input
            v-model="currentPassword"
            type="password"
            :prefix-icon="Lock"
            autocomplete="current-password"
          />
        </el-form-item>

        <el-form-item label="新密码" :error="newError ?? undefined">
          <el-input
            v-model="newPassword"
            type="password"
            :prefix-icon="Lock"
            autocomplete="new-password"
          />
          <p class="auth-hint">至少 12 位。</p>
        </el-form-item>

        <el-form-item label="确认新密码" :error="confirmError ?? undefined">
          <el-input
            v-model="confirmPassword"
            type="password"
            :prefix-icon="Lock"
            autocomplete="new-password"
          />
        </el-form-item>

        <el-alert
          v-if="formError"
          class="auth-alert"
          data-testid="auth-error"
          type="error"
          :title="formError"
          :closable="false"
          show-icon
        />
        <p v-if="errorCode" class="auth-meta">错误码 {{ errorCode }}</p>
        <p v-if="requestId" class="auth-meta">请求编号 {{ requestId }}</p>

        <el-button class="auth-submit" type="primary" native-type="submit" :loading="submitting">
          {{ submitting ? "保存中…" : "保存新密码" }}
        </el-button>
      </el-form>
    </div>
  </section>
</template>

<style scoped>
.auth {
  display: flex;
  justify-content: center;
  padding: var(--space-2xl) 0;
}

.auth-panel {
  width: 100%;
  max-width: var(--container-narrow);
  padding: var(--space-xl);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
  box-shadow: var(--shadow-md);
}

.auth-head {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
  margin-bottom: var(--space-lg);
}

.auth-mark {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 700;
  background: var(--accent-gradient);
  background-clip: text;
  -webkit-background-clip: text;
  color: transparent;
}

.auth-sub {
  font-size: var(--text-sm);
  color: var(--muted);
}

.auth-form :deep(.el-form-item) {
  margin-bottom: var(--space-md);
}

.auth-hint {
  margin-top: var(--space-3xs);
  font-size: var(--text-xs);
  color: var(--meta);
}

.auth-alert {
  margin-bottom: var(--space-sm);
}

.auth-meta {
  margin-bottom: var(--space-sm);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--meta);
}

.auth-submit {
  width: 100%;
}
</style>
