# MCP Research Notes

The official MCP documentation at https://modelcontextprotocol.io/llms-full.txt was reviewed on 2026-08-14.

Key findings:

- MCP servers expose three primary capability families: resources (file-like data), tools (callable functions), and prompts (reusable prompt templates).
- Local MCP servers commonly use stdio transport. The client launches the server subprocess and communicates through standard input/output. Remote deployments can use Streamable HTTP.
- A stdio server must never write logs to stdout because stdout carries JSON-RPC messages; logs must go to stderr or a file.
- The client lifecycle includes creating transport parameters, opening the transport/session, initializing the client, listing tools, and calling tools through the SDK.
- The implementation should use the official Python MCP SDK for client interoperability where possible, while FastMCP provides the decorator-based server API requested in the project brief.
- Tool metadata should include names, descriptions, input schemas, and annotations such as readOnlyHint and destructiveHint. Tool failures should be represented as structured MCP tool errors and accompanied by actionable messages.
- The MCP layer should keep transport concerns separate from tool implementation, validate inputs at the server boundary, and avoid leaking secrets through logs or error text.

The project brief's use of stdio for local Python servers is appropriate for this phase. Streamable HTTP is reserved for a later remote deployment surface, with authentication and origin validation added when HTTP exposure is introduced.

## Reference

[1]: https://modelcontextprotocol.io/llms-full.txt "Official MCP documentation (full text)"
