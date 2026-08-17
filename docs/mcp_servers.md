# MCP Server Foundation Guide

This Phase 1 foundation contains two local stdio MCP servers and a shared client/discovery layer. The browser server exposes Playwright automation, while the filesystem server exposes workspace-scoped file operations. The client reads `mcp_servers/config.json`, launches configured processes, initializes MCP sessions, discovers tools, enforces allowlists, and performs health checks.

## Browser Server

| Tool | Purpose | Annotation |
| --- | --- | --- |
| `browse_url` | Navigate to an HTTP(S) page and return title and readable body text. | `readOnlyHint: true` |
| `search_web` | Search Google and return result titles and URLs. | `readOnlyHint: true` |
| `click_element` | Click the first matching CSS selector. | default |
| `extract_data` | Extract text or an HTML attribute from matching elements. | default |
| `fill_form` | Fill a CSS-selected form field. | default |
| `wait_for` | Wait for a CSS selector to become visible. | default |
| `take_screenshot` | Save a full-page PNG under the artifact directory. | default |

Browser configuration is controlled by `PLAYWRIGHT_BROWSER`, `PLAYWRIGHT_HEADLESS`, `MCP_LOG_PATH`, and `MCP_ARTIFACT_DIR`. The server is headless by default and refuses non-HTTP(S) URLs.

## Filesystem Server

| Tool | Purpose | Annotation |
| --- | --- | --- |
| `read_file` | Read UTF-8 text within the workspace. | `readOnlyHint: true` |
| `write_file` | Create or overwrite a UTF-8 text file. | default |
| `list_directory` | List immediate entries and basic metadata. | `readOnlyHint: true` |
| `delete_file` | Delete a file or empty directory. | `destructiveHint: true` |
| `get_file_info` | Read type, size, mode, and modification metadata. | `readOnlyHint: true` |

`WORKSPACE_DIR` is the security boundary. Every path is resolved and checked with `Path.relative_to`; attempts to escape the directory are rejected. Delete intentionally refuses non-empty directories.

## Common Workflows

Start a server directly from the repository root with `python3 -m mcp_servers.filesystem.server` or `python3 -m mcp_servers.browser.server`. The recommended integration path is to use `MCPClient` with `mcp_servers/config.json`, call `connect_all_servers()`, then `discover_tools()`. A call should always use the server name and discovered tool name rather than bypassing the allowlist.

For the proof of concept, the orchestrator should call `browser.search_web`, optionally call `browser.browse_url` and `browser.extract_data` for selected sources, format the result, and call `filesystem.write_file` with `ai_news.txt`. The included demo script performs this sequence with deterministic fallback content if a live search is unavailable.

## Troubleshooting

| Symptom | Likely cause | Resolution |
| --- | --- | --- |
| Client cannot initialize | Dependency missing or incorrect module path. | Install requirements and run from the repository root. |
| Protocol stream is corrupted | Server wrote logs to stdout. | Keep logging on stderr or file; never use `print()` in stdio server code. |
| Browser launch fails | Playwright browser binary is absent. | Run `python -m playwright install chromium`. |
| File operation is denied | Path escapes `WORKSPACE_DIR`. | Use a workspace-relative path without `..`. |
| Tool is unavailable | Tool is omitted from `allowedTools`. | Add it explicitly to the server configuration after review. |
| Delete fails on a directory | Only empty directories are deletable. | Remove files first, then delete the directory. |
