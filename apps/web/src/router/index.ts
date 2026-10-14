import { createRouter, createWebHistory } from "vue-router";
import type { RouteRecordRaw } from "vue-router";
import ChangePasswordView from "../views/ChangePasswordView.vue";
import LobbyView from "../views/LobbyView.vue";
import LoginView from "../views/LoginView.vue";
import ProvidersView from "../views/ProvidersView.vue";
import UsersView from "../views/UsersView.vue";
import { loadCurrentUser, sessionState } from "../stores/session";

declare module "vue-router" {
  interface RouteMeta {
    requiresAdmin?: boolean;
  }
}

const routes: RouteRecordRaw[] = [
  { path: "/", redirect: { name: "lobby" } },
  { path: "/login", name: "login", component: LoginView },
  { path: "/change-password", name: "change-password", component: ChangePasswordView },
  { path: "/lobby", name: "lobby", component: LobbyView },
  {
    path: "/admin/users",
    name: "admin-users",
    component: UsersView,
    meta: { requiresAdmin: true },
  },
  {
    path: "/admin/providers",
    name: "admin-providers",
    component: ProvidersView,
    meta: { requiresAdmin: true },
  },
  { path: "/:pathMatch(.*)*", redirect: { name: "lobby" } },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to) => {
  if (!sessionState.initialized) {
    try {
      await loadCurrentUser();
    } catch {
      // An unreachable session lookup is treated as signed out.
    }
  }

  const user = sessionState.user;
  if (!user) {
    return to.name === "login" ? true : { name: "login" };
  }
  if (user.mustChangePassword) {
    return to.name === "change-password" ? true : { name: "change-password" };
  }
  if (to.name === "login" || to.name === "change-password") {
    return { name: "lobby" };
  }
  if (to.meta.requiresAdmin === true && user.role !== "admin") {
    return { name: "lobby" };
  }
  return true;
});

export default router;
