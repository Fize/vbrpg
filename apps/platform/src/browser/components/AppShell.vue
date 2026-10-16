<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Connection, Grid, Lock, SwitchButton, Tickets, User as UserIcon } from "@element-plus/icons-vue";
import { logout, sessionState } from "../stores/session";

const router = useRouter();
const route = useRoute();

const wide = computed(() => route.meta.fullBleed === true);
const user = computed(() => sessionState.user);
const isAdmin = computed(() => user.value?.role === "admin");
const showChrome = computed(() => user.value !== null);
const initial = computed(() => (user.value?.username ?? "?").slice(0, 1).toUpperCase());
const roleLabel = computed(() => (isAdmin.value ? "管理员" : "普通用户"));

async function handleLogout(): Promise<void> {
  await logout();
  await router.push({ name: "login" });
}
</script>

<template>
  <div class="shell">
    <div class="shell-bg" aria-hidden="true"></div>

    <header class="shell-header">
      <div class="shell-header-inner">
        <RouterLink to="/lobby" class="brand">
          <span class="brand-mark">[AI]</span>
          <span class="brand-name">游戏平台</span>
          <span class="brand-tag">控制台</span>
        </RouterLink>

        <nav v-if="showChrome" class="shell-nav" aria-label="主导航">
          <RouterLink to="/lobby" class="nav-link">
            <el-icon><Grid /></el-icon>
            <span>大厅</span>
          </RouterLink>
          <RouterLink v-if="isAdmin" to="/admin/users" class="nav-link">
            <el-icon><UserIcon /></el-icon>
            <span>用户管理</span>
          </RouterLink>
          <RouterLink v-if="isAdmin" to="/admin/matches" class="nav-link">
            <el-icon><Tickets /></el-icon>
            <span>对局运维</span>
          </RouterLink>
          <RouterLink v-if="isAdmin" to="/admin/providers" class="nav-link">
            <el-icon><Connection /></el-icon>
            <span>模型服务</span>
          </RouterLink>
        </nav>

        <div v-if="showChrome" class="shell-user">
          <span class="user-avatar" aria-hidden="true">{{ initial }}</span>
          <span class="user-meta">
            <strong>{{ user?.username }}</strong>
            <em>{{ roleLabel }}</em>
          </span>
          <el-button text :icon="Lock" @click="router.push({ name: 'change-password' })">
            修改密码
          </el-button>
          <el-button text :icon="SwitchButton" @click="handleLogout">退出登录</el-button>
        </div>
      </div>
    </header>

    <main class="shell-main" :class="{ 'is-wide': wide }">
      <slot />
    </main>

    <footer v-if="showChrome" class="shell-footer">
      <span>[AI] 游戏平台 · 控制台</span>
      <span class="footer-status">
        <i class="status-dot" aria-hidden="true"></i>
        服务正常
      </span>
    </footer>
  </div>
</template>

<style scoped>
.shell {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* 单一、静态的品牌氛围：顶部光晕 + 极淡网格，不做动画以免干扰表单阅读。 */
.shell-bg {
  position: fixed;
  inset: 0;
  z-index: -1;
  background:
    radial-gradient(60% 40% at 50% -10%, rgba(0, 240, 255, 0.12), transparent 70%),
    repeating-linear-gradient(
      to right,
      rgba(255, 255, 255, 0.022) 0 1px,
      transparent 1px 64px
    ),
    repeating-linear-gradient(
      to bottom,
      rgba(255, 255, 255, 0.022) 0 1px,
      transparent 1px 64px
    );
}

.shell-header {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  border-bottom: 1px solid var(--border-soft);
  background: var(--surface-glass);
  backdrop-filter: blur(12px);
}

.shell-header-inner {
  display: flex;
  align-items: center;
  gap: var(--space-lg);
  max-width: var(--container-max);
  height: var(--header-height);
  margin: 0 auto;
  padding: 0 var(--space-lg);
}

.brand {
  display: flex;
  align-items: baseline;
  gap: var(--space-xs);
  color: var(--fg);
  white-space: nowrap;
}

.brand:hover {
  color: var(--fg);
}

.brand-mark {
  font-family: var(--font-mono);
  font-size: var(--text-md);
  font-weight: 700;
  background: var(--accent-gradient);
  background-clip: text;
  -webkit-background-clip: text;
  color: transparent;
}

.brand-name {
  font-size: var(--text-md);
  font-weight: 600;
  letter-spacing: var(--tracking-tight);
}

.brand-tag {
  padding: 0 var(--space-2xs);
  border: 1px solid var(--border);
  border-radius: var(--radius-xs);
  font-size: var(--text-xs);
  color: var(--muted);
}

.shell-nav {
  display: flex;
  gap: var(--space-2xs);
  margin-right: auto;
}

.nav-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2xs);
  height: 32px;
  padding: 0 var(--space-sm);
  border-radius: var(--radius-sm);
  font-size: var(--text-base);
  color: var(--fg-2);
  transition: background-color var(--motion-fast) var(--ease-standard);
}

.nav-link:hover {
  background: var(--surface-hover);
  color: var(--fg);
}

.nav-link.router-link-active {
  background: var(--el-color-primary-light-9);
  color: var(--accent);
}

.shell-user {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-left: auto;
}

.user-avatar {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--border-accent);
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--accent);
}

.user-meta {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.user-meta strong {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--fg);
}

.user-meta em {
  font-size: var(--text-xs);
  font-style: normal;
  color: var(--muted);
}

.shell-main {
  flex: 1;
  width: 100%;
  max-width: var(--container-max);
  margin: 0 auto;
  padding: var(--space-xl) var(--space-lg) var(--space-2xl);
}

.shell-main.is-wide {
  max-width: none;
}

.shell-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: var(--container-max);
  width: 100%;
  margin: 0 auto;
  padding: var(--space-md) var(--space-lg) var(--space-lg);
  border-top: 1px solid var(--border-soft);
  font-size: var(--text-xs);
  color: var(--meta);
}

.footer-status {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2xs);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--success);
}

@media (max-width: 720px) {
  .shell-header-inner {
    flex-wrap: wrap;
    height: auto;
    padding: var(--space-sm) var(--space-md);
  }

  .shell-nav {
    order: 3;
    width: 100%;
  }

  .user-meta {
    display: none;
  }

  .shell-main {
    padding: var(--space-lg) var(--space-md) var(--space-xl);
  }
}
</style>
