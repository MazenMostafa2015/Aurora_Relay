# MCP Protocol Summary

**Author:** Manus AI  
**Scope:** Phase 1 MCP server foundation

## Overview

The Model Context Protocol (MCP) standardizes how an AI host discovers and invokes capabilities exposed by external servers. An MCP server can publish **tools**, **resources**, and **prompts**. Tools are callable functions intended for model-directed actions, resources expose file-like information for client consumption, and prompts provide reusable interaction templates [1]. This project begins with tools because browser automation and workspace file operations are the first execution capabilities required by the orchestrator.

The protocol uses a JSON-RPC message model with an initialization handshake, capability negotiation, discovery methods such as `tools/list`, and execution methods such as `tools/call`. The client foundation keeps the server configuration, transport lifecycle, tool discovery, access allowlists, and health checks separate from the tool implementations.

## Transport Decisions

| Transport | Phase 1 decision | Rationale |
| --- | --- | --- |
| stdio | **Primary transport** | Local Python servers are launched as subprocesses by the orchestrator. stdio avoids exposing a network listener and is the simplest secure default for development. |
| Streamable HTTP | Deferred extension | Appropriate for remote or separately deployed servers, but it requires authentication, origin validation, session management, and deployment hardening. |

The official documentation explicitly warns that stdio servers must not write logs to stdout because stdout carries protocol messages [1]. Accordingly, this implementation routes logs to stderr or JSON-lines files and reserves stdout for the MCP transport.

## Core Design Decisions

| Area | Decision |
| --- | --- |
| Server API | Use `FastMCP` decorators for readable tool registration and explicit annotations. |
| Client API | Use the official Python MCP SDK for stdio session lifecycle, initialization, `tools/list`, and `tools/call`. |
| Validation | Validate URL schemes, bounded timeouts, selectors, workspace paths, and allowed tool names at the boundary. |
| Tool results | Return JSON or text that is directly useful to an agent. Expected failures are structured with `isError: true`, a stable code, and an actionable message. |
| Observability | Log timestamps, tool names, success/failure, error codes, and duration without secrets or page credentials. |
| Filesystem safety | Resolve every path against a configured workspace and reject any path that escapes it. Destructive deletion is annotated with `destructiveHint`. |
| Browser safety | Allow only HTTP(S) navigation, run headless by default, and store screenshots under a configured artifact directory. |

## Authentication and Security

The Phase 1 local stdio configuration does not require network authentication because the host launches the server locally. The design still treats configuration and environment variables as sensitive: credentials should be injected by the host environment rather than committed to JSON, and logs must not contain passwords, cookies, authorization headers, or full form contents.

If Streamable HTTP is added, the deployment must require authenticated requests, validate the `Origin` header, bind safely, apply request limits, and isolate each user session. Browser automation should use a dedicated browser context per session, while filesystem access should remain scoped to an explicit workspace and reject symlink/path traversal escapes.

## References

[1]: https://modelcontextprotocol.io/llms-full.txt "Official MCP documentation"
