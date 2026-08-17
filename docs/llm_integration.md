# Phase 3 LLM Integration Guide

**Author:** Manus AI

## Setup

Install the repository requirements from the project root:

```bash
python3 -m pip install -r requirements.txt
```

Ollama is expected at `http://localhost:11434` by default. Verify it with `curl http://localhost:11434/api/tags` and ensure the configured model is installed, for example `ollama pull phi3:mini`. The sandbox used for implementation did not have an Ollama daemon available, so live local inference must be verified on the user's machine.

Remote providers are optional. Set `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY` in the environment if cloud fallback is desired. The configuration file contains placeholders and does not contain secrets.

## Provider configuration

The default file is `backend/app/config/llm_config.json`. `LLMManager.from_config()` loads provider instances, expands environment-variable placeholders, selects the configured default provider, and enables cache and cost tracking according to the file.

```python
from app.core.llm import LLMManager

manager = LLMManager.from_config("backend/app/config/llm_config.json")
statuses = await manager.initialize_all()
print(statuses)
```

Provider priority is explicit. The manager tries the preferred provider first, then the configured default and remaining providers by ascending priority. An unavailable Ollama model therefore does not prevent a configured OpenAI or Anthropic fallback from being attempted.

## Direct chat

```python
from app.core.llm import Message

response = await manager.chat_with_fallback([
    Message("system", "You are concise and accurate."),
    Message("user", "Summarize the current task."),
])
print(response.content)
```

## MCP tool orchestration

`MCPToolOrchestrator` bridges the Phase 2 MCP client and the LLM manager. It converts discovered MCP tools to provider-neutral definitions, sends them to the model, executes returned tool calls through the MCP router, appends tool results to the conversation, and requests the final answer.

```python
from app.core.llm import MCPToolOrchestrator
from app.core.mcp import MCPClient

mcp = MCPClient("backend/app/config/mcp_servers.json")
await mcp.initialize()
await manager.initialize_all()

orchestrator = MCPToolOrchestrator(manager, mcp)
result = await orchestrator.run("demo", "List the files in the workspace and summarize them.")
print(result.content)

await mcp.close_all()
```

Tool names are qualified as `server:tool`, so collisions are rejected instead of silently selecting an arbitrary server. MCP server allowlists continue to apply beneath the LLM layer.

## Prompt templates and structured output

Use `PromptTemplates.planner_prompt()`, `executor_prompt()`, `coordinator_prompt()`, and `feedback_prompt()` to create role-specific messages. Use `parse_json_output()` when a planner or other model response must satisfy a JSON contract:

```python
plan = parse_json_output(response, {
    "type": "object",
    "required": ["steps"],
    "properties": {"steps": {"type": "array"}},
})
```

Malformed JSON and schema violations raise `StructuredOutputError` and should be reported as model-output failures rather than retried as transport failures.

## Context, cache, and cost tracking

`ContextManager` keeps multi-turn messages under a configured token budget while retaining system messages. `ResponseCache` avoids repeated identical calls and exposes hit/miss statistics. `CostTracker` records prompt and completion usage returned by providers and exports a JSON report. Ollama calls are recorded with zero API cost; remote pricing can be extended in `CostTracker.PRICING_PER_1K`.

```python
print(manager.cache.stats() if manager.cache else {})
print(manager.cost_tracker.summary() if manager.cost_tracker else {})
```

## Streaming

Use `provider.stream_chat()` for text-only streaming:

```python
provider = manager.get_provider("local")
async for chunk in provider.stream_chat([Message("user", "Explain MCP briefly.")]):
    print(chunk, end="", flush=True)
```

Tool-calling conversations use the non-streaming `chat()` path in the orchestrator so complete function arguments are available before an MCP call is executed.

## Testing and troubleshooting

Run `pytest -q` from the repository root. The suite covers provider models, fallback logic, Ollama response normalization, context truncation, cache behavior, structured output, cost accounting, and the existing Phase 1 and Phase 2 MCP infrastructure.

| Symptom | Resolution |
| --- | --- |
| `Connection refused` from Ollama | Start the Ollama daemon and verify port `11434`. |
| Model not installed | Run `ollama list` and `ollama pull <model>`; update `llm_config.json` if needed. |
| OpenAI or Anthropic fallback unavailable | Set the corresponding API key environment variable and confirm the model name. |
| Tool call name is not found | Refresh MCP discovery and use a qualified `server:tool` name. |
| Structured output fails | Inspect the model response, strengthen the prompt, or reduce the schema to the fields the model must produce. |
