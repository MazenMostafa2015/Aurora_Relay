# Aurora Relay Connector Management and Revit Bridge

## Scope

Aurora Relay now provides a local-first connector command center for GitHub and Revit. Connector metadata is user-scoped and visible in the renderer; provider credentials are kept outside renderer state and are never returned by the API. GitHub actions run through an allow-listed backend adapter. Revit editing uses a plan, inspection, explicit confirmation, and apply sequence.

| Capability | Delivered behavior | Live dependency |
| --- | --- | --- |
| GitHub | Configurable API base URL, encrypted personal-access-token vault entry, connection testing, repository/issue/PR/release/workflow/commit/content action boundary | A token with the provider permissions needed for the selected action. |
| Revit mock | Deterministic element parameter preview, rejected invalid confirmation, user-scoped operation ID, exactly-once apply, and audit records | None. This is the default and is covered by automated tests. |
| Revit live bridge | Localhost contract, UI-thread transaction, allow-listed parameter update and family placement | An installed Revit add-in or RevitPythonShell bridge, plus local bridge enablement. It was not live-tested in CI. |
| Windows Commander / browser extension | Opens an authenticated local desktop action surface without carrying credential material | A separately installed launcher/native-messaging host. |

## Operator setup

Sign into the local Aurora Relay dashboard, then open **Connectors**. Use **Add a connector** to select GitHub or Revit. A GitHub personal access token is present only in the password input while the form is submitted; it is encrypted by the local vault before persistence. The dashboard returns only whether a vault reference is configured. Use the Test action to verify the configured endpoint and token before issuing provider actions.

The vault uses `AURORA_CONNECTOR_VAULT_KEY` when the desktop launcher supplies an OS-managed per-install secret. In local development, it uses `AURORA_CONNECTOR_VAULT_PATH` or a guarded user-owned key file at `$AURORA_APP_DATA_DIR/connector-vault.key`. On non-Windows platforms the fallback file is created with mode `0600`. Do not commit either value, copy the key file between users, or provide vault keys to the renderer, extension, or model bridge.

GitHub defaults to `https://api.github.com`; enter an approved GitHub Enterprise API URL only when required. Every provider action is checked against the backend allow-list and its typed parameters. The dashboard currently exposes issue creation as a deliberate human-operated action; other approved GitHub actions are available through the backend/MCP connector command surface.

## Revit model editing

Revit starts in **mock** mode. A user enters an element ID, an allow-listed parameter name, and a new value, then selects **Preview change**. The backend creates a durable operation ID and returns the target, transaction name, before/after data, and adapter mode. Nothing is changed while the operation is planned.

> Only the exact uppercase confirmation `APPLY`, presented for the same authenticated user and connector, can resolve the planned operation. A rejected, applied, expired, or cross-user operation cannot be applied again.

For a live Revit installation, follow `desktop/revit-bridge/README.md`. The bridge is localhost-only and must receive an already-confirmed operation ID plus a per-install bridge secret. It must perform the approved operation on Revit’s UI thread within a transaction. Set `REVIT_LIVE_BRIDGE_ENABLED=true` only after the organization has installed the signed bridge, distributed its trust material, verified firewall policy, and reviewed the specific Revit version compatibility. Do not expose a Revit endpoint to a LAN or the internet.

## MCP and extension deployment

The `connector_management` MCP server is configured alongside Aurora Relay’s existing MCP servers. It refuses all tool calls until the authenticated desktop launcher binds `AURORA_MCP_USER_ID` to one active local user. It lists only that user’s connector metadata, calls adapters through the same vault service, and preserves Revit’s plan-confirm-apply gate.

Windows Commander should call the validated `aurora-relay://connectors/{connectorId}/actions/{action}` deep link. A browser extension should use native messaging to open the desktop action surface or display redacted status. Neither integration may transmit GitHub credentials, arbitrary command strings, or Revit paths. See `docs/connector_extension_contracts.md` for the narrow launcher contracts.

## Troubleshooting

| Symptom | Safe response |
| --- | --- |
| GitHub test reports authorization failure | Verify token scope and expiry in GitHub, replace the connector credential through the dashboard, and retest. Do not paste the token into logs or issue reports. |
| Connector needs attention | Read the redacted test result, verify the endpoint and non-secret configuration, then rerun Test. Disable the connector if it should not be callable. |
| Revit preview works but Apply fails | Confirm the literal `APPLY` input, operation ownership, and operation state. For bridge mode, verify the local add-in/bridge is running and matches the configured install. |
| Vault cannot be read after a move or restore | Restore the matching per-install secret through the approved device recovery process; ciphertext cannot be decrypted with a different vault key. |
| MCP server rejects an action | Start the MCP process from the authenticated Aurora Relay desktop launcher. Do not set a user ID manually in a shared or remote service context. |

## Validation boundary

Automated coverage verifies encrypted credential redaction, mocked GitHub issue dispatch, user-scoped ordering, Revit no-mutation-before-confirmation behavior, cross-user rejection, exactly-once apply, local-only startup network behavior, and the renderer confirmation UI. The sandbox has no reachable pyRevit/installed Revit bridge, so no live BIM model was opened or modified during this release.

## Release evidence

The immutable `v0.8.21` release was built from revision `0671b0c9f19b1e854e75c3d18a4b0b2541c226c6` by protected Windows workflow run `32164353918`. The published `Aurora-Relay-0.8.21-win-x64.exe` has SHA-256 `d0444bca8135903e5dcff5cdb1039b7b8bbe6fa170428d89e50b701b5b96d640`, which is identical in the release checksum and provenance files.

The clean-machine record passed silent install, local backend health check (`200` on loopback), silent uninstall, and retained-user-state checks. It matched the pinned internal signer thumbprint `223DEC322FF229C490C144320FB6B51EC23A6C2F` and includes a timestamp certificate. The raw Authenticode status is `UnknownError`, which is expected on a clean runner that does not trust the private self-signed issuing certificate. The protected verifier additionally validates the exact signer with its configured custom trust chain; distribute the approved internal public certificate through organizational device management if Windows publisher trust UI is required.
