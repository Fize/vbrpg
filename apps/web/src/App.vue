<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { logout, sessionState } from "./stores/session";

const router = useRouter();
const user = computed(() => sessionState.user);
const showNav = computed(() => sessionState.user !== null && !sessionState.user.mustChangePassword);
const isAdmin = computed(() => sessionState.user?.role === "admin");

async function handleLogout(): Promise<void> {
  await logout();
  await router.push({ name: "login" });
}
</script>

<template>
  <div class="app-shell">
    <header v-if="showNav" class="app-nav">
      <nav class="app-nav-links">
        <RouterLink to="/lobby">Lobby</RouterLink>
        <RouterLink v-if="isAdmin" to="/admin/users">Users</RouterLink>
        <RouterLink v-if="isAdmin" to="/admin/providers">Providers</RouterLink>
      </nav>
      <div class="app-nav-user">
        <span>{{ user?.username }} ({{ user?.role }})</span>
        <button type="button" @click="handleLogout">Log out</button>
      </div>
    </header>
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<style>
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family:
    -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: #0f172a;
  background: #f1f5f9;
}

button {
  font: inherit;
  cursor: pointer;
}

input,
select {
  font: inherit;
}
</style>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.app-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 1.25rem;
  background: #0f172a;
  color: #e2e8f0;
}

.app-nav-links {
  display: flex;
  gap: 1rem;
}

.app-nav a {
  color: #e2e8f0;
  text-decoration: none;
}

.app-nav a.router-link-active {
  font-weight: 700;
  text-decoration: underline;
}

.app-nav-user {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.85rem;
}

.app-main {
  max-width: 960px;
  margin: 0 auto;
  padding: 1.5rem;
}
</style>
