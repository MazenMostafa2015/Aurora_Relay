// Aurora Relay style reminder: editorial command center, graphite surfaces, relay cyan, saffron for human attention.
import { useMemo, useState } from "react";
import { useAppStore } from "@/store/appStore";
import { useTaskStream } from "@/hooks/useTaskStream";
import type { Task, ViewKey } from "@/types/app";
import { toast } from "sonner";
import {
  Activity, ArrowUpRight, BrainCircuit, Check, ChevronDown, CircleHelp, Clock3,
  Command, Cpu, FileText, Gauge, Hexagon, History as HistoryIcon, LayoutDashboard, LogOut,
  Menu, MoreHorizontal, PanelLeftClose, Play, Plus, Search, Settings2, ShieldCheck,
  Sparkles, TerminalSquare, UserRound, Wifi, Wrench, X,
} from "lucide-react";

const navItems: { key: ViewKey; label: string; icon: typeof LayoutDashboard }[] = [
  { key: "overview", label: "Overview", icon: LayoutDashboard },
  { key: "tasks", label: "Task desk", icon: Activity },
  { key: "tools", label: "Tool explorer", icon: Wrench },
  { key: "settings", label: "Settings", icon: Settings2 },
];

function StatusPill({ status }: { status: Task["status"] }) {
  const copy = { executing: "Running", waiting: "Needs review", completed: "Complete", failed: "Failed", paused: "Paused" }[status];
  return <span className={`status-pill status-${status}`}><span className="status-dot" />{copy}</span>;
}

function Sidebar() {
  const view = useAppStore((state) => state.view);
  const setView = useAppStore((state) => state.setView);
  const user = useAppStore((state) => state.user);
  const logout = useAppStore((state) => state.logout);
  return <aside className="sidebar">
    <div className="brand-lockup"><div className="brand-mark"><img src="/manus-storage/aurora-mark_dc0b3245.png" alt="" /></div><div><div className="brand-name">AURORA <span>RELAY</span></div><div className="brand-caption">AI command center</div></div></div>
    <div className="sidebar-section-label">Workspace</div>
    <nav className="nav-list" aria-label="Workspace navigation">
      {navItems.map(({ key, label, icon: Icon }) => <button key={key} className={`nav-item ${view === key ? "active" : ""}`} onClick={() => setView(key)}><Icon size={17} strokeWidth={1.8} /><span>{label}</span>{key === "tasks" && <span className="nav-count">03</span>}</button>)}
    </nav>
    <div className="sidebar-divider" />
    <div className="sidebar-section-label">Pinned</div>
    <button className="pin-item" onClick={() => { setView("tasks"); toast("Task desk opened"); }}><span className="pin-swatch cyan" />Research sprint <span className="pin-meta">68%</span></button>
    <button className="pin-item" onClick={() => { setView("tasks"); toast("Approval queue opened"); }}><span className="pin-swatch saffron" />Approval queue <span className="pin-meta">01</span></button>
    <div className="sidebar-bottom"><div className="connection-card"><div className="connection-top"><span className="connection-indicator" />Local workspace</div><div className="connection-detail">API fallback mode · safe to explore</div></div><button className="profile-row" onClick={() => setView("settings")}><span className="avatar">MC</span><span className="profile-copy"><strong>{user?.username || "Guest"}</strong><small>{user?.email || "Not connected"}</small></span><MoreHorizontal size={16} /></button><button className="logout-btn" onClick={() => { logout(); toast("Signed out of this workspace"); }}><LogOut size={15} /> Sign out</button></div>
  </aside>;
}

function Header({ title, eyebrow }: { title: string; eyebrow: string }) {
  const isConnected = useAppStore((state) => state.isConnected);
  return <header className="workspace-header"><div><div className="eyebrow"><span className="eyebrow-line" />{eyebrow}</div><h1>{title}</h1></div><div className="header-actions"><div className="live-status"><span className={`live-orb ${isConnected ? "connected" : ""}`} />{isConnected ? "Live link" : "Local preview"}</div><button className="icon-button" aria-label="Help"><CircleHelp size={18} /></button><button className="icon-button" aria-label="Open command palette"><Command size={18} /></button><button className="header-avatar">MC</button></div></header>;
}

function Composer() {
  const draft = useAppStore((state) => state.draft);
  const setDraft = useAppStore((state) => state.setDraft);
  const submitTask = useAppStore((state) => state.submitTask);
  const [expanded, setExpanded] = useState(false);
  const submit = () => { if (!draft.trim()) { toast("Give the agent a direction first"); return; } submitTask(); toast("Task queued"); };
  return <section className="composer-shell">
    <div className="composer-art" />
    <div className="composer-content"><div className="composer-kicker"><Sparkles size={14} /> New agent task <span className="composer-rule" /></div><h2>Give the agent<br /><em>a direction.</em></h2><p className="composer-note">Describe the outcome you want. Aurora will frame the work, choose tools, and keep every meaningful move visible.</p><div className={`composer-input-wrap ${expanded ? "expanded" : ""}`}><textarea value={draft} onChange={(event) => setDraft(event.target.value)} onFocus={() => setExpanded(true)} placeholder="e.g. Compare the three strongest alternatives and leave me a source-backed brief…" aria-label="Task direction" /><div className="composer-toolbar"><div className="composer-tools"><button type="button" onClick={() => toast("Context attachments are available when the API is connected")}><Plus size={15} /> Add context</button><span className="mono-hint">⌘ ↵ to run</span></div><button className="run-button" onClick={submit}><Play size={15} fill="currentColor" /> Run task</button></div></div></div>
    <div className="composer-footer"><span><ShieldCheck size={14} /> You stay in control of approvals</span><span>Ollama · local model <span className="ready-dot" /></span></div>
  </section>;
}

function TaskProgress({ task }: { task: Task }) {
  const selectTask = useAppStore((state) => state.selectTask);
  return <section className="panel active-task-panel"><div className="panel-heading"><div><div className="eyebrow compact">Active thread</div><h2>{task.title}</h2></div><button className="text-button" onClick={() => selectTask(task.id)}>Open detail <ArrowUpRight size={15} /></button></div><div className="task-meta-row"><StatusPill status={task.status} /><span><Clock3 size={14} /> {task.duration}</span><span><TerminalSquare size={14} /> {task.tags.join(" · ")}</span></div><div className="progress-line"><div className="progress-fill" style={{ width: `${task.progress}%` }} /><span>{task.progress}%</span></div><div className="step-list">{task.steps.map((step, index) => <div className={`step-row ${step.status}`} key={step.id}><div className="step-index">{step.status === "done" ? <Check size={13} /> : step.status === "active" ? <span className="step-pulse" /> : String(index + 1).padStart(2, "0")}</div><div className="step-copy"><strong>{step.label}</strong><span>{step.detail}</span></div>{step.tool && <span className="tool-tag">{step.tool}</span>}<div className="step-state">{step.status === "done" ? "Done" : step.status === "active" ? "Now" : "Queued"}</div></div>)}</div></section>;
}

function ThoughtProcess() {
  const events = useAppStore((state) => state.events);
  return <section className="panel thought-panel"><div className="panel-heading"><div><div className="eyebrow compact">Signal feed</div><h2>What the agent sees</h2></div><span className="live-label"><span className="tiny-pulse" /> streaming</span></div><div className="thought-list" aria-live="polite">{events.map((event) => <div className={`thought-row kind-${event.kind}`} key={event.id}><div className="thought-time">{event.time}</div><div className="thought-marker"><span /></div><div className="thought-body"><strong>{event.label}</strong><p>{event.detail}</p></div></div>)}</div><button className="feed-button" onClick={() => toast("The full event stream opens when a live task is selected")}>View full event stream <ArrowUpRight size={15} /></button></section>;
}

function HistoryPanel() {
  const tasks = useAppStore((state) => state.tasks);
  const selectTask = useAppStore((state) => state.selectTask);
  return <section className="history-section"><div className="section-heading"><div><div className="eyebrow compact">Recent work</div><h2>Task history</h2></div><button className="text-button" onClick={() => toast("History filters are ready for the API connection")}>View all <ArrowUpRight size={15} /></button></div><div className="history-table"><div className="history-head"><span>Task</span><span>Status</span><span>Started</span><span>Duration</span><span /></div>{tasks.map((task) => <button className="history-row" key={task.id} onClick={() => selectTask(task.id)}><span className="history-title"><span className={`history-icon ${task.status}`}><FileText size={15} /></span><span><strong>{task.title}</strong><small>{task.id} · {task.tags.join(" / ")}</small></span></span><StatusPill status={task.status} /><span className="mono-cell">{task.createdAt}</span><span className="mono-cell">{task.duration}</span><ArrowUpRight size={15} className="row-arrow" /></button>)}</div></section>;
}

function ToolsView() {
  const tools = useAppStore((state) => state.tools);
  return <div className="page-view"><Header eyebrow="System inventory" title="Tool explorer" /><div className="view-intro"><div><p className="lede">A clear view of what Aurora can call, where the capability lives, and how it is shaped.</p></div><div className="inventory-stat"><span className="stat-number">{tools.length}</span><span>available tools<br /><small>across 3 servers</small></span></div></div><div className="tool-grid">{tools.map((tool) => <article className="tool-card" key={tool.name}><div className="tool-card-top"><span className="tool-symbol"><Wrench size={16} /></span><span className="server-label">{tool.server}</span></div><h3>{tool.name}</h3><p>{tool.description}</p><div className="tool-card-foot"><span className="mono-cell">JSON schema</span><ArrowUpRight size={15} /></div></article>)}</div></div>;
}

function SettingsView() {
  const user = useAppStore((state) => state.user);
  return <div className="page-view"><Header eyebrow="Workspace controls" title="Settings" /><div className="settings-layout"><section className="panel settings-card"><div className="panel-heading"><div><div className="eyebrow compact">Profile</div><h2>Your operator profile</h2></div><button className="icon-button" onClick={() => toast("Profile editing will connect to the API") }><MoreHorizontal size={18} /></button></div><div className="profile-large"><div className="avatar large">MC</div><div><h3>{user?.username || "Guest operator"}</h3><p>{user?.email || "Connect an account to sync your workspace."}</p></div></div><div className="setting-row"><span><strong>Default model</strong><small>Used when a task does not specify a provider.</small></span><span className="setting-value">Ollama · phi3:mini <ChevronDown size={15} /></span></div><div className="setting-row"><span><strong>Approval mode</strong><small>Pause before external or irreversible actions.</small></span><span className="setting-value highlighted">Always ask <ChevronDown size={15} /></span></div><div className="setting-row"><span><strong>Theme</strong><small>Keep the command center dark and low-noise.</small></span><span className="setting-value">Aurora dark <ChevronDown size={15} /></span></div></section><section className="settings-note"><div className="note-icon"><Gauge size={18} /></div><div><h3>Designed for inspection</h3><p>Every task keeps its plan, tools, approvals, and outcomes close at hand. The interface is intentionally opinionated about visibility.</p></div></section></div></div>;
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
  return <div className="page-view"><Header eyebrow="Thursday · 14 August 2026" title="Good morning, Maya." /><div className="overview-grid"><Composer /><div className="side-stats"><div className="micro-stat"><span className="micro-label">Active tasks</span><strong>03</strong><span className="micro-trend">+1 this morning</span></div><div className="micro-stat"><span className="micro-label">Tool calls today</span><strong>27</strong><span className="micro-trend neutral">Across 4 servers</span></div><div className="micro-stat dark-stat"><span className="micro-label">Avg. task clarity</span><strong>92<span>%</span></strong><span className="micro-trend">↑ 8% this week</span></div></div></div><div className="overview-panels"><TaskProgress task={active} /><ThoughtProcess /></div><HistoryPanel /></div>;
}

export default function Home() {
  const view = useAppStore((state) => state.view);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  return <div className="app-shell"><button className="mobile-menu" onClick={() => setSidebarOpen((open) => !open)} aria-label="Toggle navigation"><Menu size={19} /></button><div className={sidebarOpen ? "sidebar-wrap open" : "sidebar-wrap"}><Sidebar /></div><main className="main-canvas">{view === "overview" && <Overview />}{view === "tasks" && <TasksView />}{view === "tools" && <ToolsView />}{view === "settings" && <SettingsView />}<footer className="app-footer"><span><Hexagon size={13} /> Aurora Relay / private workspace</span><span className="footer-right">build 0.7.0 <span className="footer-divider" /> <Wifi size={13} /> local-first</span></footer></main></div>;
}
