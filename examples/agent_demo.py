"""Run the Phase 4 agent orchestrator against local Ollama and MCP servers."""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.core.agents.coordinator import Coordinator
from app.core.llm.manager import LLMManager
from app.core.mcp.client import MCPClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def main() -> None:
    llm = LLMManager.from_config(ROOT / "backend/app/config/llm_config.json")
    provider_status = await llm.initialize_all()
    if not provider_status.get("local", False):
        print("Ollama is unavailable. Start it and pull the configured model, then retry.")
        print("Example: ollama serve && ollama pull phi3:mini")
        return

    mcp = MCPClient(ROOT / "backend/app/config/mcp_servers.json")
    try:
        statuses = await mcp.initialize()
        if not any(statuses.values()):
            print("No MCP server connected; check the Phase 1 server configuration.")
            return
        coordinator = Coordinator(mcp, llm)

        async def on_event(event_type: str, data: dict) -> None:
            print(f"[{event_type}] task={data.get('task_id')} progress={data.get('progress', 0):.1f}%")

        coordinator.add_event_listener("*", on_event)
        task_id = await coordinator.submit_order("demo-user", "List the workspace files and create a concise summary file named agent_summary.txt")
        print((await coordinator.get_task_status(task_id)) or {})
    finally:
        await mcp.close_all()


if __name__ == "__main__":
    asyncio.run(main())
