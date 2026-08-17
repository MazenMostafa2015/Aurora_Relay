from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.agents.coordinator import Coordinator
from app.core.agents.hitl import HumanApprovalManager
from app.core.agents.memory import MemoryManager
from app.core.agents.planner import PlannerAgent
from app.core.agents.workflow import WorkflowEngine
from app.core.llm.provider import LLMResponse, Message
from app.core.models.task import Step, StepStatus, Task, TaskStatus
from app.core.utils.event_bus import EventBus
from app.core.utils.state_persistence import StatePersistence


class FakeLLM:
    async def chat_with_fallback(self, messages, tools=None, **kwargs):
        return LLMResponse(content='{"steps":[{"description":"Read files","tools_required":[]},{"description":"Summarize","dependencies":["step_1"],"tools_required":[]}]}' if any("planner" in (message.content or "").lower() for message in messages) else "done")


class FakeRouter:
    def list_all_tools(self):
        return {}


class FakeMCP:
    router = FakeRouter()
    async def call_tool(self, name, arguments):
        return {"content": [{"type": "text", "text": "ok"}]}


def test_task_dependency_progress_and_round_trip():
    task = Task(id="t", order="test")
    first = Step(id="s1", task_id="t", description="first", order=0)
    second = Step(id="s2", task_id="t", description="second", order=1, dependencies=["s1"])
    task.steps = [first, second]
    assert task.get_next_step().id == "s1"
    first.status = StepStatus.COMPLETED
    assert task.get_next_step().id == "s2"
    assert task.get_progress() == 50
    assert Task.from_dict(task.to_dict()).steps[1].dependencies == ["s1"]


def test_memory_manager_relevance_and_consolidation():
    memory = MemoryManager(max_short_term=2)
    memory.add_short_term("browser result about AI", {"topic": "news"}, importance=0.9)
    memory.add_short_term("unrelated", {}, importance=0.1)
    assert memory.get_short_term("AI")[0].content.startswith("browser")
    assert memory.consolidate_memories(0.8) == 1
    assert len(memory.long_term) == 1

@pytest.mark.asyncio
async def test_planner_creates_dependency_plan():
    planner = PlannerAgent(FakeLLM())
    task = await planner.create_plan(Task(id="t", order="plan"))
    assert task.status == TaskStatus.PLANNED
    assert len(task.steps) == 2
    assert task.steps[1].dependencies == [task.steps[0].id]

@pytest.mark.asyncio
async def test_planner_rejects_cycle():
    planner = PlannerAgent(FakeLLM())
    with pytest.raises(ValueError):
        planner._validate_steps([Step(id="a", dependencies=["b"]), Step(id="b", dependencies=["a"])])

@pytest.mark.asyncio
async def test_workflow_runs_dependencies():
    task = Task(id="t")
    first = Step(id="a", task_id="t", order=0)
    second = Step(id="b", task_id="t", order=1, dependencies=["a"])
    task.steps = [first, second]
    order = []
    async def execute(step, context):
        order.append(step.id)
        step.status = StepStatus.COMPLETED
        return step
    result = await WorkflowEngine().run(task, execute)
    assert result.status == TaskStatus.COMPLETED
    assert order == ["a", "b"]

@pytest.mark.asyncio
async def test_hitl_approval():
    hitl = HumanApprovalManager()
    step = Step(id="s", description="sensitive")
    await hitl.request_approval("t", step)
    hitl.approve("t", "s")
    assert await hitl.wait_for_decision("t", "s") is True


def test_state_persistence(tmp_path: Path):
    persistence = StatePersistence(tmp_path)
    task = Task(id="persist", order="save")
    persistence.save_task(task)
    loaded = persistence.load_task("persist")
    assert loaded and loaded.id == "persist"
    assert persistence.list_tasks() == ["persist"]
    assert persistence.delete_task("persist") is True

@pytest.mark.asyncio
async def test_event_bus_delivers_and_filters():
    events = EventBus()
    received = []
    async def listener(event_type, data):
        received.append((event_type, data["task_id"]))
    events.subscribe("task_completed", listener)
    await events.emit("task_completed", {"task_id": "t"})
    assert received == [("task_completed", "t")]
    assert events.get_history(task_id="t")[0]["type"] == "task_completed"

@pytest.mark.asyncio
async def test_coordinator_end_to_end_with_fake_dependencies(tmp_path: Path):
    coordinator = Coordinator(FakeMCP(), FakeLLM(), persistence=StatePersistence(tmp_path))
    task_id = await coordinator.submit_order("u", "make a plan")
    status = await coordinator.get_task_status(task_id)
    assert status["status"] == "completed"
    assert status["progress"] == 100
