import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Bot, CalendarClock, CheckCircle2, FileClock, Pause, Play, RefreshCw, ShieldCheck, Square, WandSparkles } from "lucide-react";
import { useAgentLoopStore } from "@/store/agentLoopStore";
import { useSessionStore } from "@/store/sessionStore";
import { useAgentLoopCommands } from "@/lib/commands";
import type { AgentLoopConfig, AgentLoopRecord } from "@/types/app";

const safeConfig: AgentLoopConfig = {
  enabled: false,
  dry_run: true,
  schedule: { frequency: "daily", times_per_day: 5, duration_days: 7, start_time: "08:00", end_time: "20:00", time_zone: "UTC" },
  scope: { areas: ["code", "tests", "ui", "connectors"], max_actions_per_loop: 8, allow_destructive_actions: false },
  guardrails: { max_loops_total: 35, max_consecutive_failures: 3, require_approval_for: ["deploy", "release", "delete", "external"], rollback_on_error: true },
  reporting: { summary_after_each_loop: true, daily_digest: true, final_report: true, notification_channel: "ui" },
  repository: { branch_prefix: "aurora-agent/loop", allow_review_branch_push: true, allow_merge: false, allow_deploy: false, allow_release: false },
};

function formatTime(value: string | null) {
  return value ? new Date(value).toLocaleString() : "Not scheduled";
}

function createConfig(areas: AgentLoopConfig["scope"]["areas"]): AgentLoopConfig {
  return { ...safeConfig, scope: { ...safeConfig.scope, areas } };
}

function LoopSummary({ loop, selected, onSelect }: { loop: AgentLoopRecord; selected: boolean; onSelect: () => void }) {
  const state = loop.hard_stop ? "HARD STOP" : loop.status.replace("_", " ");
  return <button type="button" className={`agent-loop-card${selected ? " selected" : ""}`} aria-label={`Select ${loop.name}`} aria-pressed={selected} onClick={onSelect}>
    <span className="agent-loop-state"><span className={`status-dot ${loop.status}`} />{state}</span>
    <strong>{loop.name}</strong>
    <small>{loop.runs_completed}/{loop.config.guardrails.max_loops_total} dry runs · {loop.config.scope.max_actions_per_loop} actions max</small>
  </button>;
}

export function AgentLoopView({ header }: { header: React.ReactNode }) {
  const user = useSessionStore((state) => state.user);
  const loops = useAgentLoopStore((state) => state.loops);
  const selectedLoopId = useAgentLoopStore((state) => state.selectedLoopId);
  const selectLoop = useAgentLoopStore((state) => state.selectLoop);
  const iterations = useAgentLoopStore((state) => state.iterations);
  const isLoading = useAgentLoopStore((state) => state.isLoading);
  const isSaving = useAgentLoopStore((state) => state.isSaving);
  const error = useAgentLoopStore((state) => state.error);
  const commands = useAgentLoopCommands();
  const [name, setName] = useState("Repository improvement loop");
  const [areas, setAreas] = useState<AgentLoopConfig["scope"]["areas"]>(safeConfig.scope.areas);
  const [hardStopText, setHardStopText] = useState("");
  const selected = useMemo(() => loops.find((loop) => loop.id === selectedLoopId) || loops[0] || null, [loops, selectedLoopId]);

  useEffect(() => { if (user) void commands.refresh(); }, [commands, user]);
  useEffect(() => { if (selected) void commands.loadIterations(selected.id); }, [commands, selected?.id]);

  const toggleArea = (area: AgentLoopConfig["scope"]["areas"][number]) => setAreas((current) => current.includes(area) ? current.filter((item) => item !== area) : [...current, area]);
  const create = async () => { const result = await commands.create(name, createConfig(areas)); if (result.ok) await commands.refresh(); };
  const hardStop = async () => { if (!selected || hardStopText !== "STOP") return; await commands.hardStop(selected); setHardStopText(""); };

  if (!user) return <section className="agent-loop-auth"><ShieldCheck size={26} /><h2>Sign in to configure automation</h2><p>Repository loops are user-scoped. Aurora will not create a schedule, branch, or report without an authenticated operator.</p></section>;

  return <div className="page-view agent-loop-view">
    {header}
    <section className="agent-loop-hero">
      <div><div className="eyebrow compact"><span className="eyebrow-line" />Bounded automation</div><h2>Think. Act. <em>Reflect.</em></h2><p>Five dry-run review cycles a day for seven days. Every plan stays inspectable; merges, releases, deploys, deletes, and external effects remain blocked.</p></div>
      <div className="agent-loop-hero-status"><span className="loop-shield"><ShieldCheck size={20} /></span><div><strong>Safe by default</strong><small>Schedule disabled until you start a loop</small></div></div>
    </section>

    <div className="agent-loop-layout">
      <aside className="agent-loop-sidebar">
        <div className="agent-loop-toolbar"><div><span className="eyebrow compact">Loop inventory</span><h3>Repository loops</h3></div><button type="button" className="icon-button" aria-label="Refresh agent loops" onClick={() => void commands.refresh()} disabled={isLoading}><RefreshCw size={16} /></button></div>
        <div className="agent-loop-list">{loops.length ? loops.map((loop) => <LoopSummary key={loop.id} loop={loop} selected={selected?.id === loop.id} onSelect={() => selectLoop(loop.id)} />) : <div className="agent-loop-empty"><Bot size={22} /><p>No loop is configured yet.</p></div>}</div>
        <div className="loop-create-form"><span className="eyebrow compact">New safe loop</span><label>Loop name<input value={name} onChange={(event) => setName(event.target.value)} maxLength={120} /></label><fieldset><legend>Improvement areas</legend>{(["code", "tests", "docs", "ui", "connectors", "security"] as const).map((area) => <label className="loop-check" key={area}><input type="checkbox" checked={areas.includes(area)} onChange={() => toggleArea(area)} />{area}</label>)}</fieldset><button type="button" className="run-button" onClick={() => void create()} disabled={isSaving || !areas.length}><WandSparkles size={15} /> Create dry-run loop</button></div>
      </aside>

      <section className="agent-loop-detail" aria-live="polite">
        {!selected ? <div className="agent-loop-empty detail"><CalendarClock size={28} /><h3>Ready when you are</h3><p>Create a loop to configure bounded repository reviews.</p></div> : <>
          <div className="agent-loop-detail-heading"><div><div className="eyebrow compact">Operator control</div><h2>{selected.name}</h2><p>Branch prefix <code>{selected.config.repository.branch_prefix}</code> · next run {formatTime(selected.next_run_at)}</p></div><span className={`loop-status ${selected.hard_stop ? "stopped" : selected.status}`}>{selected.hard_stop ? "Hard stopped" : selected.status}</span></div>
          {error && <div className="agent-loop-error"><AlertTriangle size={16} />{error}</div>}
          <div className="agent-loop-actions"><button type="button" className="run-button" onClick={() => void commands.runDry(selected)} disabled={isSaving || selected.hard_stop}><Play size={15} fill="currentColor" /> Run dry scan now</button>{selected.status === "scheduled" || selected.status === "running" ? <button type="button" className="text-button" onClick={() => void commands.pause(selected)} disabled={isSaving}><Pause size={15} /> Pause schedule</button> : <button type="button" className="text-button" onClick={() => void commands.start(selected)} disabled={isSaving || selected.hard_stop}><CalendarClock size={15} /> Enable schedule</button>}<span className="agent-loop-action-note">No source commits are made by this dry-run engine.</span></div>
          <div className="agent-loop-safety-grid"><article><ShieldCheck size={17} /><div><strong>Safety contract</strong><p>Dry-run only · {selected.config.scope.max_actions_per_loop} actions max · stop after {selected.config.guardrails.max_consecutive_failures} failures.</p></div></article><article><FileClock size={17} /><div><strong>Reviewable output</strong><p>Plan, log, validation summary, and reflection are persisted after every iteration.</p></div></article><article><CheckCircle2 size={17} /><div><strong>Approval gates</strong><p>{selected.config.guardrails.require_approval_for.join(", ")} always require an operator.</p></div></article></div>
          <div className="agent-loop-config"><div><div className="eyebrow compact">Schedule</div><strong>{selected.config.schedule.times_per_day} runs/day · {selected.config.schedule.duration_days} days</strong><p>{selected.config.schedule.start_time}–{selected.config.schedule.end_time} {selected.config.schedule.time_zone}; maximum {selected.config.guardrails.max_loops_total} loops.</p></div><div><div className="eyebrow compact">Scope</div><strong>{selected.config.scope.areas.join(" · ")}</strong><p>Review branches may be pushed. Merging, deploys, releases, and destructive actions are blocked.</p></div></div>
          <section className="agent-loop-history"><div className="section-heading"><div><div className="eyebrow compact">Iteration history</div><h3>Plans and reports</h3></div><span className="mono-cell">{iterations.length} recorded</span></div>{iterations.length ? <div className="agent-loop-table"><div className="agent-loop-table-head"><span>Run</span><span>Status</span><span>Branch</span><span>Evidence</span></div>{iterations.map((iteration) => <article key={iteration.id} className="agent-loop-row"><span><strong>#{iteration.sequence}</strong><small>{formatTime(iteration.completed_at || iteration.started_at)}</small></span><span className={`iteration-status ${iteration.status}`}>{iteration.status}</span><code>{iteration.branch_name || "No branch"}</code><span>{iteration.report_path ? "Plan · log · report" : iteration.error || "Pending"}</span></article>)}</div> : <div className="agent-loop-empty inline"><FileClock size={19} /><p>Run a dry scan to create the first reviewable report.</p></div>}</section>
          <section className="agent-loop-stop"><div><div className="eyebrow compact">Emergency control</div><h3>Hard stop the loop</h3><p>Stops scheduling immediately and cannot be undone from this loop. Type <code>STOP</code> to confirm.</p></div><div><input value={hardStopText} onChange={(event) => setHardStopText(event.target.value)} aria-label="Type STOP to hard stop loop" placeholder="Type STOP" /><button type="button" className="danger-button" onClick={() => void hardStop()} disabled={hardStopText !== "STOP" || isSaving || selected.hard_stop}><Square size={14} fill="currentColor" /> Hard stop</button></div></section>
        </>}
      </section>
    </div>
  </div>;
}
