"""Provider adapters isolated from database and API code.

Adapters return structured, secret-free data. Live provider credentials are
injected by ``ConnectorService`` only for the duration of a request.
"""
from __future__ import annotations

import base64
import asyncio
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx


class ConnectorAdapterError(RuntimeError):
    pass


@dataclass(slots=True)
class AdapterResult:
    message: str
    data: dict[str, Any]


def _require(value: dict[str, Any], *names: str) -> tuple[Any, ...]:
    missing = [name for name in names if value.get(name) in (None, "")]
    if missing:
        raise ConnectorAdapterError(f"Missing required input: {', '.join(missing)}")
    return tuple(value[name] for name in names)


class GitHubAdapter:
    provider = "github"
    capabilities = ["repository.read", "issue.write", "pull_request.write", "release.write", "workflow.dispatch", "contents.write"]
    mutation_actions = {"create_issue", "create_pull_request", "create_release", "dispatch_workflow", "create_or_update_file"}

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.transport = transport

    @staticmethod
    def _base_url(configuration: dict[str, Any]) -> str:
        candidate = str(configuration.get("base_url", "https://api.github.com")).rstrip("/")
        parsed = urlparse(candidate)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise ConnectorAdapterError("GitHub base_url must be an absolute HTTP(S) URL")
        return candidate

    @staticmethod
    def _headers(credential: str) -> dict[str, str]:
        if not credential:
            raise ConnectorAdapterError("A GitHub token is required before this connector can be tested or used")
        return {
            "Authorization": f"Bearer {credential}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        }

    async def _request(self, method: str, path: str, credential: str, configuration: dict[str, Any], *, payload: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> Any:
        response: httpx.Response | None = None
        async with httpx.AsyncClient(base_url=self._base_url(configuration), headers=self._headers(credential), timeout=httpx.Timeout(12.0, connect=5.0), transport=self.transport) as client:
            for attempt in range(3):
                try:
                    response = await client.request(method, path, json=payload, params=params)
                except httpx.TimeoutException as exc:
                    if attempt == 2:
                        raise ConnectorAdapterError("GitHub did not respond in time. Check connectivity and retry the operation.") from exc
                except httpx.HTTPError as exc:
                    if attempt == 2:
                        raise ConnectorAdapterError("GitHub could not be reached from this installation. Check connectivity and retry.") from exc
                else:
                    if response.status_code not in {429, 502, 503, 504} or attempt == 2:
                        break
                await asyncio.sleep(0.25 * (2 ** attempt))
        if response is None:
            raise ConnectorAdapterError("GitHub request could not be completed. Retry the operation.")
        if response.status_code == 429:
            raise ConnectorAdapterError("GitHub is rate limiting this connector. Wait briefly, then retry.")
        if response.status_code in {401, 403, 404}:
            raise ConnectorAdapterError("GitHub rejected this request; verify the token permissions and repository access")
        if response.status_code >= 400:
            message = response.json().get("message") if response.headers.get("content-type", "").startswith("application/json") else response.text
            raise ConnectorAdapterError(f"GitHub request failed ({response.status_code}): {str(message)[:180]}")
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    async def test(self, credential: str, configuration: dict[str, Any]) -> AdapterResult:
        profile = await self._request("GET", "/user", credential, configuration)
        return AdapterResult("GitHub authenticated successfully", {"login": profile.get("login"), "name": profile.get("name"), "scopes": []})

    async def execute(self, action: str, input_data: dict[str, Any], credential: str, configuration: dict[str, Any]) -> AdapterResult:
        if action == "list_repositories":
            data = await self._request("GET", "/user/repos", credential, configuration, params={"per_page": min(int(input_data.get("per_page", 30)), 100), "sort": input_data.get("sort", "updated")})
            repositories = [{"id": item.get("id"), "full_name": item.get("full_name"), "private": item.get("private"), "default_branch": item.get("default_branch")} for item in data]
            return AdapterResult("Repositories loaded", {"repositories": repositories})
        if action == "get_repository":
            owner, repo = _require(input_data, "owner", "repo")
            data = await self._request("GET", f"/repos/{owner}/{repo}", credential, configuration)
            return AdapterResult("Repository loaded", {"repository": data})
        owner, repo = _require(input_data, "owner", "repo")
        if action == "create_issue":
            title, = _require(input_data, "title")
            data = await self._request("POST", f"/repos/{owner}/{repo}/issues", credential, configuration, payload={"title": title, "body": input_data.get("body", ""), "labels": input_data.get("labels", [])})
        elif action == "create_pull_request":
            title, head, base = _require(input_data, "title", "head", "base")
            data = await self._request("POST", f"/repos/{owner}/{repo}/pulls", credential, configuration, payload={"title": title, "head": head, "base": base, "body": input_data.get("body", ""), "draft": bool(input_data.get("draft", False))})
        elif action == "create_release":
            tag_name, = _require(input_data, "tag_name")
            data = await self._request("POST", f"/repos/{owner}/{repo}/releases", credential, configuration, payload={"tag_name": tag_name, "target_commitish": input_data.get("target_commitish"), "name": input_data.get("name"), "body": input_data.get("body", ""), "draft": bool(input_data.get("draft", False)), "prerelease": bool(input_data.get("prerelease", False)), "generate_release_notes": bool(input_data.get("generate_release_notes", False))})
        elif action == "dispatch_workflow":
            workflow_id, ref = _require(input_data, "workflow_id", "ref")
            data = await self._request("POST", f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches", credential, configuration, payload={"ref": ref, "inputs": input_data.get("inputs", {})})
        elif action == "create_or_update_file":
            path, message, content = _require(input_data, "path", "message", "content")
            encoded = base64.b64encode(str(content).encode()).decode()
            payload = {"message": message, "content": encoded, "branch": input_data.get("branch")}
            if input_data.get("sha"):
                payload["sha"] = input_data["sha"]
            data = await self._request("PUT", f"/repos/{owner}/{repo}/contents/{path}", credential, configuration, payload=payload)
        else:
            raise ConnectorAdapterError(f"Unsupported GitHub action: {action}")
        return AdapterResult(f"GitHub action '{action}' completed", {"result": data})


class RevitMockAdapter:
    """Deterministic local model used until a signed Revit bridge is installed."""

    provider = "revit"
    capabilities = ["model.read", "parameter.write", "family_instance.place", "transaction.preview", "transaction.apply"]

    def __init__(self) -> None:
        self.elements: dict[int, dict[str, Any]] = {
            101: {"id": 101, "category": "Walls", "name": "Exterior wall", "parameters": {"Mark": "W-101", "Comments": ""}},
            202: {"id": 202, "category": "Doors", "name": "Lobby door", "parameters": {"Mark": "D-202", "Comments": ""}},
        }

    async def test(self, credential: str | None, configuration: dict[str, Any]) -> AdapterResult:
        return AdapterResult("Revit mock model is ready", {"mode": "mock", "element_count": len(self.elements), "bridge_required_for_live": True})

    async def preview(self, operation: str, payload: dict[str, Any]) -> AdapterResult:
        if operation == "set_parameter":
            data = payload["set_parameter"]
            element_id = int(data["element_id"])
            if element_id not in self.elements:
                raise ConnectorAdapterError(f"Element {element_id} does not exist in the active mock model")
            element = self.elements[element_id]
            return AdapterResult("Parameter change planned", {"transaction": payload["transaction_name"], "mode": "mock", "operation": operation, "element": {"id": element_id, "name": element["name"], "category": element["category"]}, "parameter": data["parameter"], "before": element["parameters"].get(data["parameter"]), "after": data["value"]})
        if operation == "place_family_instance":
            data = payload["place_family_instance"]
            return AdapterResult("Family placement planned", {"transaction": payload["transaction_name"], "mode": "mock", "operation": operation, "family_symbol": data["family_symbol"], "level": data["level"], "point": {"x": data["x"], "y": data["y"], "z": data["z"]}, "parameters": data.get("parameters", {})})
        raise ConnectorAdapterError(f"Unsupported Revit operation: {operation}")

    async def apply(self, operation: str, payload: dict[str, Any]) -> AdapterResult:
        preview = await self.preview(operation, payload)
        if operation == "set_parameter":
            data = payload["set_parameter"]
            element = self.elements[int(data["element_id"])]
            element["parameters"][data["parameter"]] = data["value"]
            return AdapterResult("Parameter updated in the mock model", {**preview.data, "element": element})
        data = payload["place_family_instance"]
        element_id = max(self.elements) + 1
        element = {"id": element_id, "category": "Generic Models", "name": data["family_symbol"], "level": data["level"], "point": {"x": data["x"], "y": data["y"], "z": data["z"]}, "parameters": data.get("parameters", {})}
        self.elements[element_id] = element
        return AdapterResult("Family instance placed in the mock model", {**preview.data, "element": element})
