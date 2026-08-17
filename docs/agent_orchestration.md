# Phase 4 Agent Orchestration Core

## Overview

The Agent Orchestration Core is the application layer above the Phase 2 MCP client and Phase 3 LLM manager. It accepts a user order, asks the planner to produce a validated dependency graph, executes ready steps through MCP tools, monitors progress and failures, persists task state, and emits events for user interfaces or API adapters.

## Architecture

| Component | Responsibility | Primary integration |
|---|---|---|
| `Coordinator` | Entry point and task lifecycle owner | MCP client, LLM manager, all agents |
| `PlannerAgent` | Converts an order into bounded, dependency-aware steps | `LLMManager.chat_with_fallback` |
| `ExecutorAgent` | Executes a step and its model-selected MCP tool calls | `MCPClient.call_tool` |
| `MonitorAgent` | Reports progress, timing, alerts, and retry decisions | Task and step models |
| `MemoryManager` | Maintains short-term, long-term, and task-scoped memory | Coordinator and prompts |
| `HumanApprovalManager` | Pauses sensitive steps until an explicit decision | Coordinator and event bus |
| `WorkflowEngine` | Runs dependency-ready steps with bounded concurrency | Executor callback |
| `StatePersistence` | Atomically stores resumable task JSON | Coordinator |
| `EventBus` | Publishes task, step, approval, and failure events | UI/API adapters |

## Task lifecycle

A task moves through `created`, `planning`, `planned`, `executing`, and one of `completed`, `failed`, `cancelled`, or `waiting_for_input`. Every step has its own status, retry count, timestamps, dependencies, tool-call records, and optional approval gate. The planner's JSON is validated before execution; unknown dependencies are removed and cycles are rejected rather than allowed to deadlock the workflow.

The workflow engine selects steps whose dependencies are complete. Independent steps may execute concurrently up to `max_parallel_steps`; dependent steps wait until their prerequisites finish. The coordinator persists state after creation, planning, and each step update, which makes task inspection and recovery possible after process restarts.

## Human approval

Set `requires_approval` on a planned step to pause the task before execution. The coordinator emits `approval_required` with the task and step identifiers. An integration can call `approve_step(task_id, step_id)` or `reject_step(task_id, step_id)`. Rejection fails the step and task; approval resumes execution.

## Events and streaming

The `EventBus` supports exact event subscriptions and a wildcard subscription. Events include `task_created`, `planning_started`, `planning_completed`, `step_started`, `step_completed`, `step_failed`, `approval_required`, `task_completed`, `task_failed`, and `task_cancelled`. `Coordinator.stream_updates(task_id)` provides an async iterator suitable for server-sent events or WebSocket adapters.

## Persistence and recovery

Task state is written as JSON under `data/tasks` by default. Writes use a temporary file, `fsync`, and atomic replacement. `StatePersistence.load_task()` reconstructs typed `Task` and `Step` instances. Use `cleanup_old_tasks(days)` for retention maintenance. The current Phase 4 foundation intentionally keeps persistence file-based and local; a later phase can replace the repository with a database implementation behind the same interface.

## Configuration

The defaults are in `backend/app/config/agent_config.json`:

| Setting | Default | Meaning |
|---|---:|---|
| `max_steps` | 20 | Maximum steps accepted from a plan |
| `max_parallel_steps` | 4 | Maximum independent steps running at once |
| `default_step_retries` | 3 | Retry budget for failed steps |
| `approval_timeout_seconds` | 3600 | Maximum approval wait used by integrations |
| `event_history_limit` | 1000 | In-memory event history bound |
| `task_storage_dir` | `data/tasks` | Durable task state directory |

## Example

```python
coordinator = Coordinator(mcp_client, llm_manager)
task_id = await coordinator.submit_order("user-1", "Find AI news and save a summary")
status = await coordinator.get_task_status(task_id)
```

For a complete local wiring example, see `examples/agent_demo.py`. The example uses Ollama through the Phase 3 manager and the existing Browser and Filesystem MCP servers. Live inference requires the user's local Ollama daemon and configured model.
