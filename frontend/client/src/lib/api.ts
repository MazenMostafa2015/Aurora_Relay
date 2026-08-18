// Aurora Relay style reminder: network boundaries should be quiet, typed, and explicit about failure.
import type { Tool, User } from "@/types/app";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export function describeApiError(error: unknown) {
  if (error instanceof ApiError && error.status === 401) return "The username or password was not accepted.";
  if (error instanceof Error) return error.message;
  return "The local service could not complete that request.";
}

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
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new ApiError(response.status, payload?.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  async me() { return request<User>("/auth/me"); },
  async login(username: string, password: string) {
    return request<{ access_token: string; user_id: string }>("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
  },
  async register(username: string, email: string, password: string) {
    return request<User>("/auth/register", { method: "POST", body: JSON.stringify({ username, email, password }) });
  },
  async logout() { return request<{ message: string }>("/auth/logout", { method: "POST" }); },
  async createTask(order: string, context: Record<string, unknown> = {}) {
    return request<Record<string, unknown>>("/tasks", { method: "POST", body: JSON.stringify({ order, context }) });
  },
  async listTasks() { return request<{ tasks: Record<string, unknown>[] }>("/tasks"); },
  async listTools() { return request<{ tools: Tool[] }>("/tools"); },
};
