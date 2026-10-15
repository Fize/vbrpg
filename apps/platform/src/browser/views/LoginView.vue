<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { Lock, User as UserIcon } from "@element-plus/icons-vue";
import { apiRequestId } from "../services/api";
import { uiErrorMessage } from "../services/messages";
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
  usernameError.value = username.value.trim().length === 0 ? "请输入用户名" : null;
  passwordError.value = password.value.length === 0 ? "请输入密码" : null;
  return usernameError.value === null && passwordError.value === null;
}

async function submit(): Promise<void> {
  formError.value = null;
  requestId.value = null;
  if (!validate()) return;

  submitting.value = true;
  try {
    await login(username.value.trim(), password.value);
    await router.push({ name: "lobby" });
  } catch (error) {
    // 服务端对所有凭据失败返回同一条信息，前端不得补充任何暗示用户名是否存在的细节。
    formError.value = uiErrorMessage(error);
    requestId.value = apiRequestId(error);
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
        <h1>登录</h1>
        <p class="auth-sub">账号由管理员创建。登录后进入游戏大厅。</p>
      </header>

      <el-form class="auth-form" label-position="top" novalidate @submit.prevent="submit">
        <el-form-item label="用户名" :error="usernameError ?? undefined">
          <el-input
            v-model="username"
            :prefix-icon="UserIcon"
            autocomplete="username"
            placeholder="请输入用户名"
          />
        </el-form-item>

        <el-form-item label="密码" :error="passwordError ?? undefined">
          <el-input
            v-model="password"
            type="password"
            :prefix-icon="Lock"
            autocomplete="current-password"
            placeholder="请输入密码"
            show-password
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
        <p v-if="requestId" class="auth-meta">请求编号 {{ requestId }}</p>

        <el-button class="auth-submit" type="primary" native-type="submit" :loading="submitting">
          {{ submitting ? "登录中…" : "登录" }}
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
