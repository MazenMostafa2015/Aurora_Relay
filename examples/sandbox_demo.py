"""Run Phase 5 sandbox examples on a Docker-enabled host."""
from __future__ import annotations

import asyncio

from app.core.sandbox.manager import SandboxManager


async def run_one(manager: SandboxManager, language: str, code: str) -> None:
    container_id = await manager.create_sandbox(language)
    try:
        result = await manager.execute_code(container_id, code, language, timeout=10)
        print(f"[{language}] success={result['success']} exit={result['exit_code']}")
        print(result["stdout"] or result["stderr"])
    finally:
        await manager.destroy_sandbox(container_id)


async def main() -> None:
    manager = SandboxManager(workspace_root="workspace")
    try:
        await manager.initialize()
    except RuntimeError as exc:
        print(f"Sandbox unavailable: {exc}")
        print("Start Docker and retry; no code is executed on the host.")
        return
    try:
        await run_one(manager, "python", "print({'answer': 2 + 2})")
        await run_one(manager, "javascript", "console.log(JSON.stringify({answer: 2 + 2}))")
        await run_one(manager, "shell", "printf 'sandbox shell\\n'")
        print(manager.monitor.get_global_metrics())
    finally:
        await manager.cleanup_all()


if __name__ == "__main__":
    asyncio.run(main())
