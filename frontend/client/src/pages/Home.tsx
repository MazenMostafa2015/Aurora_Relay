// Aurora Relay style reminder: editorial command center, graphite surfaces, relay cyan, saffron for human attention.
import { ChangeEvent, KeyboardEvent, lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useAppStore } from "@/store/appStore";
import { useConnectorStore } from "@/store/connectorStore";
import { useSessionStore } from "@/store/sessionStore";
import { useAuthCommands, useConnectorCommands, useNavigationCommands, useTaskCommands } from "@/lib/commands";
import { useTaskStream } from "@/hooks/useTaskStream";
import type { ConnectorDraft, ConnectorRecord, Task, ViewKey } from "@/types/app";
import { toast } from "sonner";
import { ManusDialog } from "@/components/ManusDialog";
import { ConnectorsView } from "@/components/ConnectorsView";
import {
  Activity, ArrowUpRight, Check, ChevronDown, CircleHelp, Clock3, Command, FileText,
  CirclePlus, Gauge, Github, Hexagon, LayoutDashboard, LogIn, LogOut, Menu, MoreHorizontal, Play, Plus,
  Search, Settings2, ShieldCheck, Sparkles, TerminalSquare, UserRound, Wifi, Wrench, Boxes, RefreshCw, Trash2, Building2, Bot, BadgeCheck, Puzzle,
} from "lucide-react";

const navItems: { key: ViewKey; label: string; icon: typeof LayoutDashboard }[] = [
  { key: "overview", label: "Overview", icon: LayoutDashboard },
  { key: "tasks", label: "Task desk", icon: Activity },
  { key: "tools", label: "Tool explorer", icon: Wrench },
  { key: "connectors", label: "Connectors", icon: Boxes },
  { key: "health", label: "Operations", icon: Gauge },
  { key: "extensions", label: "Extensions", icon: Puzzle },
  { key: "agent_loop", label: "Agent loop", icon: Bot },
  { key: "release_evidence", label: "Release evidence", icon: BadgeCheck },
  { key: "settings", label: "Settings", icon: Settings2 },
];

const AgentLoopView = lazy(() => import("@/components/AgentLoopView").then((module) => ({ default: module.AgentLoopView })));
const ReleaseEvidenceView = lazy(() => import("@/components/ReleaseEvidenceView").then((module) => ({ default: module.ReleaseEvidenceView })));
const HealthDashboardView = lazy(() => import("@/components/HealthDashboardView").then((module) => ({ default: module.HealthDashboardView })));
const ExtensionsView = lazy(() => import("@/components/ExtensionsView").then((module) => ({ default: module.ExtensionsView })));

function StatusPill({ status }: { status: Task["status"] }) {
  const copy = { executing: "Running", waiting: "Needs review", completed: "Complete", failed: "Failed", paused: "Paused" }[status];
  return <span className={`status-pill status-${status}`}><span className="status-dot" />{copy}</span>;
}

function Sidebar() {
  const view = useAppStore((state) => state.view);
  const user = useSessionStore((state) => state.user);
  const { goTo, openAccount } = useNavigationCommands();
  const { openDialog, signOut } = useAuthCommands();
  return <aside className="sidebar">
    <div className="brand-lockup"><div className="brand-mark" aria-hidden="true"><span className="brand-sigil" /></div><div><div className="brand-name">AURORA <span>RELAY</span></div><div className="brand-caption">AI command center</div></div></div>
    <div className="sidebar-section-label">Workspace</div>
    <nav className="nav-list" aria-label="Workspace navigation">
      {navItems.map(({ key, label, icon: Icon }) => <button type="button" key={key} className={`nav-item ${view === key ? "active" : ""}`} onClick={() => goTo(key)}><Icon size={17} strokeWidth={1.8} /><span>{label}</span>{key === "tasks" && <span className="nav-count">03</span>}</button>)}
    </nav>
    <div className="sidebar-divider" />
    <div className="sidebar-section-label">Pinned</div>
    <button type="button" className="pin-item" onClick={() => { goTo("tasks"); toast.info("Task desk opened"); }}><span className="pin-swatch cyan" />Research sprint <span className="pin-meta">68%</span></button>
    <button type="button" className="pin-item" onClick={() => { goTo("tasks"); toast.info("Approval queue opened"); }}><span className="pin-swatch saffron" />Approval queue <span className="pin-meta">01</span></button>
    <div className="sidebar-bottom"><div className="connection-card"><div className="connection-top"><span className="connection-indicator" />Local workspace</div><div className="connection-detail">API fallback mode · safe to explore</div></div><button type="button" className="profile-row" onClick={() => openAccount()}><span className="avatar">{user?.username.slice(0, 2).toUpperCase() || "AR"}</span><span className="profile-copy"><strong>{user?.username || "Guest operator"}</strong><small>{user?.email || "Sign in to connect"}</small></span><MoreHorizontal size={16} /></button>{user ? <button type="button" className="logout-btn" onClick={() => void signOut()}><LogOut size={15} /> Sign out</button> : <button type="button" className="logout-btn" onClick={() => openDialog()}><LogIn size={15} /> Sign in</button>}</div>
  </aside>;
}

function Header({ title, eyebrow }: { title: string; eyebrow: string }) {
  const isConnected = useAppStore((state) => state.isConnected);
  const user = useSessionStore((state) => state.user);
  const { goTo, openAccount } = useNavigationCommands();
  return <header className="workspace-header"><div><div className="eyebrow"><span className="eyebrow-line" />{eyebrow}</div><h1>{title}</h1></div><div className="header-actions"><div className="live-status"><span className={`live-orb ${isConnected ? "connected" : ""}`} />{isConnected ? "Live link" : "Local preview"}</div><button type="button" className="icon-button" aria-label="Help" onClick={() => toast.info("Aurora Relay keeps execution on this device; sign in to submit tasks.")}><CircleHelp size={18} /></button><button type="button" className="icon-button" aria-label="Open tool explorer" onClick={() => { goTo("tools"); toast.info("Tool explorer opened"); }}><Command size={18} /></button><button type="button" className="header-avatar" aria-label={user ? "Open settings" : "Sign in"} onClick={() => openAccount()}>{user?.username.slice(0, 2).toUpperCase() || <UserRound size={16} />}</button></div></header>;
}

function Composer() {
  const draft = useAppStore((state) => state.draft);
  const setDraft = useAppStore((state) => state.setDraft);
  const isTaskSubmitting = useAppStore((state) => state.isTaskSubmitting);
  const { submitTask } = useTaskCommands();
  const [expanded, setExpanded] = useState(false);
  const [attachmentName, setAttachmentName] = useState("");
  const attachmentInput = useRef<HTMLInputElement>(null);
  const submit = async () => { const result = await submitTask(attachmentName ? { attachment_name: attachmentName } : {}); if (result.ok) setAttachmentName(""); };
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => { if ((event.metaKey || event.ctrlKey) && event.key === "Enter") { event.preventDefault(); void submit(); } };
  const selectAttachment = (event: ChangeEvent<HTMLInputElement>) => setAttachmentName(event.target.files?.[0]?.name || "");
  return <section className="composer-shell">
    <div className="composer-art" />
    <div className="composer-content"><div className="composer-kicker"><Sparkles size={14} /> New agent task <span className="composer-rule" /></div><h2>Give the agent<br /><em>a direction.</em></h2><p className="composer-note">Describe the outcome you want. Aurora will frame the work, choose tools, and keep every meaningful move visible.</p><div className={`composer-input-wrap ${expanded ? "expanded" : ""}`}><textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={handleKeyDown} onFocus={() => setExpanded(true)} placeholder="e.g. Compare the three strongest alternatives and leave me a source-backed brief…" aria-label="Task direction" /><div className="composer-toolbar"><div className="composer-tools"><input ref={attachmentInput} className="sr-only" type="file" onChange={selectAttachment} aria-label="Attach task context" /><button type="button" onClick={() => attachmentInput.current?.click()}><Plus size={15} /> {attachmentName ? `Attached: ${attachmentName}` : "Add context"}</button><span className="mono-hint">⌘ ↵ to run</span></div><button type="button" className="run-button" onClick={() => void submit()} disabled={isTaskSubmitting}><Play size={15} fill="currentColor" /> {isTaskSubmitting ? "Queueing…" : "Run task"}</button></div></div></div>
    <div className="composer-footer"><span><ShieldCheck size={14} /> You stay in control of approvals</span><span>Ollama · local model <span className="ready-dot" /></span></div>
  </section>;
}

function TaskProgress({ task }: { task: Task }) {
  const { openTask } = useNavigationCommands();
  return <section className="panel active-task-panel"><div className="panel-heading"><div><div className="eyebrow compact">Active thread</div><h2>{task.title}</h2></div><button type="button" className="text-button" onClick={() => openTask(task.id)}>Open detail <ArrowUpRight size={15} /></button></div><div className="task-meta-row"><StatusPill status={task.status} /><span><Clock3 size={14} /> {task.duration}</span><span><TerminalSquare size={14} /> {task.tags.join(" · ")}</span></div><div className="progress-line"><div className="progress-fill" style={{ width: `${task.progress}%` }} /><span>{task.progress}%</span></div><div className="step-list">{task.steps.map((step, index) => <div className={`step-row ${step.status}`} key={step.id}><div className="step-index">{step.status === "done" ? <Check size={13} /> : step.status === "active" ? <span className="step-pulse" /> : String(index + 1).padStart(2, "0")}</div><div className="step-copy"><strong>{step.label}</strong><span>{step.detail}</span></div>{step.tool && <span className="tool-tag">{step.tool}</span>}<div className="step-state">{step.status === "done" ? "Done" : step.status === "active" ? "Now" : "Queued"}</div></div>)}</div></section>;
}

function ThoughtProcess() {
  const events = useAppStore((state) => state.events);
  const { goTo } = useNavigationCommands();
  const recentEvents = useMemo(() => events.slice(-80), [events]);
  return <section className="panel thought-panel"><div className="panel-heading"><div><div className="eyebrow compact">Signal feed</div><h2>What the agent sees</h2></div><span className="live-label"><span className="tiny-pulse" /> streaming</span></div><div className="thought-list" aria-live="polite">{recentEvents.map((event) => <div className={`thought-row kind-${event.kind}`} key={event.id}><div className="thought-time">{event.time}</div><div className="thought-marker"><span /></div><div className="thought-body"><strong>{event.label}</strong><p>{event.detail}</p></div></div>)}</div><button type="button" className="feed-button" onClick={() => { goTo("tasks"); toast.info("Live event stream is shown with the selected task"); }}>View full event stream <ArrowUpRight size={15} /></button></section>;
}

function HistoryPanel() {
  const tasks = useAppStore((state) => state.tasks);
  const { goTo, openTask } = useNavigationCommands();
  const recentTasks = useMemo(() => tasks.slice(0, 100), [tasks]);
  return <section className="history-section"><div className="section-heading"><div><div className="eyebrow compact">Recent work</div><h2>Task history</h2></div><button type="button" className="text-button" onClick={() => goTo("tasks")}>View all <ArrowUpRight size={15} /></button></div><div className="history-table"><div className="history-head"><span>Task</span><span>Status</span><span>Started</span><span>Duration</span><span /></div>{recentTasks.map((task) => <button type="button" className="history-row" key={task.id} onClick={() => openTask(task.id)}><span className="history-title"><span className={`history-icon ${task.status}`}><FileText size={15} /></span><span><strong>{task.title}</strong><small>{task.id} · {task.tags.join(" / ")}</small></span></span><StatusPill status={task.status} /><span className="mono-cell">{task.createdAt}</span><span className="mono-cell">{task.duration}</span><ArrowUpRight size={15} className="row-arrow" /></button>)}</div></section>;
}

function ToolsView() {
  const tools = useAppStore((state) => state.tools);
  return <div className="page-view"><Header eyebrow="System inventory" title="Tool explorer" /><div className="view-intro"><div><p className="lede">A clear view of what Aurora can call, where the capability lives, and how it is shaped.</p></div><div className="inventory-stat"><span className="stat-number">{tools.length}</span><span>available tools<br /><small>across 3 servers</small></span></div></div><div className="tool-grid">{tools.map((tool) => <article className="tool-card" key={tool.name}><div className="tool-card-top"><span className="tool-symbol"><Wrench size={16} /></span><span className="server-label">{tool.server}</span></div><h3>{tool.name}</h3><p>{tool.description}</p><div className="tool-card-foot"><span className="mono-cell">JSON schema</span><ArrowUpRight size={15} /></div></article>)}</div></div>;
}

function SettingsView() {
  const user = useSessionStore((state) => state.user);
  const { openDialog } = useAuthCommands();
  return <div className="page-view"><Header eyebrow="Workspace controls" title="Settings" /><div className="settings-layout"><section className="panel settings-card"><div className="panel-heading"><div><div className="eyebrow compact">Profile</div><h2>Your operator profile</h2></div><button type="button" className="icon-button" aria-label="Manage profile" onClick={() => openDialog()}><MoreHorizontal size={18} /></button></div><div className="profile-large"><div className="avatar large">{user?.username.slice(0, 2).toUpperCase() || "AR"}</div><div><h3>{user?.username || "Guest operator"}</h3><p>{user?.email || "Sign in to use the local task service."}</p></div></div><div className="setting-row"><span><strong>Default model</strong><small>Used when a task does not specify a provider.</small></span><button type="button" className="setting-value" onClick={() => toast.info("Model selection is managed by the local Ollama runtime.")}>Ollama · phi3:mini <ChevronDown size={15} /></button></div><div className="setting-row"><span><strong>Approval mode</strong><small>Pause before external or irreversible actions.</small></span><button type="button" className="setting-value highlighted" onClick={() => toast.info("Approval mode is enforced by the local coordinator.")}>Always ask <ChevronDown size={15} /></button></div><div className="setting-row"><span><strong>Theme</strong><small>Keep the command center dark and low-noise.</small></span><button type="button" className="setting-value" onClick={() => toast.info("Aurora dark is active for this desktop workspace.")}>Aurora dark <ChevronDown size={15} /></button></div></section><section className="settings-note"><div className="note-icon"><Gauge size={18} /></div><div><h3>Designed for inspection</h3><p>Every task keeps its plan, tools, approvals, and outcomes close at hand. The interface is intentionally opinionated about visibility.</p></div></section></div></div>;
}

function TasksView() {
  const tasks = useAppStore((state) => state.tasks);
  const activeTaskId = useAppStore((state) => state.activeTaskId);
  const active = tasks.find((task) => task.id === activeTaskId) || tasks[0];
  return <div className="page-view"><Header eyebrow="Task operations" title="Task desk" /><div className="task-view-grid"><TaskProgress task={active} /><ThoughtProcess /></div><HistoryPanel /></div>;
}

function Overview() {
  const tasks = useAppStore((state) => state.tasks);
  const active = tasks.find((task) => task.id === useAppStore.getState().activeTaskId) || tasks[0];
  useTaskStream(active.id);
  const user = useSessionStore((state) => state.user);
  return <div className="page-view"><Header eyebrow="Local workspace" title={user ? `Welcome back, ${user.username}.` : "Sign in to direct the agent."} /><div className="overview-grid"><Composer /><div className="side-stats"><div className="micro-stat"><span className="micro-label">Active tasks</span><strong>{tasks.filter((task) => task.status === "executing").length}</strong><span className="micro-trend">Local workspace</span></div><div className="micro-stat"><span className="micro-label">Available tools</span><strong>04</strong><span className="micro-trend neutral">Across local servers</span></div><div className="micro-stat dark-stat"><span className="micro-label">Authentication</span><strong>{user ? "ON" : "—"}</strong><span className="micro-trend">{user ? "Local session active" : "Sign in required"}</span></div></div></div><div className="overview-panels"><TaskProgress task={active} /><ThoughtProcess /></div><HistoryPanel /></div>;
}

export default function Home() {
  const view = useAppStore((state) => state.view);
  const authDialogOpen = useSessionStore((state) => state.authDialogOpen);
  const authError = useSessionStore((state) => state.authError);
  const authStatus = useSessionStore((state) => state.status);
  const { hydrate, closeDialog, signIn, signUp } = useAuthCommands();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  useEffect(() => { void hydrate(); }, [hydrate]);
  return <div className="app-shell"><button type="button" className="mobile-menu" onClick={() => setSidebarOpen((open) => !open)} aria-label="Toggle navigation"><Menu size={19} /></button><div className={sidebarOpen ? "sidebar-wrap open" : "sidebar-wrap"}><Sidebar /></div><main className="main-canvas">{view === "overview" && <Overview />}{view === "tasks" && <TasksView />}{view === "tools" && <ToolsView />}{view === "connectors" && <ConnectorsView header={<Header eyebrow="Integration control" title="Connectors" />} />}{view === "health" && <Suspense fallback={<div className="page-view"><Header eyebrow="Local observability" title="Operations" /><section className="panel"><p>Loading operational health…</p></section></div>}><HealthDashboardView header={<Header eyebrow="Local observability" title="Operations" />} /></Suspense>}{view === "extensions" && <Suspense fallback={<div className="page-view"><Header eyebrow="Local extensibility" title="Extensions" /><section className="panel"><p>Loading reviewed extensions…</p></section></div>}><ExtensionsView header={<Header eyebrow="Local extensibility" title="Extensions" />} /></Suspense>}{view === "agent_loop" && <Suspense fallback={<div className="page-view"><Header eyebrow="Repository automation" title="Agent loop" /><section className="panel"><p>Loading loop controls…</p></section></div>}><AgentLoopView header={<Header eyebrow="Repository automation" title="Agent loop" />} /></Suspense>}{view === "release_evidence" && <Suspense fallback={<div className="page-view"><Header eyebrow="Release assurance" title="Release evidence" /><section className="panel"><p>Loading release evidence…</p></section></div>}><ReleaseEvidenceView header={<Header eyebrow="Release assurance" title="Release evidence" />} /></Suspense>}{view === "settings" && <SettingsView />}<footer className="app-footer"><span><Hexagon size={13} /> Aurora Relay / private workspace</span><span className="footer-right">build 0.8.22 <span className="footer-divider" /> <Wifi size={13} /> local-first</span></footer></main><ManusDialog open={authDialogOpen} onOpenChange={(open) => { if (!open) closeDialog(); }} onLogin={async (username, password) => (await signIn(username, password)).ok} onRegister={async (username, email, password) => (await signUp(username, email, password)).ok} isSubmitting={authStatus === "authenticating"} error={authError} /></div>;
}
