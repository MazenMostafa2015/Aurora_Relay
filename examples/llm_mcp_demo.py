"""End-to-end local Ollama plus MCP tool-calling demonstration."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.core.llm import LLMManager, MCPToolOrchestrator
from app.core.mcp import MCPClient


async def main() -> None:
    llm = LLMManager.from_config(ROOT / "backend" / "app" / "config" / "llm_config.json")
    statuses = await llm.initialize_all()
    print("LLM provider status:", statuses)
    if not statuses.get("local"):
        print("Ollama is unavailable. Start Ollama and install the configured model before retrying.")
        return

    mcp = MCPClient(ROOT / "backend" / "app" / "config" / "mcp_servers.json")
    await mcp.initialize()
    try:
        orchestrator = MCPToolOrchestrator(llm, mcp)
        response = await orchestrator.run("demo", "List the files in the workspace and summarize what you find.")
        print(response.content or "The model returned no final text.")
    finally:
        await mcp.close_all()


if __name__ == "__main__":
    asyncio.run(main())
