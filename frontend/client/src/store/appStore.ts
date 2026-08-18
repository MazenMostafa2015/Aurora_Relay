import { create } from "zustand";
import type { ActivityEvent, Task, Tool, ViewKey, WorkspaceState } from "@/types/app";

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

export const useAppStore = create<WorkspaceState>((set) => ({
  view: "overview",
  draft: "",
  tasks: seededTasks,
  activeTaskId: "task-047",
  events: seededEvents,
  tools: seededTools,
  isConnected: false,
  isTaskSubmitting: false,
  setView: (view: ViewKey) => set({ view }),
  setDraft: (draft: string) => set({ draft }),
  selectTask: (id: string) => set({ activeTaskId: id, view: "tasks" }),
  setConnected: (isConnected: boolean) => set({ isConnected }),
  addEvent: (event: ActivityEvent) => set((state) => ({ events: [event, ...state.events].slice(0, 12) })),
  setTaskSubmitting: (isTaskSubmitting: boolean) => set({ isTaskSubmitting }),
  acceptSubmittedTask: (task: Task) => set((state) => ({
    draft: "",
    view: "tasks",
    activeTaskId: task.id,
    tasks: [task, ...state.tasks.filter((existing) => existing.id !== task.id)],
    events: [{ id: `e-${Date.now()}`, time: "now", label: "Task submitted", detail: "The local coordinator accepted the task.", kind: "signal" as const }, ...state.events].slice(0, 12),
  })),
  recordTaskSubmissionFailure: (message: string) => set((state) => ({
    events: [{ id: `e-${Date.now()}`, time: "now", label: "Task submission failed", detail: message, kind: "approval" as const }, ...state.events].slice(0, 12),
  })),
}));
