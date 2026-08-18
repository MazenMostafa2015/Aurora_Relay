// Aurora Relay style reminder: preserve the dark editorial command center, with inspectable evidence and restrained cyan signals.
import { CheckCircle2, Copy, Download, ExternalLink, FileBadge2, Fingerprint, ShieldCheck, Stamp } from "lucide-react";
import { toast } from "sonner";

const release = {
  version: "v0.8.22",
  publishedAt: "18 Aug 2026",
  revision: "1ebf09a8723c91d5657e5c3cd58902124ae0c487",
  releaseUrl: "https://github.com/MazenMostafa2015/Aurora_Relay/releases/tag/v0.8.22",
  workflowUrl: "https://github.com/MazenMostafa2015/Aurora_Relay/actions/runs/32170293193",
  installerSha256: "04b83c2a92fec1fab981f5036087f31cd3946eb8b488dc3a93005ccbb577df18",
  signerThumbprint: "223DEC322FF229C490C144320FB6B51EC23A6C2F",
  timestampEndpoint: "http://timestamp.digicert.com",
};

const assets = [
  { name: "Aurora-Relay-0.8.22-win-x64.exe", kind: "Windows installer", size: "158.7 MiB", href: "https://github.com/MazenMostafa2015/Aurora_Relay/releases/download/v0.8.22/Aurora-Relay-0.8.22-win-x64.exe", primary: true },
  { name: "SHA256SUMS", kind: "Integrity manifest", size: "99 B", href: "https://github.com/MazenMostafa2015/Aurora_Relay/releases/download/v0.8.22/SHA256SUMS" },
  { name: "provenance.json", kind: "Build provenance", size: "819 B", href: "https://github.com/MazenMostafa2015/Aurora_Relay/releases/download/v0.8.22/provenance.json" },
  { name: "clean-machine-evidence.json", kind: "Installation evidence", size: "1.1 KiB", href: "https://github.com/MazenMostafa2015/Aurora_Relay/releases/download/v0.8.22/clean-machine-evidence.json" },
];

function CopyValue({ value, label }: { value: string; label: string }) {
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      toast.success(`${label} copied`);
    } catch {
      toast.error(`Could not copy ${label.toLowerCase()}`);
    }
  };
  return <button type="button" className="evidence-copy" onClick={() => void copy()} aria-label={`Copy ${label}`}><Copy size={13} /></button>;
}

export function ReleaseEvidenceView({ header }: { header: React.ReactNode }) {
  return <div className="page-view release-evidence-view">
    {header}
    <section className="release-evidence-hero" aria-label="Release summary">
      <div>
        <div className="eyebrow compact">Signed release record</div>
        <h2>Every artifact,<br /><em>accounted for.</em></h2>
        <p>Inspect the published Windows installer, its integrity manifest, provenance, signer pin, and clean-machine verification without leaving the local operator workspace.</p>
      </div>
      <div className="release-hero-status"><span className="release-status-orb"><ShieldCheck size={19} /></span><div><strong>Release verified</strong><small>{release.version} · {release.publishedAt}</small></div></div>
    </section>

    <section className="release-evidence-summary" aria-label="Release integrity summary">
      <article><CheckCircle2 size={17} /><div><span>Integrity manifest</span><strong>Digest matched</strong><small>SHA-256 checked against the published manifest.</small></div></article>
      <article><FileBadge2 size={17} /><div><span>Build provenance</span><strong>Tag resolved</strong><small>Protected workflow and source revision recorded.</small></div></article>
      <article><Download size={17} /><div><span>Clean machine</span><strong>Install passed</strong><small>Silent install, local health check, and uninstall completed.</small></div></article>
    </section>

    <div className="release-evidence-layout">
      <section className="release-assets-panel" aria-labelledby="release-assets-heading">
        <div className="release-section-heading"><div><div className="eyebrow compact">Published payload</div><h2 id="release-assets-heading">Release assets</h2></div><a className="release-link" href={release.releaseUrl} target="_blank" rel="noreferrer">Open release <ExternalLink size={14} /></a></div>
        <div className="release-assets-list">
          {assets.map((asset) => <article className={`release-asset ${asset.primary ? "primary" : ""}`} key={asset.name}>
            <span className="release-asset-icon"><Download size={16} /></span>
            <div className="release-asset-copy"><strong>{asset.name}</strong><span>{asset.kind} <i /> {asset.size}</span></div>
            <a className="asset-download" href={asset.href} target="_blank" rel="noreferrer" aria-label={`Download ${asset.name}`}>{asset.primary ? "Download" : "Open"} <ExternalLink size={13} /></a>
          </article>)}
        </div>
      </section>

      <section className="release-proof-panel" aria-labelledby="release-proof-heading">
        <div className="release-section-heading"><div><div className="eyebrow compact">Verification chain</div><h2 id="release-proof-heading">Evidence ledger</h2></div><a className="release-link subtle" href={release.workflowUrl} target="_blank" rel="noreferrer">Workflow <ExternalLink size={14} /></a></div>
        <dl className="release-ledger">
          <div><dt><Fingerprint size={14} /> Installer SHA-256</dt><dd><code>{release.installerSha256}</code><CopyValue value={release.installerSha256} label="Installer SHA-256" /></dd></div>
          <div><dt><FileBadge2 size={14} /> Source revision</dt><dd><code>{release.revision}</code><CopyValue value={release.revision} label="Source revision" /></dd></div>
          <div><dt><Stamp size={14} /> Signer pin</dt><dd><code>{release.signerThumbprint}</code><CopyValue value={release.signerThumbprint} label="Signer thumbprint" /></dd></div>
        </dl>
        <div className="release-evidence-note"><ShieldCheck size={16} /><div><strong>Internal trust boundary</strong><p>The installer is timestamped through <code>{release.timestampEndpoint}</code>. Clean-machine evidence confirms timestamp presence and the pinned internal signer; it does not claim public commercial-certificate trust.</p></div></div>
      </section>
    </div>
  </div>;
}
