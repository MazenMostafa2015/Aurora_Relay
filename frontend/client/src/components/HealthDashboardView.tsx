// Aurora Relay style reminder: render a calm dark operational ledger; all refreshes are user initiated and all secrets stay out of the renderer.
import { useMemo } from "react";
import { Activity, AlertTriangle, BadgeCheck, CheckCircle2, CirclePause, CircleStop, Clock3, ExternalLink, Gauge, Github, RefreshCw, Settings2, ShieldCheck, TerminalSquare, Wrench, X } from "lucide-react";
import { toast } from "sonner";
import { useHealthCommands, useNavigationCommands, useAuthCommands } from "@/lib/commands";
import { useHealthStore } from "@/store/healthStore";

function stamp(value: string | null) {
  if (!value) return "No recorded time";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "No recorded time" : parsed.toLocaleString();
}

function uptime(seconds: number) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return hours ? `${hours}h ${minutes}m` : `${minutes}m`;
}

const statusLabel = { operational: "Operational", degraded: "Needs attention", critical: "Action required" };

export function HealthDashboardView({ header }: { header: React.ReactNode }) {
  const snapshot = useHealthStore((state) => state.snapshot);
  const isLoading = useHealthStore((state) => state.isLoading);
  const testingConnectorId = useHealthStore((state) => state.testingConnectorId);
  const error = useHealthStore((state) => state.error);
  const lastUpdated = useHealthStore((state) => state.lastUpdated);
  const dismissedAlertIds = useHealthStore((state) => state.dismissedAlertIds);
  const dismissAlert = useHealthStore((state) => state.dismissAlert);
  const { refresh, testConnector } = useHealthCommands();
  const { goTo } = useNavigationCommands();
  const { openDialog } = useAuthCommands();
  const activeAlerts = useMemo(() => snapshot.alerts.filter((item) => !dismissedAlertIds.includes(item.id)), [dismissedAlertIds, snapshot.alerts]);

  const requestRefresh = async () => {
    const result = await refresh(true);
    if (!result.ok && result.code === "authentication") openDialog(result.message);
  };
  const requestTest = async (connectorId: string) => {
    const result = await testConnector(connectorId);
    if (!result.ok && result.code === "authentication") openDialog(result.message);
  };

  return <div className="page-view health-dashboard-view">
    {header}
    <section className="health-hero" aria-label="Operational health summary">
      <div>
        <div className="eyebrow compact">Local-first observability</div>
        <h2>Operations, <em>in focus.</em></h2>
        <p>Read current system posture, connector readiness, bounded repository activity, and the verified release chain from one controlled surface.</p>
      </div>
      <div className="health-hero-actions">
        <div className={`health-posture ${snapshot.system.status}`}><span /><div><strong>{statusLabel[snapshot.system.status]}</strong><small>{lastUpdated ? `Refreshed ${stamp(lastUpdated)}` : "Packaged local fallback"}</small></div></div>
        <button type="button" className="health-refresh-button" onClick={() => void requestRefresh()} disabled={isLoading} aria-label="Refresh operational status"><RefreshCw size={15} className={isLoading ? "spinning" : ""} />{isLoading ? "Refreshing…" : "Refresh status"}</button>
      </div>
    </section>

    {error && <div className="health-inline-error" role="status"><AlertTriangle size={16} /><span>Live status could not be refreshed: {error}. Packaged release evidence remains available.</span></div>}

    <section className="health-summary-grid" aria-label="System status summary">
      <article><span className="health-summary-icon"><Gauge size={17} /></span><div><span>System</span><strong>{statusLabel[snapshot.system.status]}</strong><small>{snapshot.system.version} · {uptime(snapshot.system.uptime_seconds)} uptime</small></div></article>
      <article><span className="health-summary-icon"><Wrench size={17} /></span><div><span>Connectors</span><strong>{snapshot.connectors.filter((item) => item.status === "connected").length} ready</strong><small>{snapshot.connectors.length ? `${snapshot.connectors.length} registered connector${snapshot.connectors.length === 1 ? "" : "s"}` : "Configure a local connector"}</small></div></article>
      <article><span className="health-summary-icon"><Activity size={17} /></span><div><span>Agent loop</span><strong>{snapshot.agent_loop.state}</strong><small>{snapshot.agent_loop.current_iteration}/{snapshot.agent_loop.total_iterations || 0} guarded iterations</small></div></article>
      <article><span className="health-summary-icon"><BadgeCheck size={17} /></span><div><span>Release</span><strong>{snapshot.release.version}</strong><small>{snapshot.release.sha256_verified ? "Digest verified" : "Verification pending"}</small></div></article>
      <article><span className="health-summary-icon"><ShieldCheck size={17} /></span><div><span>Vault</span><strong>{snapshot.vault.state === "ready" ? "Protected" : "Locked"}</strong><small>{snapshot.vault.backend.replaceAll("-", " ")}</small></div></article>
    </section>

    <div className="health-main-grid">
      <section className="health-panel connectors-health-panel" aria-labelledby="health-connectors-heading">
        <div className="health-panel-heading"><div><div className="eyebrow compact">Integration readiness</div><h2 id="health-connectors-heading">Connectors</h2></div><button type="button" className="health-link-button" onClick={() => goTo("connectors")}>Manage <Settings2 size={14} /></button></div>
        {snapshot.connectors.length ? <div className="health-connector-list">{snapshot.connectors.map((connector) => <article className="health-connector-row" key={connector.id}>
          <span className={`connector-health-mark ${connector.status}`}><Github size={15} /></span><div className="connector-health-copy"><strong>{connector.display_name}</strong><span>{connector.status === "connected" ? `Last checked ${stamp(connector.last_connected)}` : connector.error || "Configuration required"}</span></div><span className={`health-status-chip ${connector.status}`}>{connector.status}</span><button type="button" className="connector-test-button" disabled={testingConnectorId === connector.id || connector.status === "disabled"} onClick={() => void requestTest(connector.id)}>{testingConnectorId === connector.id ? "Testing…" : "Test"}</button>
        </article>)}</div> : <div className="health-empty-state"><Wrench size={18} /><div><strong>No connectors registered</strong><p>Configure a GitHub or Revit connector to surface live readiness checks.</p></div><button type="button" onClick={() => goTo("connectors")}>Open connectors <ExternalLink size={13} /></button></div>}
      </section>

      <section className="health-panel loop-health-panel" aria-labelledby="health-loop-heading">
        <div className="health-panel-heading"><div><div className="eyebrow compact">Repository automation</div><h2 id="health-loop-heading">Agent loop</h2></div><button type="button" className="health-link-button" onClick={() => goTo("agent_loop")}>Open loop <ExternalLink size={14} /></button></div>
        <div className="health-loop-state"><span className={`loop-state-icon ${snapshot.agent_loop.state}`}>{snapshot.agent_loop.state === "paused" ? <CirclePause size={19} /> : snapshot.agent_loop.state === "stopped" ? <CircleStop size={19} /> : <Activity size={19} />}</span><div><strong>{snapshot.agent_loop.state === "idle" ? "Dry-run idle" : `Loop ${snapshot.agent_loop.state}`}</strong><p>{snapshot.agent_loop.last_result ? `Last outcome: ${snapshot.agent_loop.last_result}` : "No recorded iteration for this operator."}</p></div></div>
        <div className="health-loop-metrics"><span><b>{snapshot.agent_loop.current_iteration}</b> current</span><span><b>{snapshot.agent_loop.total_iterations || 0}</b> allowed</span><span><b>{snapshot.agent_loop.next_run ? stamp(snapshot.agent_loop.next_run) : "Manual"}</b> next run</span></div>
        <div className="health-iteration-list">{snapshot.agent_loop.recent_iterations.length ? snapshot.agent_loop.recent_iterations.map((iteration) => <div className={`health-iteration ${iteration.result}`} key={`${iteration.iteration}-${iteration.timestamp}`}><span><CheckCircle2 size={14} /></span><div><strong>Iteration {iteration.iteration}</strong><p>{iteration.summary}</p></div><time>{stamp(iteration.timestamp)}</time></div>) : <p className="health-empty-copy">No iteration history yet. Repository schedules remain disabled until explicitly enabled and bounded.</p>}</div>
      </section>
    </div>

    <div className="health-main-grid secondary">
      <section className="health-panel release-health-panel" aria-labelledby="health-release-heading">
        <div className="health-panel-heading"><div><div className="eyebrow compact">Artifact assurance</div><h2 id="health-release-heading">Release integrity</h2></div><button type="button" className="health-link-button" onClick={() => goTo("release_evidence")}>Evidence ledger <ExternalLink size={14} /></button></div>
        <div className="health-verification-list">
          {[["Installer digest", snapshot.release.sha256_verified], ["Build provenance", snapshot.release.provenance_verified], ["Signer pin", snapshot.release.signer_pinned], ["Timestamp presence", snapshot.release.timestamp_present], ["Clean-machine evidence", snapshot.release.clean_machine_verified]].map(([label, verified]) => <div key={String(label)}><CheckCircle2 size={15} className={verified ? "verified" : "pending"} /><span>{label}</span><strong>{verified ? "Verified" : "Review"}</strong></div>)}
        </div>
        <p className="health-trust-note"><ShieldCheck size={15} />{snapshot.release.trust_note}</p>
      </section>

      <section className="health-panel activity-health-panel" aria-labelledby="health-activity-heading">
        <div className="health-panel-heading"><div><div className="eyebrow compact">Audited operator events</div><h2 id="health-activity-heading">Recent activity</h2></div><span className="health-local-label"><TerminalSquare size={13} /> local</span></div>
        {snapshot.activities.length ? <div className="health-activity-list">{snapshot.activities.map((activity) => <div className={`health-activity-row ${activity.type}`} key={activity.id}><span /><div><strong>{activity.message}</strong><p>{activity.source}</p></div><time>{stamp(activity.timestamp)}</time></div>)}</div> : <p className="health-empty-copy">No authenticated operator activity is available in the local history.</p>}
      </section>
    </div>

    <section className={`health-panel vault-health-panel ${snapshot.vault.state}`} aria-labelledby="health-vault-heading">
      <div className="health-panel-heading"><div><div className="eyebrow compact">Credential boundary</div><h2 id="health-vault-heading">Credential vault</h2></div><span className={`health-status-chip ${snapshot.vault.state === "ready" ? "connected" : "error"}`}>{snapshot.vault.state}</span></div>
      <div className="vault-health-copy"><ShieldCheck size={18} /><div><strong>{snapshot.vault.state === "ready" ? "OS-protected key material is available" : "Credentials are fail-closed"}</strong><p>{snapshot.vault.message}</p><small>Backend: {snapshot.vault.backend.replaceAll("-", " ")}{snapshot.vault.fallback ? " · encrypted fallback" : ""}. No secret values are exposed to the dashboard.</small></div></div>
    </section>

    <section className="health-alerts" aria-labelledby="health-alerts-heading"><div className="health-alerts-heading"><div><div className="eyebrow compact">Escalation queue</div><h2 id="health-alerts-heading">Alerts</h2></div><span>{activeAlerts.length} active</span></div>{activeAlerts.length ? <div className="health-alert-list">{activeAlerts.map((alert) => <article className={`health-alert ${alert.severity}`} key={alert.id}><AlertTriangle size={17} /><div><strong>{alert.message}</strong>{alert.recommendation && <p>{alert.recommendation}</p>}</div><button type="button" aria-label={`Dismiss alert: ${alert.message}`} onClick={() => { dismissAlert(alert.id); toast.info("Alert dismissed for this session"); }}><X size={16} /></button></article>)}</div> : <div className="health-clear-alerts"><CheckCircle2 size={18} /><span>No active operational alerts.</span></div>}</section>
  </div>;
}
