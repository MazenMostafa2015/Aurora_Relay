# Sandboxed Code Execution

Phase 5 adds a Docker-backed code execution capability to the MCP and agent stack. The Code-Executor MCP server exposes `execute_python`, `execute_javascript`, `execute_shell`, `execute_with_data`, `create_file_in_sandbox`, and `sandbox_capabilities`.

## Configuration

Defaults are in `backend/app/config/sandbox_config.json`. The manager uses Python 3.11 slim for Python and Shell execution and Node 20 slim for JavaScript. The default policy has no network, a read-only root filesystem, all Linux capabilities dropped, no-new-privileges, one CPU, 512 MiB memory, 128 processes, a 100 MiB temporary filesystem, a 120-second hard maximum, and a one MiB output cap.

## Direct usage

```python
from app.core.sandbox.manager import SandboxManager

manager = SandboxManager(workspace_root="workspace")
await manager.initialize()
container_id = await manager.create_sandbox(language="python")
try:
    result = await manager.execute_code(container_id, "print(2 + 2)", language="python", timeout=10)
    print(result["stdout"], result["exit_code"])
finally:
    await manager.destroy_sandbox(container_id)
```

The manager fails closed when the Docker SDK or daemon is unavailable. It does not silently execute arbitrary code on the host.

## MCP server

Run the server from the repository root with:

```bash
python3 -m app.core.mcp_servers.code_executor.server
```

Register the command in the host’s MCP configuration with the repository root on `PYTHONPATH`. The server creates a fresh short-lived container for each tool call and removes it in a `finally` block. Tool results are structured dictionaries containing `success`, `exit_code`, `stdout`, `stderr`, `execution_time`, `language`, `timed_out`, `output_truncated`, and monitor metrics.

## Docker images

Build the supplied images with:

```bash
docker compose -f docker/docker-compose.sandbox.yml --profile sandbox-images build
```

The Compose profile is intentionally an image-build helper rather than a permanent execution service. The manager creates per-run containers with its own resource and security settings. Do not add a Docker socket mount, `privileged: true`, host networking, or host namespace modes.

## Validation

Run the full suite with `pytest -q`. The test suite exercises configuration validation, traversal protection, resource truncation, mocked container lifecycle, fail-closed Docker behavior, and MCP tool registration. A Docker-backed smoke test should be run on a Docker-enabled host with approved images before production deployment.

## Troubleshooting

If initialization reports that the Docker SDK is missing, install the project requirements. If it reports that Docker is unavailable, start Docker or use a deployment with rootless Docker enabled. If an execution times out, the container is killed and removed; inspect the returned `timed_out` field and audit record. If output is truncated, retrieve a smaller result or write a bounded artifact to the staged workspace rather than printing it.
