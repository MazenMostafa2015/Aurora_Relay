# User Guide

Aurora Relay is a private AI command center for submitting work, inspecting agent progress, and reviewing the tools used to complete a task.

## Workspace navigation

The Overview shows the task composer, active thread, signal feed, recent work, and operational counters. Task desk focuses on the selected task and its step progress. Tool explorer shows the registered capabilities and the server that owns each tool. Settings contains workspace defaults and account connection status.

## Submitting work

Describe the outcome you want in the task composer, add context when available, and select **Run task**. The agent creates a plan, requests approval for sensitive actions according to policy, executes eligible steps, and records tool calls and results. The UI is designed to keep the plan and evidence visible rather than hide work behind a single loading state.

## Approvals and history

Sensitive or irreversible steps should pause for approval. Review the proposed action and its scope before approving. Task history keeps the status, start time, duration, tags, and selected task details available for review. Do not paste passwords, API keys, private keys, or regulated personal information into task context.

## Connection behavior

The frontend can run in local-first mode with seeded state when the backend is unavailable. When connected, authenticated API responses and WebSocket events replace the local activity feed. A disconnected or stale connection should be treated as a signal to verify backend health rather than as proof that a task completed.
