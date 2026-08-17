// Aurora Relay style reminder: network boundaries should be quiet, typed, and explicit about failure.
import type { Task, Tool, User } from "@/types/app";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (
  import.meta.env.DEV
    ? "http://127.0.0.1:8000/api/v1"
    : `${window.location.origin}/api/v1`
);

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem("aurora-token");
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers || {}),
    },
  });
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json() as Promise<T>;
}

export const api = {
  async me() { return request<User>("/auth/me"); },
  async login(username: string, password: string) {
    return request<{ access_token: string; user_id: string }>("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
  },
  async createTask(order: string, context: Record<string, unknown> = {}) {
    return request<Task>("/tasks", { method: "POST", body: JSON.stringify({ order, context }) });
  },
  async listTasks() { return request<{ tasks: Task[] }>("/tasks"); },
  async listTools() { return request<{ tools: Tool[] }>("/tools"); },
};
