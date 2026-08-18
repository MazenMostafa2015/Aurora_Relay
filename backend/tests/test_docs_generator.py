from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
GENERATOR_PATH = REPOSITORY_ROOT / "scripts" / "generate_docs.py"


def load_generator_module():
    specification = importlib.util.spec_from_file_location("generate_docs", GENERATOR_PATH)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def test_generator_includes_documented_symbols_and_reviewed_manifest(tmp_path: Path):
    generator = load_generator_module()
    source_root = tmp_path / "source"
    manifest_root = tmp_path / "manifests"
    output_root = tmp_path / "generated"
    source_root.mkdir()
    manifest_root.mkdir()
    (source_root / "module.py").write_text(
        '''"""Stable module guidance."""\n\ndef public_action():\n    """Perform a reviewed action."""\n\nclass OperatorView:\n    """Expose an operator-safe state."""\n\n    def refresh(self):\n        """Refresh without external side effects."""\n''',
        encoding="utf-8",
    )
    (manifest_root / "example.json").write_text(
        '{"id":"aurora.example","display_name":"Example","version":"1.0.0","kind":"sandboxed_tool","permissions":["sandbox.execute"],"description":"A local example."}',
        encoding="utf-8",
    )

    documents = generator.generated_documents(source_root, manifest_root)
    assert "`module.public_action`" in documents[Path("backend-reference.md")]
    assert "`module.OperatorView.refresh`" in documents[Path("backend-reference.md")]
    assert "`aurora.example`" in documents[Path("extensions-reference.md")]
    assert generator.apply_documents(documents, output_root, check=False) == 0
    assert generator.apply_documents(documents, output_root, check=True) == 0

    (source_root / "module.py").write_text('def public_action():\n    """Changed documentation."""\n', encoding="utf-8")
    assert generator.apply_documents(generator.generated_documents(source_root, manifest_root), output_root, check=True) == 1
