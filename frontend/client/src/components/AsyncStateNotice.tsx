import { AlertTriangle, RefreshCw, WifiOff } from "lucide-react";

type AsyncStateNoticeProps = {
  error?: string | null;
  loading?: boolean;
  onRetry?: () => void;
  subject: string;
};

export function AsyncStateNotice({ error, loading = false, onRetry, subject }: AsyncStateNoticeProps) {
  if (loading) return <div className="async-state-notice loading" role="status" aria-live="polite"><RefreshCw size={16} className="spinning" /><span>Loading {subject}…</span></div>;
  if (!error) return null;
  return <div className="async-state-notice error" role="alert"><WifiOff size={16} /><div><strong>{subject} could not be refreshed.</strong><span>{error} Your saved local state is still available.</span></div>{onRetry && <button type="button" onClick={onRetry}><RefreshCw size={14} /> Try again</button>}<AlertTriangle size={16} aria-hidden="true" /></div>;
}
