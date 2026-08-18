// Aurora Relay style reminder: extension state is local, explicit, and never holds secrets or executable code.
import { create } from "zustand";
import type { ExtensionManifestRecord, ExtensionState } from "@/types/app";

export const useExtensionStore = create<ExtensionState>((set) => ({
  extensions: [],
  selectedExtensionId: null,
  query: "",
  isLoading: false,
  isSaving: false,
  error: null,
  lastExecution: null,
  setExtensions: (extensions: ExtensionManifestRecord[]) => set((state) => ({
    extensions,
    selectedExtensionId: state.selectedExtensionId && extensions.some((item) => item.id === state.selectedExtensionId)
      ? state.selectedExtensionId
      : extensions[0]?.id || null,
  })),
  selectExtension: (selectedExtensionId) => set({ selectedExtensionId, lastExecution: null }),
  setQuery: (query) => set({ query }),
  setLoading: (isLoading) => set({ isLoading }),
  setSaving: (isSaving) => set({ isSaving }),
  setError: (error) => set({ error }),
  setLastExecution: (lastExecution) => set({ lastExecution }),
}));
