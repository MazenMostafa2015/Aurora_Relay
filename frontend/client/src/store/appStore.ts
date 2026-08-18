// Aurora Relay style reminder: state should expose progress, uncertainty, and the next action clearly.
import { create } from "zustand";
import { api, ApiError } from "@/lib/api";
import type { ActivityEvent, Task, Tool, ViewKey, WorkspaceState } from "@/types/app";

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

function readableError(error: unknown) {
  if (error instanceof ApiError && error.status === 401) return "The username or password was not accepted.";
  if (error instanceof Error) return error.message;
  return "The local service could not complete that request.";
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

const seededTasks: Task[] = [
  {
    id: "task-047",
    title: "Map the current AI tooling landscape",
    status: "executing",
    progress: 68,
    createdAt: "Today, 09:42",
    duration: "04m 18s",
    summary: "Comparing primary sources, extracting product signals, and organizing findings into a concise brief.",
    tags: ["research", "browser", "brief"],
    steps: [
      { id: "s1", label: "Frame the research question", status: "done", detail: "Scope and evaluation criteria established." },
      { id: "s2", label: "Collect primary sources", status: "active", detail: "Reviewing 12 of 18 sources.", tool: "browser.search" },
      { id: "s3", label: "Cluster product signals", status: "queued", detail: "Waiting for source pass to complete." },
      { id: "s4", label: "Write the final brief", status: "queued", detail: "Will synthesize evidence and caveats." },
    ],
  },
  {
    id: "task-046",
    title: "Prepare the launch-readiness checklist",
    status: "completed",
    progress: 100,
    createdAt: "Yesterday, 16:08",
    duration: "07m 51s",
    summary: "Turned a release plan into an owner-aware checklist with clear risk gates.",
    tags: ["planning", "checklist"],
    steps: [],
  },
  {
    id: "task-045",
    title: "Inspect the quarterly support themes",
    status: "waiting",
    progress: 41,
    createdAt: "Yesterday, 11:24",
    duration: "02m 02s",
    summary: "Paused before exporting the final table because an approval is required.",
    tags: ["analysis", "approval"],
    steps: [],
  },
];

const seededEvents: ActivityEvent[] = [
  { id: "e1", time: "09:46:12", label: "Source pass in progress", detail: "12 of 18 pages reviewed; two sources need a second look.", kind: "signal" },
  { id: "e2", time: "09:45:34", label: "browser.extract", detail: "Captured the product comparison table from source 11.", kind: "tool" },
  { id: "e3", time: "09:44:51", label: "Agent thought", detail: "The strongest signal is adoption friction, not model capability.", kind: "thought" },
  { id: "e4", time: "09:43:07", label: "Plan accepted", detail: "Four steps created from the brief and ranked by evidence value.", kind: "done" },
];

const seededTools: Tool[] = [
  { name: "browser.search", description: "Search the open web and return ranked result metadata.", server: "Browser" },
  { name: "browser.extract", description: "Extract readable content from a page or selected region.", server: "Browser" },
  { name: "filesystem.write", description: "Write a bounded artifact into the task workspace.", server: "Filesystem" },
  { name: "code_executor.python", description: "Run Python inside the isolated execution sandbox.", server: "Code Executor" },
];

export const useAppStore = create<WorkspaceState>((set, get) => ({
  user: null,
  token: storedToken(),
  authDialogOpen: false,
  authError: null,
  view: "overview",
  draft: "",
  tasks: seededTasks,
  activeTaskId: "task-047",
  events: seededEvents,
  tools: seededTools,
  isConnected: false,
  isLoading: false,
  setView: (view: ViewKey) => set({ view }),
  setDraft: (draft: string) => set({ draft }),
  submitTask: async (context = {}) => {
    const draft = get().draft.trim();
    if (!draft) return false;
    if (!get().token) {
      set({ authDialogOpen: true, authError: "Sign in to submit a task to the local coordinator." });
      return false;
    }
    set({ isLoading: true });
    try {
      const created = mapApiTask(await api.createTask(draft, context));
      set((state) => ({
        draft: "",
        view: "tasks",
        activeTaskId: created.id,
        tasks: [created, ...state.tasks.filter((task) => task.id !== created.id)],
        events: [{ id: `e-${Date.now()}`, time: "now", label: "Task submitted", detail: "The local coordinator accepted the task.", kind: "signal" }, ...state.events],
      }));
      return true;
    } catch (error) {
      set((state) => ({ events: [{ id: `e-${Date.now()}`, time: "now", label: "Task submission failed", detail: readableError(error), kind: "approval" }, ...state.events] }));
      return false;
    } finally {
      set({ isLoading: false });
    }
  },
  selectTask: (id: string) => set({ activeTaskId: id, view: "tasks" }),
  setConnected: (isConnected: boolean) => set({ isConnected }),
  addEvent: (event: ActivityEvent) => set((state) => ({ events: [event, ...state.events].slice(0, 12) })),
  initializeSession: async () => {
    if (!get().token) return;
    set({ isLoading: true });
    try {
      set({ user: await api.me(), authError: null });
    } catch {
      clearStoredToken();
      set({ user: null, token: null });
    } finally {
      set({ isLoading: false });
    }
  },
  openAuthDialog: () => set({ authDialogOpen: true, authError: null }),
  closeAuthDialog: () => set({ authDialogOpen: false, authError: null }),
  login: async (username, password) => {
    set({ isLoading: true, authError: null });
    try {
      const session = await api.login(username, password);
      saveToken(session.access_token);
      const user = await api.me();
      set({ token: session.access_token, user, authDialogOpen: false, authError: null });
      return true;
    } catch (error) {
      set({ authError: readableError(error) });
      return false;
    } finally {
      set({ isLoading: false });
    }
  },
  register: async (username, email, password) => {
    set({ isLoading: true, authError: null });
    try {
      await api.register(username, email, password);
      const session = await api.login(username, password);
      saveToken(session.access_token);
      const user = await api.me();
      set({ token: session.access_token, user, authDialogOpen: false, authError: null });
      return true;
    } catch (error) {
      set({ authError: readableError(error) });
      return false;
    } finally {
      set({ isLoading: false });
    }
  },
  logout: async () => {
    const token = get().token;
    clearStoredToken();
    set({ user: null, token: null, view: "overview", authError: null });
    if (!token) return;
    try {
      await api.logout();
    } catch (error) {
      get().addEvent({ id: `e-${Date.now()}`, time: "now", label: "Remote logout could not be confirmed", detail: readableError(error), kind: "approval" });
    }
  },
}));
