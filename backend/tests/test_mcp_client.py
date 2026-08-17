from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.core.mcp.client import MCPClient
from app.core.mcp.config import MCPConfig, ServerConfig
from app.core.mcp.protocol import AmbiguousToolError, ConfigurationError, ToolDescriptor
from app.core.mcp.retry import RetryConfig, retry_with_backoff
from app.core.mcp.router import ToolRouter


class FakeConnection:
    def __init__(self, config):
        self.name = config.name
        self.config = config
        self.state = SimpleNamespace(value="connected")
        self.calls = []
        self.failures = 0

    async def list_tools(self):
        return SimpleNamespace(tools=[SimpleNamespace(name="echo", description="Echo text", inputSchema={"type": "object"}, annotations={})])

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if self.failures:
            self.failures -= 1
            raise ConnectionError("temporary")
        return {"result": arguments}

    async def health_check(self):
        return True


@pytest.mark.asyncio
async def test_retry_with_backoff_retries_transient_errors():
    attempts = 0

    async def operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise TimeoutError("temporary")
        return "ok"

    result = await retry_with_backoff(operation, RetryConfig(max_retries=2, base_delay=0, jitter=0))
    assert result == "ok"
    assert attempts == 3


def test_router_rejects_ambiguous_unqualified_tools():
    router = ToolRouter()
    router.register([ToolDescriptor("one", "echo"), ToolDescriptor("two", "echo")])
    with pytest.raises(AmbiguousToolError):
        router.resolve("echo")
    assert router.resolve("one:echo").server_name == "one"


def test_config_validates_and_round_trips(tmp_path):
    path = tmp_path / "mcp_servers.json"
    path.write_text(json.dumps({"mcpServers": {"demo": {"command": "python3", "args": ["-V"], "timeout": 3}}}))
    config = MCPConfig(path)
    assert config.get("demo").timeout == 3
    config.add_server("other", {"command": "node", "maxRetries": 0})
    assert "other" in json.loads(path.read_text())["mcpServers"]


def test_config_rejects_empty_command(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"mcpServers": {"bad": {"command": ""}}}')
    with pytest.raises(ConfigurationError):
        MCPConfig(path)


@pytest.mark.asyncio
async def test_client_initializes_discovers_and_routes(monkeypatch, tmp_path):
    path = tmp_path / "mcp_servers.json"
    path.write_text(json.dumps({"mcpServers": {"demo": {"command": "python3", "allowedTools": ["echo"]}}}))
    fake = FakeConnection(ServerConfig.from_dict("demo", {"command": "python3", "allowedTools": ["echo"]}))

    async def fake_add(self, config):
        return fake

    monkeypatch.setattr("app.core.mcp.client.ConnectionPool.add", fake_add)
    monkeypatch.setattr("app.core.mcp.client.ConnectionPool.get", lambda self, name: fake)
    client = MCPClient(path)
    statuses = await client.initialize()
    assert statuses == {"demo": True}
    assert "demo:echo" in client.tool_registry
    result = await client.call_tool("echo", {"value": "hello"})
    assert result == {"result": {"value": "hello"}}
    assert fake.calls == [("echo", {"value": "hello"})]
