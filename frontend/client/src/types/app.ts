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

export type SessionStatus = "anonymous" | "authenticating" | "authenticated" | "error";

export type SessionOperationResult =
  | { ok: true; message?: string }
  | { ok: false; message: string };

export interface SessionState {
  user: User | null;
  token: string | null;
  status: SessionStatus;
  authDialogOpen: boolean;
  authError: string | null;
  initializeSession: () => Promise<SessionOperationResult>;
  openAuthDialog: (reason?: string) => void;
  closeAuthDialog: () => void;
  login: (username: string, password: string) => Promise<SessionOperationResult>;
  register: (username: string, email: string, password: string) => Promise<SessionOperationResult>;
  logout: () => Promise<SessionOperationResult>;
}

export interface WorkspaceState {
  view: ViewKey;
  draft: string;
  tasks: Task[];
  activeTaskId: string;
  events: ActivityEvent[];
  tools: Tool[];
  isConnected: boolean;
  isTaskSubmitting: boolean;
  setView: (view: ViewKey) => void;
  setDraft: (draft: string) => void;
  selectTask: (id: string) => void;
  setConnected: (connected: boolean) => void;
  addEvent: (event: ActivityEvent) => void;
  setTaskSubmitting: (isSubmitting: boolean) => void;
  acceptSubmittedTask: (task: Task) => void;
  recordTaskSubmissionFailure: (message: string) => void;
}
