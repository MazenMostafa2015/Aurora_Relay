import json

import pytest

from mcp_servers.browser import server


def test_invalid_url_rejected():
    with pytest.raises(Exception):
        server._validate_url("file:///etc/passwd")


def test_http_url_accepted():
    assert server._validate_url("https://example.com") == "https://example.com"


@pytest.mark.asyncio
async def test_browse_url_returns_structured_content(monkeypatch):
    class FakePage:
        url = "https://example.com"
        async def goto(self, *args, **kwargs): pass
        async def title(self): return "Example"
        def locator(self, selector): return self
        async def inner_text(self, **kwargs): return "hello"
    async def fake_get_page():
        return FakePage()
    monkeypatch.setattr(server, "_get_page", fake_get_page)
    raw = await server.browse_url("https://example.com")
    payload = json.loads(raw) if isinstance(raw, str) else raw
    if "content" in payload and isinstance(payload["content"], list):
        payload = json.loads(payload["content"][0]["text"])
    assert payload["title"] == "Example"
    assert payload["content"] == "hello"
