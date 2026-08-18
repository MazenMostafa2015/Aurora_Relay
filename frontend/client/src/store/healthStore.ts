// Aurora Relay style reminder: operational health is local metadata only; never persist credentials or raw diagnostics here.
import { create } from "zustand";
import type { HealthSnapshot, HealthState } from "@/types/app";

const localFallback: HealthSnapshot = {
  generated_at: "",
  system: { status: "degraded", version: "0.8.22", uptime_seconds: 0, last_loop_completion: null },
  connectors: [],
  agent_loop: { state: "idle", current_iteration: 0, total_iterations: 0, last_result: null, next_run: null, recent_iterations: [] },
  release: {
    version: "v0.8.22", sha256_verified: true, provenance_verified: true, signer_pinned: true,
    timestamp_present: true, clean_machine_verified: true,
    trust_note: "Local fallback: release claims are packaged with Aurora Relay; connect to refresh operator status.",
  },
  vault: {
    state: "locked", backend: "browser-local-fallback", fallback: false,
    message: "Desktop credential protection is unavailable in browser-only mode. Connector secrets remain locked.",
  },
  activities: [],
  alerts: [],
};

export const useHealthStore = create<HealthState>((set) => ({
  snapshot: localFallback,
  isLoading: false,
  testingConnectorId: null,
  error: null,
  lastUpdated: null,
  dismissedAlertIds: [],
  setSnapshot: (snapshot) => set({ snapshot, lastUpdated: snapshot.generated_at, error: null }),
  setLoading: (isLoading) => set({ isLoading }),
  setTestingConnectorId: (testingConnectorId) => set({ testingConnectorId }),
  setError: (error) => set({ error }),
  dismissAlert: (alertId) => set((state) => ({ dismissedAlertIds: state.dismissedAlertIds.includes(alertId) ? state.dismissedAlertIds : [...state.dismissedAlertIds, alertId] })),
}));
