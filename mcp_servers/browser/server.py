"""Playwright-backed browser automation MCP server.

The server uses stdio by default so it can be launched by an MCP host. Logs are
sent to stderr/file through the shared logger and never to stdout.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from urllib.parse import quote, urlparse

from fastmcp import FastMCP
from playwright.async_api import Browser, Page, async_playwright

from mcp_servers.common.error_handler import ValidationError, configure_logging, handle_mcp_error

mcp = FastMCP("Browser-Server")
logger = configure_logging(os.getenv("MCP_LOG_PATH"))
_playwright = None
_browser: Browser | None = None
_page: Page | None = None


def _validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValidationError("URL must be an absolute http(s) URL.")
    return url


async def _get_page() -> Page:
    global _playwright, _browser, _page
    if _page and not _page.is_closed():
        return _page
    _playwright = await async_playwright().start()
    browser_name = os.getenv("PLAYWRIGHT_BROWSER", "chromium")
    launcher = getattr(_playwright, browser_name, None)
    if launcher is None:
        raise ValidationError(f"Unsupported browser engine: {browser_name}")
    _browser = await launcher.launch(headless=os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() != "false")
    context = await _browser.new_context()
    _page = await context.new_page()
    return _page


async def _close_browser() -> None:
    global _playwright, _browser, _page
    if _browser:
        await _browser.close()
    if _playwright:
        await _playwright.stop()
    _browser = _page = _playwright = None


@mcp.tool(annotations={"readOnlyHint": True})
@handle_mcp_error
async def browse_url(url: str) -> str:
    """Navigate to an HTTP(S) URL and return its title and readable page content."""
    page = await _get_page()
    await page.goto(_validate_url(url), wait_until="domcontentloaded", timeout=30_000)
    text = await page.locator("body").inner_text(timeout=10_000)
    return json.dumps({"url": page.url, "title": await page.title(), "content": text[:100_000]}, ensure_ascii=False)


@mcp.tool(annotations={"readOnlyHint": True})
@handle_mcp_error
async def search_web(query: str, num_results: int = 10) -> str:
    """Search the public web using Bing and return result titles, URLs, and snippets."""
    if not query.strip():
        raise ValidationError("query must not be empty.")
    if not 1 <= num_results <= 50:
        raise ValidationError("num_results must be between 1 and 50.")
    page = await _get_page()
    await page.goto(f"https://www.bing.com/search?q={quote(query)}", wait_until="domcontentloaded", timeout=30_000)
    results = await page.locator("li.b_algo h2 a").evaluate_all("""(links, limit) => links.map(a => ({title: (a.innerText || '').trim(), url: a.href})).filter(x => x.title && /^https?:/.test(x.url)).slice(0, limit)""", num_results)
    return json.dumps({"query": query, "results": results}, ensure_ascii=False)


@mcp.tool
@handle_mcp_error
async def click_element(selector: str) -> str:
    """Click a CSS selector on the current page and return the resulting URL and title."""
    page = await _get_page()
    await page.locator(selector).first.click(timeout=30_000)
    await page.wait_for_load_state("domcontentloaded", timeout=30_000)
    return json.dumps({"url": page.url, "title": await page.title()})


@mcp.tool
@handle_mcp_error
async def extract_data(selector: str, attribute: str = "textContent") -> str:
    """Extract text or an HTML attribute from all elements matching a CSS selector."""
    if not selector.strip():
        raise ValidationError("selector must not be empty.")
    page = await _get_page()
    locator = page.locator(selector)
    count = await locator.count()
    values = []
    for index in range(count):
        element = locator.nth(index)
        values.append(await element.get_attribute(attribute) if attribute != "textContent" else await element.text_content())
    return json.dumps({"selector": selector, "attribute": attribute, "values": values})


@mcp.tool
@handle_mcp_error
async def fill_form(selector: str, value: str) -> str:
    """Fill a form field identified by CSS selector with a value."""
    if not selector.strip():
        raise ValidationError("selector must not be empty.")
    page = await _get_page()
    await page.locator(selector).fill(value, timeout=30_000)
    return json.dumps({"selector": selector, "filled": True})


@mcp.tool
@handle_mcp_error
async def wait_for(selector: str, timeout: int = 30_000) -> str:
    """Wait for a CSS selector to become visible, with a bounded timeout in milliseconds."""
    if not 1 <= timeout <= 120_000:
        raise ValidationError("timeout must be between 1 and 120000 milliseconds.")
    page = await _get_page()
    await page.locator(selector).wait_for(state="visible", timeout=timeout)
    return json.dumps({"selector": selector, "visible": True})


@mcp.tool
@handle_mcp_error
async def take_screenshot(filename: str | None = None) -> str:
    """Capture the current page to a workspace-local PNG and return its path."""
    page = await _get_page()
    directory = Path(os.getenv("MCP_ARTIFACT_DIR", "./artifacts")).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename or "browser.png").name
    if not safe_name.lower().endswith(".png"):
        safe_name += ".png"
    path = directory / safe_name
    await page.screenshot(path=str(path), full_page=True)
    return json.dumps({"path": str(path)})


if __name__ == "__main__":
    mcp.run(transport=os.getenv("MCP_TRANSPORT", "stdio"))
