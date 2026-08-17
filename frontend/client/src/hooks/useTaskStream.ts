// Aurora Relay style reminder: live activity should feel immediate without hiding connection truth.
import { useEffect } from "react";
import { useAppStore } from "@/store/appStore";

export function useTaskStream(taskId: string) {
  const setConnected = useAppStore((state) => state.setConnected);
  const addEvent = useAppStore((state) => state.addEvent);
  useEffect(() => {
    const configured = import.meta.env.VITE_WS_BASE_URL;
    if (!configured || !taskId) {
      setConnected(false);
      return;
    }
    const socket = new WebSocket(`${configured}/ws`);
    socket.onopen = () => {
      setConnected(true);
      socket.send(JSON.stringify({ type: "subscribe", task_id: taskId }));
    };
    socket.onmessage = (message) => {
      try {
        const payload = JSON.parse(message.data) as { type?: string; payload?: { label?: string; detail?: string } };
        addEvent({ id: `live-${Date.now()}`, time: "now", label: payload.type || "Live update", detail: payload.payload?.detail || payload.payload?.label || "The coordinator sent a new event.", kind: "signal" });
      } catch {
        // Ignore malformed frames; the stream is supplementary to the task state.
      }
    };
    socket.onerror = () => setConnected(false);
    socket.onclose = () => setConnected(false);
    return () => socket.close();
  }, [addEvent, setConnected, taskId]);
}
