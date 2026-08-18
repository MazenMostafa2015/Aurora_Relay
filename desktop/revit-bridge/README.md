# Aurora Relay Revit Bridge

This source defines a **loopback-only Revit API bridge** for environments that install a signed Aurora Relay Revit add-in. It runs model mutations through Revit’s `ExternalEvent` handler on the Revit UI thread and permits only the FastAPI-approved operation contract: parameter assignment and family-instance placement.

The current application release uses the deterministic Revit mock adapter by default. A live bridge is an enterprise deployment step because Autodesk Revit SDK assemblies are version-specific and may not be redistributed in this repository. Before enabling a live bridge, administrators must compile the add-in against their deployed Revit version, distribute the `.addin` manifest through the approved add-in directory, provision a per-install loopback bearer token in an OS-backed secret store, and enable `revit_live_bridge_enabled` only after a local health check succeeds.

The bridge **must not** accept arbitrary Revit macros, executable code, paths, or model operations. Aurora Relay’s API first persists a preview, then requires the literal `APPLY` confirmation, and the bridge should additionally validate the signed operation ID and request hash before opening a Revit transaction.
