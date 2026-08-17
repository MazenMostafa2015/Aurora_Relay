// Aurora Relay style reminder: keep data contracts crisp, operational, and easy to scan.
export type ViewKey = "overview" | "tasks" | "tools" | "settings";
export type TaskStatus = "executing" | "waiting" | "completed" | "failed" | "paused";

export interface User {
  id: string;
  username: string;
  email: string;
  is_admin?: boolean;
}

export interface TaskStep {
  id: string;
  label: string;
  status: "done" | "active" | "queued" | "waiting";
  detail: string;
  tool?: string;
}

export interface Task {
  id: string;
  title: string;
  status: TaskStatus;
  progress: number;
  createdAt: string;
  duration: string;
  summary: string;
  steps: TaskStep[];
  tags: string[];
}

export interface ActivityEvent {
  id: string;
  time: string;
  label: string;
  detail: string;
  kind: "signal" | "tool" | "thought" | "approval" | "done";
}

export interface Tool {
  name: string;
  description: string;
  server: string;
  schema?: Record<string, unknown>;
}

export interface WorkspaceState {
  user: User | null;
  token: string | null;
  view: ViewKey;
  draft: string;
  tasks: Task[];
  activeTaskId: string;
  events: ActivityEvent[];
  tools: Tool[];
  isConnected: boolean;
  isLoading: boolean;
  setView: (view: ViewKey) => void;
  setDraft: (draft: string) => void;
  submitTask: () => void;
  selectTask: (id: string) => void;
  setConnected: (connected: boolean) => void;
  addEvent: (event: ActivityEvent) => void;
  logout: () => void;
}
