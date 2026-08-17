"""Basic Phase 2 MCP client usage example."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.core.mcp import MCPClient
from mcp_servers.common.protocol import content_text


async def main() -> None:
    config_path = ROOT / "backend" / "app" / "config" / "mcp_servers.json"
    async with MCPClient(config_path) as client:
        print("Connected servers:", list(client.connections))
        print("Available tools:", json.dumps(client.router.list_all_tools(), indent=2))
        result = await client.call_tool("filesystem:list_directory", {"path": "."})
        print("Filesystem result:", content_text(result)[:500])
        print("Health:", await client.health_check())


if __name__ == "__main__":
    asyncio.run(main())
