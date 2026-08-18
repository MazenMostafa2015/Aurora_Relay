import { create } from "zustand";
import type { AgentLoopIteration, AgentLoopRecord, AgentLoopState } from "@/types/app";

export const useAgentLoopStore = create<AgentLoopState>((set) => ({
  loops: [],
  selectedLoopId: null,
  iterations: [],
  isLoading: false,
  isSaving: false,
  error: null,
  setLoops: (loops) => set((state) => ({
    loops,
    selectedLoopId: state.selectedLoopId && loops.some((item) => item.id === state.selectedLoopId)
      ? state.selectedLoopId
      : loops[0]?.id || null,
  })),
  upsertLoop: (loop: AgentLoopRecord) => set((state) => ({
    loops: [...state.loops.filter((item) => item.id !== loop.id), loop].sort((a, b) => b.created_at.localeCompare(a.created_at)),
    selectedLoopId: state.selectedLoopId || loop.id,
  })),
  selectLoop: (selectedLoopId) => set({ selectedLoopId, iterations: [] }),
  setIterations: (iterations: AgentLoopIteration[]) => set({ iterations }),
  setLoading: (isLoading) => set({ isLoading }),
  setSaving: (isSaving) => set({ isSaving }),
  setError: (error) => set({ error }),
}));
