from __future__ import annotations

from typing import Any


PLANNER_RESPONSE: dict[str, Any] = {
    "steps": [
        {"id": "step-1", "description": "Inspect the workspace", "tool": "filesystem.list_directory", "depends_on": []},
        {"id": "step-2", "description": "Summarize the result", "tool": "filesystem.read_file", "depends_on": ["step-1"]},
    ]
}

TOOL_RESULT = {"status": "success", "content": "workspace contains README.md and data/"}


def fake_tool_registry() -> dict[str, dict[str, Any]]:
    return {
        "filesystem.list_directory": {"server": "filesystem", "description": "List workspace files", "schema": {}},
        "filesystem.read_file": {"server": "filesystem", "description": "Read a workspace file", "schema": {}},
        "browser.search": {"server": "browser", "description": "Search the web", "schema": {}},
    }
