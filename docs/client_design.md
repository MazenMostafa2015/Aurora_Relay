# MCP Client Design

**Author:** Manus AI

## Architecture overview

Phase 2 adds a high-level multi-server client under `backend/app/core/mcp`. The client separates configuration, transport lifecycle, tool discovery, routing, retry policy, and pooling. The production transport is delegated to the official MCP Python SDK, which already implements MCP framing and stdio lifecycle. This avoids maintaining a second JSON-RPC reader loop while retaining typed protocol models for tests, errors, and future transports.

| Component | Responsibility |
| --- | --- |
| `client.py` | Public facade for initialization, discovery, routed tool calls, health checks, and shutdown. |
| `connection.py` | One server session, stdio subprocess ownership, initialization timeout, SDK calls, health state, and graceful close. |
| `discovery.py` | Calls `tools/list`, normalizes SDK metadata, and applies per-server allowlists. |
| `router.py` | Resolves `tool` and `server:tool` names, rejects missing tools and ambiguous unqualified names. |
| `retry.py` | Bounded exponential backoff with jitter for transient connection failures. |
| `pool.py` | Bounded collection of connections plus reconnect-on-health-failure monitoring. |
| `config.py` | Validates and persists `mcpServers` configuration. |
| `protocol.py` | JSON-RPC envelope models and client-specific exception taxonomy. |

The official client tutorial describes the same core lifecycle: create stdio parameters, enter the transport and client session contexts, initialize, list tools, call tools, and allow the async context manager to close the session and subprocess [1]. The mcp-use project confirms the value of multi-server support, dynamic server selection, and tool restrictions, while this implementation keeps the lower-level foundation on the official SDK [2].

## Connection management strategy

Each `MCPConnection` has explicit `DISCONNECTED`, `CONNECTING`, `CONNECTED`, `ERROR`, and `CLOSING` states. Initialization is serialized by a lock. The connection starts a stdio subprocess through the SDK, awaits the initialization handshake with a configurable timeout, and stores the session only after initialization succeeds. Every list and call operation also has a timeout. Shutdown closes the SDK context stack and therefore the child transport; the pool then clears its references.

This follows the MCP lifecycle requirement that initialization is the first interaction, capability negotiation precedes normal operations, and transport shutdown should be graceful [3]. A failed connection is isolated: client initialization records that server as unavailable and continues initializing other configured servers.

## Tool discovery and registration

Discovery queries `tools/list` once per connected server during initialization. The client stores normalized descriptors keyed by `server:tool`, including the server name, description, input schema, and annotations. The configured `allowedTools` list is applied before registration, so disallowed tools never become routable. A subsequent explicit discovery refresh rebuilds the router and registry.

## Routing model

Qualified names such as `browser:browse_url` are always deterministic. An unqualified name is accepted only when exactly one server exposes it. If multiple servers expose the same name, the router raises `AmbiguousToolError` and tells the caller to qualify the name. This prevents silent calls to the wrong server.

## Error handling philosophy

Errors are divided into configuration, connection, timeout, routing, permission, and execution categories. Retry logic applies only to transient transport-like failures, never to validation, permission, ambiguity, missing-tool, or tool-execution errors. Error messages identify the server and operation. The SDK's typed call result remains available to callers, while tool results marked as errors are converted to `ToolExecutionError` at the client boundary.

## Performance and reliability considerations

The pool bounds the number of active server processes. Initialization is intentionally isolated per server and can be parallelized in a later optimization without changing the public API. Health checks use `tools/list` as a lightweight capability-level probe and reconnect failed sessions. Retry delays use exponential backoff with jitter and a hard maximum. Per-request timeouts prevent hung subprocesses from consuming tasks indefinitely.

## References

[1]: https://modelcontextprotocol.io/docs/2026-07-28/develop/build-client "Build an MCP client"
[2]: https://github.com/mcp-use/mcp-use/blob/main/libraries/python/README.md "mcp-use for Python"
[3]: https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle "MCP lifecycle specification"
