// Aurora Relay style reminder: keep data contracts crisp, operational, and easy to scan.
export type ViewKey = "overview" | "tasks" | "tools" | "connectors" | "agent_loop" | "settings";
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

export type AgentLoopStatus = "idle" | "scheduled" | "running" | "paused" | "stopped" | "completed";
export type AgentLoopArea = "code" | "tests" | "docs" | "ui" | "connectors" | "security";

export interface AgentLoopConfig {
  enabled: boolean;
  dry_run: true;
  schedule: { frequency: "daily"; times_per_day: 5; duration_days: 7; start_time: string; end_time: string; time_zone: "UTC" };
  scope: { areas: AgentLoopArea[]; max_actions_per_loop: number; allow_destructive_actions: false };
  guardrails: { max_loops_total: number; max_consecutive_failures: number; require_approval_for: Array<"deploy" | "release" | "delete" | "external">; rollback_on_error: boolean };
  reporting: { summary_after_each_loop: boolean; daily_digest: boolean; final_report: boolean; notification_channel: "ui" };
  repository: { branch_prefix: string; allow_review_branch_push: boolean; allow_merge: false; allow_deploy: false; allow_release: false };
}

export interface AgentLoopRecord {
  id: string;
  name: string;
  enabled: boolean;
  hard_stop: boolean;
  status: AgentLoopStatus;
  config: AgentLoopConfig;
  runs_completed: number;
  consecutive_failures: number;
  next_run_at: string | null;
  started_at: string | null;
  ends_at: string | null;
  last_error: string | null;
  latest_report: Record<string, unknown> | null;
  created_at: string;
  updated_at: string | null;
}

export interface AgentLoopIteration {
  id: string;
  loop_id: string;
  sequence: number;
  status: "planning" | "completed" | "failed";
  dry_run: boolean;
  branch_name: string | null;
  plan_path: string | null;
  log_path: string | null;
  report_path: string | null;
  plan: Record<string, unknown>;
  actions: Array<Record<string, unknown>>;
  reflection: Record<string, unknown>;
  validation: Record<string, unknown>;
  error: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface AgentLoopState {
  loops: AgentLoopRecord[];
  selectedLoopId: string | null;
  iterations: AgentLoopIteration[];
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
  setLoops: (loops: AgentLoopRecord[]) => void;
  upsertLoop: (loop: AgentLoopRecord) => void;
  selectLoop: (loopId: string | null) => void;
  setIterations: (iterations: AgentLoopIteration[]) => void;
  setLoading: (value: boolean) => void;
  setSaving: (value: boolean) => void;
  setError: (value: string | null) => void;
}
