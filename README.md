[README.md](https://github.com/user-attachments/files/31152124/README.md)
# Aurora_Relay
assets were replaced with self-contained artwork, and production API calls now follow Electron’s randomized loopback origin. 
# MCP Server Foundation

This repository implements Phases 1 through 4 of the AI application: Browser and Filesystem MCP servers, a multi-server MCP client, a provider-neutral LLM layer supporting OpenAI, Anthropic, and local Ollama models, and an agent orchestration core that plans, executes, monitors, persists, and streams user tasks.

## Setup

From the repository root, install Python dependencies with `python3 -m pip install -r requirements.txt` and install the Playwright browser with `python3 -m playwright install chromium`. The servers use stdio by default. The configured workspace is `./workspace`; logs are written under `./logs`.

## Run and Test

Run `pytest -q` to execute the unit tests. Launch a server directly with `python3 -m mcp_servers.filesystem.server` or `python3 -m mcp_servers.browser.server`. An MCP host should launch them from the repository root using the commands in `mcp_servers/config.json`. The Phase 2 client example is `python3 examples/basic_usage.py`; the Phase 3 Ollama plus MCP example is `python3 examples/llm_mcp_demo.py`. MCP configuration is in `backend/app/config/mcp_servers.json`, and LLM provider configuration is in `backend/app/config/llm_config.json`.

The proof of concept can be run with `python3 scripts/validate_workflow.py`. It searches for AI news through the browser server, then saves the gathered report to `workspace/ai_news.txt` through the filesystem server. The Phase 4 agent demonstration is `python3 examples/agent_demo.py`; it connects Ollama, the MCP client, and the Coordinator, then reports live task events. The Phase 5 sandbox demonstration is `PYTHONPATH=backend python3 examples/sandbox_demo.py`; it runs Python, JavaScript, and Shell code in Docker containers and fails closed when Docker is unavailable. Agent configuration is in `backend/app/config/agent_config.json`, sandbox configuration is in `backend/app/config/sandbox_config.json`, and durable task state is stored under `data/tasks/` by default. The script also prints the discovered tools and health status.

## Structure

| Path | Responsibility |
| --- | --- |
| `mcp_servers/browser/server.py` | Playwright browser tools |
| `mcp_servers/filesystem/server.py` | Workspace-safe file tools |
| `mcp_servers/common/mcp_client.py` | Phase 1 official SDK client lifecycle and tool calls |
| `backend/app/core/mcp/client.py` | Phase 2 multi-server client facade |
| `backend/app/core/mcp/connection.py` | Per-server SDK connection lifecycle |
| `backend/app/core/mcp/discovery.py` | Tool discovery and registration |
| `backend/app/core/mcp/router.py` | Qualified and ambiguity-safe tool routing |
| `backend/app/core/mcp/pool.py` | Connection pooling and health monitoring |
| `backend/app/core/mcp/retry.py` | Retry policy with exponential backoff |
| `backend/app/core/mcp/config.py` | Validated server configuration management |
| `mcp_servers/common/server_discovery.py` | JSON configuration discovery and manifests |
| `mcp_servers/common/error_handler.py` | Structured errors and observability |
| `docs/mcp_protocol_summary.md` | Protocol, transport, and security decisions |
| `docs/mcp_servers.md` | Tool reference and troubleshooting |
| `scripts/validate_workflow.py` | Phase 1 multi-server validation demonstration |
| `examples/basic_usage.py` | Phase 2 client usage example |
| `docs/client_design.md` | Phase 2 design rationale and research references |
| `docs/mcp_client.md` | Phase 2 client API and operations guide |
| `backend/app/core/llm/provider.py` | Provider-neutral LLM contracts and normalized response models |
| `backend/app/core/llm/openai_provider.py` | OpenAI adapter |
| `backend/app/core/llm/anthropic_provider.py` | Anthropic adapter |
| `backend/app/core/llm/ollama_provider.py` | Local Ollama adapter |
| `backend/app/core/llm/manager.py` | Provider registry, fallback, caching, and cost hooks |
| `backend/app/core/llm/tool_orchestrator.py` | LLM-to-MCP tool-calling loop |
| `backend/app/core/llm/context.py` | Conversation context management |
| `backend/app/core/llm/cache.py` | TTL response cache |
| `backend/app/core/llm/structured.py` | JSON structured-output parsing and validation |
| `backend/app/core/llm/cost_tracker.py` | Usage and cost tracking |
| `backend/app/config/llm_config.json` | LLM provider configuration |
| `docs/llm_interface_design.md` | Phase 3 design and provider research |
| `docs/llm_integration.md` | Phase 3 setup and API guide |
| `examples/llm_mcp_demo.py` | Ollama plus MCP end-to-end example |
| `backend/app/core/agents/coordinator.py` | Main task orchestration lifecycle |
| `backend/app/core/agents/planner.py` | LLM-driven plan creation and validation |
| `backend/app/core/agents/executor.py` | Step execution through MCP tools |
| `backend/app/core/agents/monitor.py` | Progress, timing, alerts, and failure recovery |
| `backend/app/core/agents/memory.py` | Short-term, long-term, and task memory |
| `backend/app/core/agents/hitl.py` | Human approval gates for sensitive steps |
| `backend/app/core/agents/workflow.py` | Dependency-aware bounded concurrency |
| `backend/app/core/utils/state_persistence.py` | Atomic JSON task persistence |
| `backend/app/core/utils/event_bus.py` | Async task and step event streaming |
| `backend/app/config/agent_config.json` | Phase 4 agent configuration |
| `docs/agent_orchestration.md` | Phase 4 architecture and operations guide |
| `examples/agent_demo.py` | Full agent orchestration example |
| `backend/app/core/sandbox/manager.py` | Docker sandbox lifecycle and execution |
| `backend/app/core/sandbox/config.py` | Validated sandbox policy configuration |
| `backend/app/core/sandbox/security.py` | Security hardening and suspicious-event audit |
| `backend/app/core/sandbox/resources.py` | CPU, memory, PID, timeout, and output policies |
| `backend/app/core/sandbox/filesystem.py` | Staged workspace and traversal protection |
| `backend/app/core/sandbox/monitor.py` | Execution metrics and audit monitoring |
| `backend/app/core/mcp_servers/code_executor/server.py` | Code Execution MCP tools |
| `docker/sandbox/Dockerfile.python` | Non-root Python execution image |
| `docker/sandbox/Dockerfile.node` | Non-root Node.js execution image |
| `docker/docker-compose.sandbox.yml` | Hardened sandbox image build profile |
| `backend/app/config/sandbox_config.json` | Phase 5 sandbox configuration |
| `docs/sandbox_security.md` | Threat model and security controls |
| `docs/sandbox_execution.md` | Phase 5 API and operations guide |
| `examples/sandbox_demo.py` | Docker-backed execution example |

## Security Notes

Do not place API keys, passwords, cookies, or authorization headers in configuration files or logs. Keep the filesystem workspace dedicated to agent-created artifacts. Review `allowedTools` before enabling destructive capabilities. HTTP deployment is intentionally deferred; when added, it must include authentication, origin validation, and session isolation.


## Phase 8: Integration, Testing, and Deployment Preparation

Phase 8 adds deterministic integration fixtures, API/MCP/agent/sandbox coverage, frontend Playwright smoke tests, a dependency-free async health load harness, security scanning configuration, production Dockerfiles, a full Docker Compose stack, Prometheus/Grafana observability, structured request logs, and CI automation.

### Validate locally

```bash
PYTHONPATH=backend pytest -q tests backend/tests
python -m compileall -q backend mcp_servers
cd frontend && pnpm validate
cd frontend && pnpm exec playwright install chromium && pnpm test:e2e
cd .. && docker compose config
```

### Run the production-like stack

```bash
cp .env.example .env
# Replace every development secret in .env
docker compose up --build -d
```

See `docs/deployment.md`, `docs/developer_guide.md`, `docs/user_guide.md`, and `docs/production_readiness.md` for operational guidance. The system is deployment-prepared, but production certification still requires environment-specific database, TLS, backup, load, security, sandbox-isolation, and observability checks.


## Desktop application foundation

The repository now includes `desktop/`, an Electron-based shell for Aurora Relay. It starts the packaged FastAPI backend on a randomized loopback port, waits for the health endpoint, serves the bundled React frontend through the local service, and keeps mutable state under the platform-specific user data directory. Local SQLite is the default desktop database, and the first-run wizard prefers Ollama while keeping cloud providers and diagnostics opt-in.

The renderer is isolated with disabled Node integration, context isolation, and Chromium sandboxing. The preload bridge exposes only narrowly scoped status, tray, quit, and validated external-link operations. The code-execution sandbox remains fail-closed; desktop packaging does not enable host execution when Docker or an approved sandbox runtime is unavailable.

Build the desktop foundation with the following command after installing PyInstaller and desktop dependencies:

```bash
FRONTEND_DIR=/path/to/frontend desktop/scripts/build-all.sh dir
```

Use `win`, `mac`, `linux`, or `all` for platform targets. Native Windows and macOS builds, code signing, notarization, update-feed publishing, Ollama distribution, and clean-machine installation tests must run in the appropriate release environments. The current package is **configuration-ready, not production-certified** until those gates pass.
