from __future__ import annotations

import pytest

from mcp_servers.common.server_discovery import ServerDiscovery


def test_configured_mcp_servers_are_discoverable():
    config_path = "/home/ubuntu/projects/mcp-aplication-36e0710f/mcp_servers/config.json"
    discovery = ServerDiscovery(config_path)
    servers = discovery.discover()
    names = {server.name for server in servers}
    assert {"browser", "filesystem"}.issubset(names)


@pytest.mark.asyncio
async def test_filesystem_server_exposes_tools():
    from mcp_servers.filesystem.server import mcp
    tools = await mcp.list_tools()
    names = {tool.name for tool in tools}
    assert "list_directory" in names
    assert "read_file" in names
