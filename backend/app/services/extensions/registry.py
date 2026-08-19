"""Verified local extension package discovery; raw manifests are never executable."""
from __future__ import annotations

from pathlib import Path

from .signing import ExtensionPackageVerifier, PackageVerificationError, VerifiedExtensionPackage


class ExtensionRegistryError(RuntimeError):
    def __init__(self, message: str, *, code: str = "registry_invalid") -> None:
        super().__init__(message)
        self.code = code


class ExtensionRegistry:
    """Loads only locally stored, successfully verified `.aurx` archives."""

    def __init__(self, root: str | Path | None = None, *, trust_dir: str | Path | None = None) -> None:
        self.root = Path(root).resolve() if root else Path(__file__).resolve().parents[3] / "extensions"
        self.package_dir = self.root / "packages"
        self.trust_dir = Path(trust_dir).resolve() if trust_dir else self.root / "trust"
        self.verifier = ExtensionPackageVerifier(self.trust_dir)

    def catalog(self) -> dict[str, VerifiedExtensionPackage]:
        if not self.package_dir.exists():
            return {}
        discovered: dict[str, VerifiedExtensionPackage] = {}
        for package_path in sorted(self.package_dir.glob("*.aurx")):
            try:
                verified = self.verifier.verify(package_path)
            except PackageVerificationError as exc:
                raise ExtensionRegistryError(str(exc), code=exc.code) from exc
            if verified.manifest.id in discovered:
                raise ExtensionRegistryError("Duplicate verified extension id", code="duplicate_extension")
            discovered[verified.manifest.id] = verified
        return discovered

    def package(self, extension_id: str) -> VerifiedExtensionPackage:
        package = self.catalog().get(extension_id)
        if package is None:
            raise ExtensionRegistryError("Extension is not available in the verified local registry", code="package_unavailable")
        return package
