# Generated extension reference

> This file is generated from checked-in local manifests by `python scripts/generate_docs.py`. It never reads remote package catalogs.

| Identifier | Name | Version | Kind | Declared permissions | Connector | Purpose |
| --- | --- | --- | --- | --- | --- | --- |
| `aurora.connector.github` | GitHub Connector Adapter | 1.0.0 | connector_adapter | connector.read | github | A built-in compatibility adapter that routes GitHub operations through the existing authenticated connector controls. |
| `aurora.connector.revit` | Revit Connector Adapter | 1.0.0 | connector_adapter | connector.read | revit | A built-in compatibility adapter that routes Revit preview and apply operations through the guarded local connector workflow. |
| `aurora.sandbox-echo` | Sandbox Echo | 1.0.0 | sandboxed_tool | sandbox.execute | — | A reviewed local sample that proves extension code runs only inside the Docker sandbox. |

## Execution boundary

Reviewed manifests do not grant host-process access. Sandboxed tool execution remains Docker-only and fails closed when the sandbox is unavailable.
