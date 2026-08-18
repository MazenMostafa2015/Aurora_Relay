# Deterministic documentation automation

Aurora Relay generates developer and extension references entirely from **local reviewed source**. The generator reads Python module, class, and function docstrings through the standard-library AST, then reads checked-in JSON manifests from `backend/extensions/manifests/`. It does not call an LLM, download a package catalog, access credentials, or execute extension entrypoints.

| Input | Generated reference | Purpose |
| --- | --- | --- |
| Public Python docstrings under `backend/app/` | `docs/generated/backend-reference.md` | Keeps the backend API and service reference aligned with source comments. |
| Checked-in extension manifests | `docs/generated/extensions-reference.md` | Lists reviewed extension identity, permissions, kind, connector metadata, and declared purpose. |

Run the generator from the repository root whenever a public docstring or reviewed extension manifest changes.

```bash
python scripts/generate_docs.py
python scripts/generate_docs.py --check
```

The normal command updates the checked-in Markdown artifacts. The `--check` command exits non-zero when source and generated documents differ, which makes documentation freshness enforceable in continuous integration. Generated references are reviewed source artifacts; do not hand-edit them.

| Change type | Required action |
| --- | --- |
| Public backend class or function | Update its docstring, run the generator, and review `backend-reference.md`. |
| Local extension manifest | Update the manifest, run the generator, and review `extensions-reference.md`. |
| Extension entrypoint or external execution policy | Update the manually maintained operational documentation as well; the generator intentionally records only static manifest metadata. |

The generator deliberately omits private symbols, runtime local state, encrypted vault content, connector credential records, and executable extension source. This preserves the local-first, fail-closed trust boundary while still producing a repeatable reference for reviewed interfaces.
