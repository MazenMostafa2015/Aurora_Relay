# Phase 2 MCP Client Guide

**Author:** Manus AI

## Overview

The Phase 2 client connects to the Browser and Filesystem MCP servers from Phase 1, discovers their tools, and routes calls across them. It uses the official Python MCP SDK for stdio transport and session lifecycle, while the local modules provide configuration, registration, routing, retries, and health monitoring.

## Configuration

The default configuration is `backend/app/config/mcp_servers.json`. Each entry under `mcpServers` defines a command, arguments, environment variables, an optional `allowedTools` list, a request `timeout`, and retry settings.

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "python3",
      "args": ["-m", "mcp_servers.filesystem.server"],
      "env": {"WORKSPACE_DIR": "/absolute/path/to/workspace"},
      "allowedTools": ["read_file", "write_file", "list_directory"],
      "timeout": 30,
      "maxRetries": 2,
      "retryBaseDelay": 0.25
    }
  }
}
```

`MCPConfig` validates commands, argument types, timeout values, retry counts, and environment objects. Environment values support shell-style variable expansion. Configuration can also be created or updated through `add_server()` and removed with `remove_server()`.

## Basic usage

```python
import asyncio
from backend.app.core.mcp import MCPClient

async def main() -> None:
    client = MCPClient("backend/app/config/mcp_servers.json")
    statuses = await client.initialize()
    print(statuses)
    print(client.router.list_all_tools())

    result = await client.call_tool("list_directory", {"path": "."})
    print(result)
    await client.close_all()

asyncio.run(main())
```

For application code, prefer the async context manager so shutdown occurs even when a call fails:

```python
async with MCPClient("backend/app/config/mcp_servers.json") as client:
    result = await client.call_tool("filesystem:list_directory", {"path": "."})
```

## API reference

| API | Description |
| --- | --- |
| `MCPClient.initialize()` | Connects each configured server independently and discovers tools from successful connections. Returns `{server: bool}` statuses. |
| `MCPClient.discover_tools()` | Refreshes tool metadata and rebuilds the router registry. |
| `MCPClient.call_tool(name, arguments, server_name=None)` | Calls a unique unqualified tool or a qualified `server:tool` name. |
| `MCPClient.health_check()` | Probes connections and attempts a reconnect when a probe fails. |
| `MCPClient.close_all()` | Cancels monitoring, closes all SDK contexts, and clears routing state. |
| `ToolRouter.list_all_tools()` | Returns registered descriptors keyed by `server:tool`. |
| `MCPConfig.add_server()` / `remove_server()` | Mutates and persists configuration. |

## Discovery and routing

Discovery applies each server's allowlist before registering tools. Calls such as `read_file` route automatically when there is one matching server. Calls such as `filesystem:read_file` are explicit and are recommended in workflows where multiple servers may expose similar names. An unqualified call that matches more than one server raises `AmbiguousToolError` instead of guessing.

## Error handling and retries

The client exposes distinct exception classes for malformed configuration, failed connections, timeouts, missing tools, ambiguous routes, allowlist violations, and tool execution failures. Retry policy is bounded and applies only to transient connection-like failures. Validation and permission errors fail immediately. Configure `maxRetries`, `retryBaseDelay`, and `timeout` per server.

## Health monitoring

`ConnectionPool.start_health_monitoring()` starts a cancellable periodic task. Each check uses `tools/list` as a capability-level liveness probe. Failed connections are disconnected and reconnected. The pool is bounded by `max_connections`.

## Performance tuning

Use a smaller timeout for quick filesystem tools and a larger timeout for browser navigation. Keep `maxRetries` low for non-idempotent operations such as writes or deletes. Increase the pool limit only when the application needs more concurrent server processes. Tool discovery is cached in the client registry until `discover_tools()` is called again.

## Troubleshooting

| Symptom | Likely cause | Resolution |
| --- | --- | --- |
| A server status is `false` | Command, module path, environment, or dependency failure | Run the configured command manually and inspect the server log. |
| Tool not found | Tool is not exposed or was filtered by `allowedTools` | Refresh discovery and check the allowlist. |
| Ambiguous tool error | Multiple servers expose the same unqualified name | Use `server:tool` qualification. |
| Request timeout | Server is hung or timeout is too low | Inspect server logs and increase only the affected server timeout. |
| Repeated retries | Transport or subprocess instability | Check process limits, command paths, and stderr logs; do not increase retries blindly. |

## Validation

Run the complete suite from the repository root:

```bash
pytest -q
python3 -m compileall -q backend mcp_servers scripts
```

The Phase 2 tests cover retry backoff, routing ambiguity, configuration round-tripping and validation, and multi-server client discovery and calls. The existing Phase 1 tests remain part of the same suite.
