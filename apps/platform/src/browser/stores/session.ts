import { reactive } from "vue";
import { ApiError, api, setCsrfToken, type LoginResult, type User } from "../services/api";

interface SessionState {
  user: User | null;
  loading: boolean;
  initialized: boolean;
}

export const sessionState = reactive<SessionState>({
  user: null,
  loading: false,
  initialized: false,
});

function applyLoginResult(result: LoginResult): User {
  sessionState.user = result.user;
  sessionState.initialized = true;
  return result.user;
}

export async function login(username: string, password: string): Promise<User> {
  sessionState.loading = true;
  try {
    return applyLoginResult(await api.login(username, password));
  } finally {
    sessionState.loading = false;
  }
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<User> {
  sessionState.loading = true;
  try {
    return applyLoginResult(await api.changePassword(currentPassword, newPassword));
  } finally {
    sessionState.loading = false;
  }
}

/** Resolves to the current user, or null for an expired or absent session. */
export async function loadCurrentUser(): Promise<User | null> {
  sessionState.loading = true;
  try {
    const user = await api.loadCurrentUser();
    sessionState.user = user;
    return user;
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      sessionState.user = null;
      return null;
    }
    throw error;
  } finally {
    sessionState.loading = false;
    sessionState.initialized = true;
  }
}

export async function logout(): Promise<void> {
  try {
    await api.logout();
  } finally {
    // Local state is cleared even when the server call fails, so the UI never
    // keeps presenting a session the user asked to end.
    setCsrfToken(null);
    sessionState.user = null;
    sessionState.initialized = true;
  }
}

export function isAuthenticated(): boolean {
  return sessionState.user !== null;
}

export function isAdmin(): boolean {
  return sessionState.user?.role === "admin";
}
