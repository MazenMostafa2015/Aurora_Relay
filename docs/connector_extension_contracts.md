# Aurora Relay desktop extension contracts

## Windows Commander surface

Windows Commander integrations should invoke the local authenticated Aurora Relay deep link `aurora-relay://connectors/{connectorId}/actions/{action}`. The Electron main process validates the connector/action allow-list and forwards only a structured action request to the local backend. It must never pass a raw command line, secret, or Revit model path from the external caller into a provider adapter.

## Browser/Chrome surface

The optional browser extension should use native messaging to call the installed Electron host and request a pre-authorized GitHub or page-context action. The extension may display connector status and open the local dashboard, but must not store GitHub tokens. Credentials remain in the desktop credential vault and provider actions require the backend’s authenticated connector endpoint.

## Revit bridge surface

The Revit bridge listens only on `127.0.0.1` and accepts no mutation unless it carries a per-install secret from the OS credential store and an already-confirmed Aurora Relay operation ID. Its endpoint is intentionally separate from the renderer and external browser surfaces.
