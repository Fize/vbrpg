import { createRouter, createWebHistory } from "vue-router";
import type { RouteRecordRaw } from "vue-router";
import AdminMatchesView from "../views/AdminMatchesView.vue";
import ChangePasswordView from "../views/ChangePasswordView.vue";
import LobbyView from "../views/LobbyView.vue";
import LoginView from "../views/LoginView.vue";
import MatchView from "../views/MatchView.vue";
import ProvidersView from "../views/ProvidersView.vue";
import UsersView from "../views/UsersView.vue";
import { loadCurrentUser, sessionState } from "../stores/session";
import { setUnauthorizedHandler } from "../services/api";

declare module "vue-router" {
  interface RouteMeta {
    requiresAdmin?: boolean;
    /** A match room is a workspace, not a document: it gets the full window width. */
    fullBleed?: boolean;
  }
}

const routes: RouteRecordRaw[] = [
  { path: "/", redirect: { name: "lobby" } },
  { path: "/login", name: "login", component: LoginView },
  { path: "/change-password", name: "change-password", component: ChangePasswordView },
  { path: "/lobby", name: "lobby", component: LobbyView },
  {
    path: "/matches/:instanceId",
    name: "match",
    component: MatchView,
    meta: { fullBleed: true },
  },
  {
    path: "/admin/users",
    name: "admin-users",
    component: UsersView,
    meta: { requiresAdmin: true },
  },
  {
    path: "/admin/matches",
    name: "admin-matches",
    component: AdminMatchesView,
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

// An expired session must not leave the console showing stale data: any 401 sends the user back
// to the login page, not just the ones a navigation happens to trigger.
setUnauthorizedHandler(() => {
  sessionState.user = null;
  void router.push({ name: "login" });
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
  if (to.name === "login") {
    return { name: "lobby" };
  }
  if (to.meta.requiresAdmin === true && user.role !== "admin") {
    return { name: "lobby" };
  }
  return true;
});

export default router;
