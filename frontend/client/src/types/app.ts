// Aurora Relay style reminder: keep data contracts crisp, operational, and easy to scan.
export type ViewKey = "overview" | "tasks" | "tools" | "connectors" | "settings";
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

export type ConnectorProvider = "github" | "revit";
export type ConnectorStatus = "not_configured" | "testing" | "connected" | "needs_attention" | "disabled";

export interface ConnectorRecord {
  id: string;
  provider: ConnectorProvider;
  display_name: string;
  status: ConnectorStatus;
  sort_order: number;
  configuration: Record<string, unknown>;
  credential_configured: boolean;
  capabilities: string[];
  last_tested_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface ConnectorDraft {
  provider: ConnectorProvider;
  display_name: string;
  configuration: Record<string, unknown>;
  credential?: string;
  credential_label?: string;
}

export interface ConnectorActionResult {
  ok: boolean;
  provider: ConnectorProvider;
  action: string;
  message: string;
  data: Record<string, unknown>;
}

export interface RevitPlan {
  operation_id: string;
  state: "planned";
  requires_confirmation: true;
  preview: Record<string, unknown>;
  message: string;
}

export interface RevitOperationResult {
  operation_id: string;
  state: "applied" | "failed" | "rejected";
  message: string;
  result: Record<string, unknown>;
}

export interface ConnectorState {
  connectors: ConnectorRecord[];
  selectedConnectorId: string | null;
  query: string;
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
  pendingRevitPlan: RevitPlan | null;
  setQuery: (query: string) => void;
  selectConnector: (connectorId: string | null) => void;
  setLoading: (value: boolean) => void;
  setSaving: (value: boolean) => void;
  setError: (value: string | null) => void;
  setConnectors: (connectors: ConnectorRecord[]) => void;
  upsertConnector: (connector: ConnectorRecord) => void;
  removeConnector: (connectorId: string) => void;
  setPendingRevitPlan: (plan: RevitPlan | null) => void;
}
