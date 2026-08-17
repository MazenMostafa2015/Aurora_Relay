"""Phase 1 validation workflow for browser + filesystem MCP servers."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mcp_servers.common.mcp_client import MCPClient
from mcp_servers.common.protocol import content_text


async def main() -> None:
    root = ROOT
    config = root / "mcp_servers" / "config.json"
    async with MCPClient(config) as client:
        statuses = await client.get_server_health()
        tools = await client.discover_tools()
        print(json.dumps({"health": statuses, "tools": tools}, indent=2))
        search_result = await client.call_tool("browser", "search_web", {"query": "latest AI advancements news", "num_results": 5})
        text = content_text(search_result)
        try:
            parsed = json.loads(text)
            report = "Latest AI advancements search results\n\n" + "\n".join(f"- {item.get('title', 'Untitled')}: {item.get('url', '')}" for item in parsed.get("results", []))
        except json.JSONDecodeError:
            report = f"Latest AI advancements search results\n\n{text}"
        await client.call_tool("filesystem", "write_file", {"path": "ai_news.txt", "content": report})
        print(f"Wrote {root / 'workspace' / 'ai_news.txt'}")


if __name__ == "__main__":
    asyncio.run(main())
