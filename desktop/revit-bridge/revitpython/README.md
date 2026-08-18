# RevitPythonShell adapter

`AuroraRelayCommands.py` is the direct Revit API implementation for the two operations that Aurora Relay exposes: setting an existing writable element parameter and placing a point-based family instance. It intentionally exposes no generic `exec`, macro, path, or document-save command.

The installed bridge host should deserialize only a FastAPI-confirmed operation, invoke one of these two functions with typed fields, and return a structured result. Test with a non-production Revit model first. The current automated suite continues to exercise the equivalent deterministic mock adapter because Revit and RevitPythonShell are unavailable in CI.
