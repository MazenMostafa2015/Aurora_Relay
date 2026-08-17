# Phase 2 MCP Client Research Notes

The Phase 2 design was cross-checked against the official Python SDK, the mcp-use Python library, the official MCP client tutorial, and the lifecycle specification.

| Source | Findings relevant to this implementation |
| --- | --- |
| [1] Official Python SDK | The SDK provides both client and server APIs, supports stdio, Streamable HTTP, and SSE, and exposes a high-level `Client` whose async context manager owns the connection lifecycle. Tool calls return a `CallToolResult`, with `content`, `structured_content`, and an error flag. |
| [2] mcp-use Python README | Multi-server support, dynamic server selection, tool restrictions, and direct programmatic MCP access are useful patterns. The library is an optional higher-level agent/client framework; this project keeps the foundation on the official SDK to minimize duplicated protocol handling. |
| [3] Official build-client tutorial | The recommended stdio flow is to create server parameters, open `stdio_client`, enter an async client session, initialize, list tools, call tools, and let the async context manager close the session and subprocess. Tool results should be read from typed content blocks and their error state should be preserved. |
| [4] MCP lifecycle specification | Initialization must be the first interaction, must negotiate protocol version and capabilities, and must be followed by `notifications/initialized`. Normal requests follow only after initialization. stdio shutdown should close the child input stream, wait, then terminate/kill if necessary. Requests should have configurable timeouts and cancellation/error handling. |

## Architecture implication

The Phase 2 client should wrap the official SDK rather than reimplement JSON-RPC framing for production transport. A small protocol module remains valuable for typed JSON-RPC message models, error codes, and test doubles. Connection objects should expose explicit states, serialized initialization, configurable request timeouts, bounded retries, and graceful shutdown. Tool discovery should normalize metadata and enforce per-server allowlists. Routing should index unique tool names and reject ambiguous or unavailable calls instead of guessing.

## References

[1]: https://github.com/modelcontextprotocol/python-sdk "Official MCP Python SDK"
[2]: https://github.com/mcp-use/mcp-use/blob/main/libraries/python/README.md "mcp-use Python README"
[3]: https://modelcontextprotocol.io/docs/2026-07-28/develop/build-client "Build an MCP client"
[4]: https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle "MCP lifecycle specification"
