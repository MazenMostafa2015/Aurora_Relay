import json

import pytest

from mcp_servers.filesystem import server


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_DIR", str(tmp_path))
    return tmp_path


def test_path_traversal_rejected(workspace):
    with pytest.raises(Exception):
        server.safe_path("../outside.txt")


@pytest.mark.asyncio
async def test_write_read_list_info_delete(workspace):
    written = json.loads(await server.write_file("notes/hello.txt", "hello"))
    assert written["written"] is True
    assert await server.read_file("notes/hello.txt") == "hello"
    listing = json.loads(await server.list_directory("notes"))
    assert listing["entries"][0]["name"] == "hello.txt"
    info = json.loads(await server.get_file_info("notes/hello.txt"))
    assert info["type"] == "file"
    deleted = json.loads(await server.delete_file("notes/hello.txt"))
    assert deleted["deleted"] is True


@pytest.mark.asyncio
async def test_error_is_actionable(workspace):
    with pytest.raises(Exception, match="does not exist"):
        await server.read_file("missing.txt")
