// Aurora Relay connector state: local metadata only; credentials stay transient.
import { create } from "zustand";
import type { ConnectorRecord, ConnectorState, RevitPlan } from "@/types/app";

export const useConnectorStore = create<ConnectorState>((set) => ({
  connectors: [],
  selectedConnectorId: null,
  query: "",
  isLoading: false,
  isSaving: false,
  error: null,
  pendingRevitPlan: null,
  setQuery: (query) => set({ query }),
  selectConnector: (selectedConnectorId) => set({ selectedConnectorId }),
  setLoading: (isLoading) => set({ isLoading }),
  setSaving: (isSaving) => set({ isSaving }),
  setError: (error) => set({ error }),
  setConnectors: (connectors) => set((state) => ({ connectors, selectedConnectorId: state.selectedConnectorId && connectors.some((item) => item.id === state.selectedConnectorId) ? state.selectedConnectorId : connectors[0]?.id || null })),
  upsertConnector: (connector: ConnectorRecord) => set((state) => ({ connectors: [...state.connectors.filter((item) => item.id !== connector.id), connector].sort((a, b) => a.sort_order - b.sort_order) })),
  removeConnector: (connectorId) => set((state) => ({ connectors: state.connectors.filter((item) => item.id !== connectorId), selectedConnectorId: state.selectedConnectorId === connectorId ? null : state.selectedConnectorId })),
  setPendingRevitPlan: (pendingRevitPlan: RevitPlan | null) => set({ pendingRevitPlan }),
}));
