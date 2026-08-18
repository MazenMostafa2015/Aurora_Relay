import { create } from "zustand";
import { api, describeApiError } from "@/lib/api";
import type { SessionOperationResult, SessionState } from "@/types/app";

const TOKEN_STORAGE_KEY = "aurora-token";

function storedToken(): string | null {
  return typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

function clearStoredToken() {
  if (typeof window !== "undefined") window.localStorage.removeItem(TOKEN_STORAGE_KEY);
}

function saveToken(token: string) {
  if (typeof window !== "undefined") window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export const useSessionStore = create<SessionState>((set, get) => ({
  user: null,
  token: storedToken(),
  status: storedToken() ? "authenticating" : "anonymous",
  authDialogOpen: false,
  authError: null,
  initializeSession: async (): Promise<SessionOperationResult> => {
    if (!get().token) {
      set({ status: "anonymous", user: null, authError: null });
      return { ok: true };
    }
    set({ status: "authenticating", authError: null });
    try {
      const user = await api.me();
      set({ user, status: "authenticated", authError: null });
      return { ok: true };
    } catch {
      clearStoredToken();
      set({ user: null, token: null, status: "anonymous", authError: null });
      return { ok: true, message: "Your saved local session was no longer valid." };
    }
  },
  openAuthDialog: (reason) => set((state) => ({
    authDialogOpen: true,
    authError: reason || null,
    status: state.user ? "authenticated" : "anonymous",
  })),
  closeAuthDialog: () => set((state) => ({
    authDialogOpen: false,
    authError: null,
    status: state.user ? "authenticated" : "anonymous",
  })),
  login: async (username, password): Promise<SessionOperationResult> => {
    set({ status: "authenticating", authError: null });
    try {
      const session = await api.login(username, password);
      saveToken(session.access_token);
      const user = await api.me();
      set({ token: session.access_token, user, status: "authenticated", authDialogOpen: false, authError: null });
      return { ok: true };
    } catch (error) {
      const message = describeApiError(error);
      set({ status: "error", authError: message });
      return { ok: false, message };
    }
  },
  register: async (username, email, password): Promise<SessionOperationResult> => {
    set({ status: "authenticating", authError: null });
    try {
      await api.register(username, email, password);
      const session = await api.login(username, password);
      saveToken(session.access_token);
      const user = await api.me();
      set({ token: session.access_token, user, status: "authenticated", authDialogOpen: false, authError: null });
      return { ok: true };
    } catch (error) {
      const message = describeApiError(error);
      set({ status: "error", authError: message });
      return { ok: false, message };
    }
  },
  logout: async (): Promise<SessionOperationResult> => {
    const token = get().token;
    clearStoredToken();
    set({ user: null, token: null, status: "anonymous", authDialogOpen: false, authError: null });
    if (!token) return { ok: true };
    try {
      await api.logout();
      return { ok: true };
    } catch (error) {
      return { ok: true, message: `Signed out locally. ${describeApiError(error)}` };
    }
  },
}));
