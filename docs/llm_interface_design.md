# LLM Integration Layer Design

**Author:** Manus AI

## Scope

Phase 3 adds a provider-neutral LLM layer above the Phase 2 MCP client. The application can register local Ollama models and remote OpenAI or Anthropic models behind one interface. The same normalized `Message`, `ToolDefinition`, and `LLMResponse` objects are used by all providers, while each adapter converts them to its provider-native request and response format.

## Provider comparison

| Provider | Transport | Tool calling | Cost model | Operational role |
| --- | --- | --- | --- | --- |
| Ollama | Local HTTP at `/api/chat` | Native tools when the selected model supports them | Local compute; tracked as zero API cost | Default offline/private provider. |
| OpenAI | Async Chat Completions API | `tools` function definitions and structured tool calls | Token-based remote API pricing | High-quality cloud fallback. |
| Anthropic | Async Messages API | `tools` with JSON input schemas and `tool_use` blocks | Token-based remote API pricing | Alternative cloud fallback and long-context option. |

OpenAI function calling represents tools as function definitions and returns structured tool calls in assistant messages [1]. Anthropic's Messages API represents tools with JSON input schemas and returns `tool_use` content blocks [2]. Ollama's chat endpoint accepts message history and can return tool calls for compatible models [3]. The adapters normalize these differences before the manager or MCP orchestrator sees them.

## Unified interface

The base provider exposes `initialize()`, `chat()`, `stream_chat()`, `extract_tool_calls()`, and `get_model_name()`. Configuration contains provider, model, credentials or base URL, sampling parameters, timeout, priority, and metadata. The normalized response preserves text, normalized tool calls, finish reason, usage, model, provider, and the raw provider response for diagnostics.

## Tool-calling implementation

The MCP client discovers tools as `server:tool` descriptors. The LLM orchestrator converts each descriptor into a `ToolDefinition` with its description and JSON input schema. When a provider returns a tool call, the orchestrator resolves the qualified name through the MCP router, executes the MCP tool, appends the result as a tool message, and calls the model again. The loop is bounded by `max_rounds` to avoid runaway tool recursion.

> Tool descriptions are untrusted data from the MCP server. The orchestrator routes only to discovered and allowlisted tools, and the MCP server remains responsible for its own path, navigation, and destructive-operation safety checks.

## Prompt engineering strategy

`PromptTemplates` provides four roles. The planner is instructed to return a machine-readable plan with dependencies and risks. The executor receives one step plus prior context and is instructed to use tools precisely. The coordinator handles user requests and decides whether planning is necessary. The feedback template compares prior output with user feedback. Tool descriptions are passed separately through the provider tool schema rather than being duplicated into free-form prompts.

Structured output is parsed from plain JSON or JSON fenced blocks. A lightweight schema validator checks required fields, primitive types, nested objects, and arrays. This lets planner responses be validated without forcing the application to depend on a single schema library.

## Context management

`ConversationContext` stores messages, metadata, timestamps, and an estimated token count. The default estimate is deliberately conservative and inexpensive; provider usage remains authoritative when available. When a context exceeds its limit, system messages are preserved and the oldest non-system messages are removed until the target is satisfied. The context manager provides conversation lookup, message addition, retrieval, and clearing.

## Caching and cost controls

`ResponseCache` uses a deterministic SHA-256 key over provider, messages, tools, and request parameters. It is bounded by TTL and maximum entries and records hit/miss statistics. Caching is enabled by default in configuration but can be disabled per manager or per call. `CostTracker` records usage returned by remote providers, applies configurable model pricing, and treats Ollama as zero API cost. Unknown remote models are conservatively recorded at zero unless pricing is explicitly added, avoiding fabricated price claims.

## Streaming

Each provider implements `stream_chat()` as an async iterator of text deltas. OpenAI consumes streamed choice deltas, Anthropic consumes `text_stream`, and Ollama consumes newline-delimited JSON objects. The orchestration loop uses non-streaming `chat()` for tool calls because complete structured tool-call arguments are required before MCP execution; user-facing text can use `stream_chat()` when no tool loop is required.

## Fallback and error handling

The manager orders providers by explicit preference and configured priority. A failed provider is logged and the next provider is attempted. Configuration, tool validation, malformed structured output, and MCP permission errors are not hidden by provider fallback. Provider credentials are read from environment-variable placeholders and are never written to logs or configuration output. Local Ollama failures are expected when the daemon or requested model is unavailable; the manager can fall back to remote providers when credentials are configured.

## References

[1]: https://platform.openai.com/docs/guides/function-calling "OpenAI Function Calling"
[2]: https://docs.anthropic.com/en/docs/build-with-claude/tool-use "Anthropic Tool Use"
[3]: https://docs.ollama.com/capabilities/tool-calling "Ollama Tool Calling"
[4]: https://modelcontextprotocol.io/docs/learn/architecture "Model Context Protocol architecture"
