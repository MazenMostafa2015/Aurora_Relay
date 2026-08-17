from __future__ import annotations

import pytest

from app.core.agents.workflow import WorkflowEngine
from app.core.models.task import Step, StepStatus


@pytest.mark.asyncio
async def test_dependency_aware_workflow_completes_in_order():
    executed: list[str] = []

    async def run_step(step: Step):
        executed.append(step.id)
        return {"step": step.id, "status": "success"}

    steps = [
        Step(id="first", description="first", depends_on=[]),
        Step(id="second", description="second", depends_on=["first"]),
    ]
    engine = WorkflowEngine(max_concurrency=2)
    result = await engine.run(steps, run_step)
    assert result["status"] == "completed"
    assert executed == ["first", "second"]
    assert all(step.status == StepStatus.COMPLETED for step in steps)
