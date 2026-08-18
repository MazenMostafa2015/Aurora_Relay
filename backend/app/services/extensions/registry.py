"""Strict discovery of checked-in local extension manifests and entrypoints."""
from __future__ import annotations

import json
from pathlib import Path

from ...api.models import ExtensionManifest


class ExtensionRegistryError(RuntimeError):
    pass


class ExtensionRegistry:
    """Loads only local JSON manifests stored under a controlled directory."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root).resolve() if root else Path(__file__).resolve().parents[3] / "extensions"
        self.manifest_dir = self.root / "manifests"
        self.entrypoint_dir = self.root / "entries"

    def catalog(self) -> dict[str, ExtensionManifest]:
        if not self.manifest_dir.exists():
            return {}
        discovered: dict[str, ExtensionManifest] = {}
        for manifest_path in sorted(self.manifest_dir.glob("*.json")):
            try:
                manifest = ExtensionManifest.model_validate(json.loads(manifest_path.read_text(encoding="utf-8")))
            except Exception as exc:  # validation details are intentionally not rendered to end users
                raise ExtensionRegistryError(f"Invalid local extension manifest: {manifest_path.name}") from exc
            if manifest.id in discovered:
                raise ExtensionRegistryError(f"Duplicate local extension id: {manifest.id}")
            if manifest.kind.value == "sandboxed_tool" and not manifest.entrypoint:
                raise ExtensionRegistryError(f"Sandboxed extension {manifest.id} requires an entrypoint")
            discovered[manifest.id] = manifest
        return discovered

    def manifest(self, extension_id: str) -> ExtensionManifest:
        manifest = self.catalog().get(extension_id)
        if manifest is None:
            raise ExtensionRegistryError("Extension is not available in the local registry")
        return manifest

    def entrypoint_path(self, manifest: ExtensionManifest) -> Path:
        if not manifest.entrypoint:
            raise ExtensionRegistryError("This extension does not declare an executable entrypoint")
        root = self.entrypoint_dir.resolve()
        entrypoint = (root / manifest.entrypoint).resolve()
        if root not in entrypoint.parents or not entrypoint.is_file():
            raise ExtensionRegistryError("Extension entrypoint is not available in the local registry")
        return entrypoint
