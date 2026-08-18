import { useMemo } from "react";
import { toast } from "sonner";
import { api, describeApiError } from "@/lib/api";
import { useAppStore } from "@/store/appStore";
import { useSessionStore } from "@/store/sessionStore";
import type { Task, ViewKey } from "@/types/app";

export type CommandResult =
  | { ok: true; message?: string }
  | { ok: false; code: "validation" | "authentication" | "request"; message: string };

function failure(code: Extract<CommandResult, { ok: false }>['code'], message: string): CommandResult {
  return { ok: false, code, message };
}

function mapApiTask(value: Record<string, unknown>): Task {
  const rawStatus = String(value.status || "waiting");
  const status: Task["status"] = rawStatus === "executing" || rawStatus === "completed" || rawStatus === "failed" || rawStatus === "paused"
    ? rawStatus
    : "waiting";
  const rawSteps = Array.isArray(value.steps) ? value.steps : [];
  return {
    id: String(value.id),
    title: String(value.order || "Untitled task"),
    status,
    progress: Math.max(0, Math.min(100, Math.round(Number(value.progress || 0) * (Number(value.progress || 0) <= 1 ? 100 : 1)))),
    createdAt: value.created_at ? new Date(String(value.created_at)).toLocaleString() : "Just now",
    duration: "Just now",
    summary: typeof value.summary === "string" ? value.summary : "The local coordinator is preparing this task.",
    tags: ["local API"],
    steps: rawSteps.map((step, index) => {
      const item = step && typeof step === "object" ? step as Record<string, unknown> : {};
      const stepStatus = String(item.status || "pending");
      return {
        id: String(item.id || `step-${index}`),
        label: String(item.description || `Step ${index + 1}`),
        status: stepStatus === "completed" ? "done" : stepStatus === "executing" ? "active" : stepStatus === "waiting_approval" ? "waiting" : "queued",
        detail: typeof item.error === "string" ? item.error : "Awaiting local execution.",
      };
    }),
  };
}

export function useAuthCommands() {
  const initializeSession = useSessionStore((state) => state.initializeSession);
  const openAuthDialog = useSessionStore((state) => state.openAuthDialog);
  const closeAuthDialog = useSessionStore((state) => state.closeAuthDialog);
  const login = useSessionStore((state) => state.login);
  const register = useSessionStore((state) => state.register);
  const logout = useSessionStore((state) => state.logout);

  return useMemo(() => ({
    hydrate: async (): Promise<CommandResult> => {
      const result = await initializeSession();
      return result.ok ? { ok: true, message: result.message } : failure("request", result.message);
    },
    openDialog: (reason?: string) => openAuthDialog(reason),
    closeDialog: () => closeAuthDialog(),
    signIn: async (username: string, password: string): Promise<CommandResult> => {
      if (!username.trim() || !password) {
        const message = "Enter both a username and password to continue.";
        openAuthDialog(message);
        toast.error(message);
        return failure("validation", message);
      }
      const result = await login(username.trim(), password);
      if (result.ok) toast.success("Signed in to the local workspace");
      else toast.error(result.message);
      return result.ok ? { ok: true } : failure("request", result.message);
    },
    signUp: async (username: string, email: string, password: string): Promise<CommandResult> => {
      if (!username.trim() || !email.includes("@") || password.length < 8) {
        const message = "Use a username, a valid email address, and a password with at least 8 characters.";
        openAuthDialog(message);
        toast.error(message);
        return failure("validation", message);
      }
      const result = await register(username.trim(), email.trim(), password);
      if (result.ok) toast.success("Account created and signed in");
      else toast.error(result.message);
      return result.ok ? { ok: true } : failure("request", result.message);
    },
    signOut: async (): Promise<CommandResult> => {
      const result = await logout();
      useAppStore.getState().setView("overview");
      if (result.message) toast.warning(result.message);
      else toast.success("Signed out of this workspace");
      return { ok: true, message: result.message };
    },
  }), [closeAuthDialog, initializeSession, login, logout, openAuthDialog, register]);
}

export function useTaskCommands() {
  const setTaskSubmitting = useAppStore((state) => state.setTaskSubmitting);
  const acceptSubmittedTask = useAppStore((state) => state.acceptSubmittedTask);
  const recordTaskSubmissionFailure = useAppStore((state) => state.recordTaskSubmissionFailure);

  return useMemo(() => ({
    submitTask: async (context: Record<string, unknown> = {}): Promise<CommandResult> => {
      const draft = useAppStore.getState().draft.trim();
      if (!draft) {
        const message = "Give the agent a direction first.";
        toast.error(message);
        return failure("validation", message);
      }
      if (!useSessionStore.getState().token) {
        const message = "Sign in to submit a task to the local coordinator.";
        useSessionStore.getState().openAuthDialog(message);
        toast.error(message);
        return failure("authentication", message);
      }
      setTaskSubmitting(true);
      try {
        const task = mapApiTask(await api.createTask(draft, context));
        acceptSubmittedTask(task);
        toast.success("Task queued with the local coordinator");
        return { ok: true };
      } catch (error) {
        const message = describeApiError(error);
        recordTaskSubmissionFailure(message);
        toast.error(message);
        return failure("request", message);
      } finally {
        setTaskSubmitting(false);
      }
    },
  }), [acceptSubmittedTask, recordTaskSubmissionFailure, setTaskSubmitting]);
}

export function useNavigationCommands() {
  const setView = useAppStore((state) => state.setView);
  const selectTask = useAppStore((state) => state.selectTask);
  const openAuthDialog = useSessionStore((state) => state.openAuthDialog);
  const user = useSessionStore((state) => state.user);

  return useMemo(() => ({
    goTo: (view: ViewKey) => {
      setView(view);
      return { ok: true } as const;
    },
    openTask: (taskId: string) => {
      selectTask(taskId);
      return { ok: true } as const;
    },
    openAccount: () => {
      if (user) {
        setView("settings");
        return { ok: true } as const;
      }
      openAuthDialog();
      return failure("authentication", "Sign in to manage your workspace settings.");
    },
  }), [openAuthDialog, selectTask, setView, user]);
}
