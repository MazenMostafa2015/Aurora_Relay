import { useMemo } from "react";
import { toast } from "sonner";
import { api, describeApiError } from "@/lib/api";
import { useAppStore } from "@/store/appStore";
import { useConnectorStore } from "@/store/connectorStore";
import { useSessionStore } from "@/store/sessionStore";
import type { ConnectorDraft, ConnectorRecord, RevitPlan, Task, ViewKey } from "@/types/app";

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

export function useConnectorCommands() {
  const setLoading = useConnectorStore((state) => state.setLoading);
  const setSaving = useConnectorStore((state) => state.setSaving);
  const setConnectors = useConnectorStore((state) => state.setConnectors);
  const upsertConnector = useConnectorStore((state) => state.upsertConnector);
  const removeConnector = useConnectorStore((state) => state.removeConnector);
  const setError = useConnectorStore((state) => state.setError);
  const setPendingRevitPlan = useConnectorStore((state) => state.setPendingRevitPlan);

  return useMemo(() => ({
    refresh: async (): Promise<CommandResult> => {
      if (!useSessionStore.getState().token) return failure("authentication", "Sign in to manage connectors.");
      setLoading(true);
      try {
        setConnectors((await api.listConnectors()).connectors);
        setError(null);
        return { ok: true };
      } catch (error) {
        const message = describeApiError(error);
        setError(message);
        return failure("request", message);
      } finally { setLoading(false); }
    },
    create: async (draft: ConnectorDraft): Promise<CommandResult> => {
      if (!draft.display_name.trim()) return failure("validation", "Name the connector before saving it.");
      if (draft.provider === "github" && !draft.credential) return failure("validation", "Add a GitHub token to configure this connector.");
      setSaving(true);
      try {
        const connector = await api.createConnector({ ...draft, display_name: draft.display_name.trim() });
        upsertConnector(connector);
        toast.success(`${connector.display_name} added`);
        return { ok: true };
      } catch (error) {
        const message = describeApiError(error); toast.error(message); return failure("request", message);
      } finally { setSaving(false); }
    },
    test: async (connector: ConnectorRecord): Promise<CommandResult> => {
      setSaving(true);
      try {
        const result = await api.testConnector(connector.id);
        await (async () => { const latest = await api.listConnectors(); setConnectors(latest.connectors); })();
        result.ok ? toast.success(result.message) : toast.error(result.message);
        return result.ok ? { ok: true, message: result.message } : failure("request", result.message);
      } catch (error) { const message = describeApiError(error); toast.error(message); return failure("request", message); } finally { setSaving(false); }
    },
    runAction: async (connector: ConnectorRecord, action: string, input: Record<string, unknown>): Promise<CommandResult> => {
      if (connector.provider !== "github") return failure("validation", "This action is only available for GitHub connectors.");
      if (action === "create_issue" && (!String(input.owner || "").trim() || !String(input.repository || "").trim() || !String(input.title || "").trim())) return failure("validation", "Provide an owner, repository, and issue title.");
      setSaving(true);
      try {
        const providerInput = action === "create_issue" ? { ...input, repo: String(input.repository) } : input;
        const result = await api.runConnectorAction(connector.id, action, providerInput);
        result.ok ? toast.success(result.message) : toast.error(result.message);
        return result.ok ? { ok: true, message: result.message } : failure("request", result.message);
      } catch (error) { const message = describeApiError(error); toast.error(message); return failure("request", message); } finally { setSaving(false); }
    },
    setEnabled: async (connector: ConnectorRecord, enabled: boolean): Promise<CommandResult> => {
      setSaving(true);
      try {
        const updated = await api.updateConnector(connector.id, { enabled });
        upsertConnector(updated);
        toast.success(`${connector.display_name} ${enabled ? "enabled" : "disabled"}`);
        return { ok: true };
      } catch (error) { const message = describeApiError(error); toast.error(message); return failure("request", message); } finally { setSaving(false); }
    },
    move: async (connector: ConnectorRecord, sortOrder: number): Promise<CommandResult> => {
      setSaving(true);
      try {
        const updated = await api.updateConnector(connector.id, { sort_order: sortOrder });
        upsertConnector(updated);
        await (async () => { const latest = await api.listConnectors(); setConnectors(latest.connectors); })();
        return { ok: true };
      } catch (error) { const message = describeApiError(error); toast.error(message); return failure("request", message); } finally { setSaving(false); }
    },
    remove: async (connector: ConnectorRecord): Promise<CommandResult> => {
      setSaving(true);
      try { await api.deleteConnector(connector.id); removeConnector(connector.id); toast.success(`${connector.display_name} removed`); return { ok: true }; }
      catch (error) { const message = describeApiError(error); toast.error(message); return failure("request", message); }
      finally { setSaving(false); }
    },
    planRevitParameter: async (connectorId: string, elementId: number, parameter: string, value: string): Promise<CommandResult & { plan?: RevitPlan }> => {
      if (!Number.isInteger(elementId) || elementId <= 0 || !parameter.trim()) return failure("validation", "Provide a positive element ID and parameter name.");
      setSaving(true);
      try {
        const plan = await api.planRevit(connectorId, { operation: "set_parameter", transaction_name: `Aurora Relay: set ${parameter.trim()}`, set_parameter: { element_id: elementId, parameter: parameter.trim(), value } });
        setPendingRevitPlan(plan);
        return { ok: true, plan };
      } catch (error) { const message = describeApiError(error); toast.error(message); return failure("request", message); } finally { setSaving(false); }
    },
    applyRevit: async (connectorId: string, plan: RevitPlan): Promise<CommandResult> => {
      setSaving(true);
      try {
        const result = await api.applyRevit(connectorId, plan.operation_id);
        setPendingRevitPlan(null);
        result.state === "applied" ? toast.success(result.message) : toast.error(result.message);
        return result.state === "applied" ? { ok: true } : failure("request", result.message);
      } catch (error) { const message = describeApiError(error); toast.error(message); return failure("request", message); } finally { setSaving(false); }
    },
  }), [removeConnector, setConnectors, setError, setLoading, setPendingRevitPlan, setSaving, upsertConnector]);
}
