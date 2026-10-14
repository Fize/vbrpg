<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import StateBlock from "../components/StateBlock.vue";
import { logout, sessionState } from "../stores/session";

const router = useRouter();
const user = computed(() => sessionState.user);

async function handleLogout(): Promise<void> {
  await logout();
  await router.push({ name: "login" });
}
</script>

<template>
  <section class="lobby-view">
    <h1>Lobby</h1>

    <StateBlock :loading="!user" loading-text="Loading session…">
      <div v-if="user" class="user-card">
        <dl>
          <dt>Username</dt>
          <dd>{{ user.username }}</dd>
          <dt>Role</dt>
          <dd>{{ user.role }}</dd>
          <dt>Account status</dt>
          <dd>{{ user.active ? "active" : "disabled" }}</dd>
          <dt>Member since</dt>
          <dd>{{ new Date(user.createdAt).toLocaleString() }}</dd>
        </dl>
        <button type="button" @click="handleLogout">Log out</button>
      </div>

      <StateBlock empty empty-text="The game lobby arrives in a later phase." />
    </StateBlock>
  </section>
</template>

<style scoped>
.lobby-view h1 {
  margin-bottom: 1rem;
}

.user-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  align-items: flex-start;
  padding: 1rem;
  margin-bottom: 1rem;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.35rem 1rem;
  margin: 0;
}

dt {
  font-weight: 600;
  color: #475569;
}

dd {
  margin: 0;
}

button {
  padding: 0.5rem 0.9rem;
  border: none;
  border-radius: 4px;
  background: #0f172a;
  color: #fff;
}
</style>
