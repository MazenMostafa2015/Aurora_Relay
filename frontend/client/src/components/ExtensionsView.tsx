// Aurora Relay style reminder: reviewed local extensions are explicit, disabled by default, and never execute on the host.
import { type ReactNode, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Boxes, CheckCircle2, CircleOff, LockKeyhole, Play, Power, Search, ShieldCheck, TerminalSquare } from "lucide-react";
import { useExtensionCommands } from "@/lib/commands";
import { useExtensionStore } from "@/store/extensionStore";
import { useSessionStore } from "@/store/sessionStore";
import type { ExtensionManifestRecord } from "@/types/app";

function StatusPill({ status }: { status: ExtensionManifestRecord["status"] }) {
  const normalized = status || "not_installed";
  const label = { not_installed: "Catalog", installed: "Installed", disabled: "Disabled", ready: "Ready", blocked: "Blocked", failed: "Failed" }[normalized];
  return <span className={`extension-status ${normalized}`}><span />{label}</span>;
}

export function ExtensionsView({ header }: { header: ReactNode }) {
  const token = useSessionStore((state) => state.token);
  const extensions = useExtensionStore((state) => state.extensions);
  const selectedExtensionId = useExtensionStore((state) => state.selectedExtensionId);
  const query = useExtensionStore((state) => state.query);
  const isLoading = useExtensionStore((state) => state.isLoading);
  const isSaving = useExtensionStore((state) => state.isSaving);
  const error = useExtensionStore((state) => state.error);
  const lastExecution = useExtensionStore((state) => state.lastExecution);
  const selectExtension = useExtensionStore((state) => state.selectExtension);
  const setQuery = useExtensionStore((state) => state.setQuery);
  const { refresh, install, setEnabled, saveConfiguration, execute } = useExtensionCommands();
  const [configurationText, setConfigurationText] = useState("{}");

  useEffect(() => { if (token) void refresh(); }, [refresh, token]);
  const filtered = useMemo(() => extensions.filter((item) => `${item.display_name} ${item.description} ${item.kind}`.toLowerCase().includes(query.toLowerCase().trim())), [extensions, query]);
  const selected = filtered.find((item) => item.id === selectedExtensionId) || extensions.find((item) => item.id === selectedExtensionId) || filtered[0] || null;
  useEffect(() => { setConfigurationText(JSON.stringify(selected?.configuration || {}, null, 2)); }, [selected?.id, selected?.configuration]);
  const persistConfiguration = () => {
    if (!selected) return;
    try {
      const parsed: unknown = JSON.parse(configurationText);
      if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") throw new Error("Configuration must be a JSON object.");
      void saveConfiguration(selected.id, parsed as Record<string, unknown>);
    } catch (error) { useExtensionStore.getState().setError(error instanceof Error ? error.message : "Configuration must be a JSON object."); }
  };

  if (!token) return <div className="page-view">{header}<section className="extension-auth-gate"><div className="extension-gate-icon"><LockKeyhole size={21} /></div><div><div className="eyebrow compact">Trust boundary</div><h2>Sign in to inspect local extensions.</h2><p>Extension manifests are reviewed from this installation. Lifecycle controls, configuration, and Docker-only execution require an authenticated local operator session.</p></div></section></div>;

  return <div className="page-view extensions-view">
    {header}
    <section className="extension-hero">
      <div><div className="eyebrow compact">Reviewed local registry</div><h2>Extensions stay <em>contained.</em></h2><p>Only checked-in manifests appear here. Installs begin disabled, permission claims remain visible, and executable tools use the Docker sandbox or stop.</p></div>
      <div className="extension-hero-seal"><ShieldCheck size={19} /><span>Host execution<br />is never a fallback</span></div>
    </section>
    <div className="extension-toolbar"><label className="extension-search"><Search size={16} /><input aria-label="Search extensions" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search the reviewed catalog" /></label><button type="button" className="extension-refresh" onClick={() => void refresh()} disabled={isLoading || isSaving}>{isLoading ? "Refreshing…" : "Refresh catalog"}</button></div>
    {error && <div role="alert" className="extension-alert"><AlertTriangle size={16} />{error}</div>}
    <div className="extension-layout">
      <section className="extension-catalog" aria-label="Reviewed extension catalog">
        <div className="extension-section-heading"><span>Catalog</span><small>{filtered.length} reviewed package{filtered.length === 1 ? "" : "s"}</small></div>
        {filtered.length ? filtered.map((extension) => <button type="button" key={extension.id} className={`extension-row ${selected?.id === extension.id ? "selected" : ""}`} onClick={() => selectExtension(extension.id)}><span className="extension-row-icon"><Boxes size={17} /></span><span className="extension-row-copy"><strong>{extension.display_name}</strong><small>{extension.kind.replace("_", " ")} · v{extension.version}</small></span><StatusPill status={extension.status} /></button>) : <div className="extension-empty"><CircleOff size={18} />No reviewed extensions match this filter.</div>}
      </section>
      <section className="extension-detail" aria-live="polite">
        {selected ? <>
          <div className="extension-detail-heading"><div><div className="eyebrow compact">{selected.kind.replace("_", " ")}</div><h2>{selected.display_name}</h2></div><StatusPill status={selected.status} /></div>
          <p className="extension-description">{selected.description}</p>
          <div className="extension-detail-meta"><div><span className="extension-meta-label">Extension ID</span><code>{selected.id}</code></div><div><span className="extension-meta-label">Entrypoint</span><code>{selected.entrypoint || "No executable entrypoint"}</code></div></div>
          <div className="extension-permissions"><span className="extension-meta-label">Declared permissions</span><div>{selected.permissions.map((permission) => <span className="permission-chip" key={permission}><ShieldCheck size={13} />{permission}</span>)}</div></div>
          {selected.connector_provider && <p className="extension-connector-link"><ShieldCheck size={15} />Built-in adapter for the existing <strong>{selected.connector_provider === "github" ? "GitHub" : "Revit"}</strong> connector. Credentials remain in the local vault.</p>}
          <div className="extension-actions">
            {!selected.installed ? <button type="button" className="extension-primary" onClick={() => void install(selected.id)} disabled={isSaving}><Boxes size={16} />Install disabled</button> : <button type="button" className={`extension-toggle ${selected.enabled ? "enabled" : ""}`} onClick={() => void setEnabled(selected.id, !selected.enabled)} disabled={isSaving}><Power size={16} />{selected.enabled ? "Disable extension" : "Enable extension"}</button>}
            {selected.kind === "sandboxed_tool" && <button type="button" className="extension-run" onClick={() => void execute(selected.id)} disabled={!selected.enabled || isSaving}><Play size={15} fill="currentColor" />Run in Docker</button>}
          </div>
          {!selected.installed && <p className="extension-note"><LockKeyhole size={14} />Installation writes local state only. Enable separately after reviewing this manifest.</p>}
          {selected.installed && !selected.enabled && <p className="extension-note"><LockKeyhole size={14} />Disabled extensions cannot run. Enabling changes local lifecycle state; it does not grant host execution.</p>}
          {selected.installed && <section className="extension-configuration"><div><span className="extension-meta-label">Non-secret configuration</span><small>Credentials, tokens, and passwords are rejected here and remain in the local credential vault.</small></div><textarea aria-label="Extension configuration JSON" value={configurationText} onChange={(event) => setConfigurationText(event.target.value)} spellCheck={false} /><button type="button" className="extension-refresh" onClick={persistConfiguration} disabled={isSaving}>Save configuration</button></section>}
          {selected.last_error && <div role="alert" className="extension-alert"><AlertTriangle size={16} />{selected.last_error}</div>}
          {lastExecution?.extension_id === selected.id && <section className={`extension-execution ${lastExecution.state}`}><div><TerminalSquare size={17} /><strong>{lastExecution.state === "completed" ? "Sandbox result" : "Execution withheld"}</strong></div><p>{lastExecution.message}</p>{lastExecution.stdout && <pre>{lastExecution.stdout}</pre>}{lastExecution.stderr && <pre className="stderr">{lastExecution.stderr}</pre>}{lastExecution.state === "completed" && <small><CheckCircle2 size={13} />Exit code {lastExecution.exit_code ?? "n/a"}; output captured from the isolated execution boundary.</small>}</section>}
        </> : <div className="extension-empty"><Boxes size={20} />Select an extension to inspect its reviewed manifest.</div>}
      </section>
    </div>
  </div>;
}
