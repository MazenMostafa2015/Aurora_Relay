# Aurora Relay v0.8.20: Session Architecture and Offline Renderer Hardening

**Release intent.** This corrective release separates durable authentication state from workspace state, routes visible renderer actions through typed command boundaries, and removes legacy remote renderer assets. The objective is to make the desktop renderer easier to audit while preserving its local-first operation and the existing Aurora Relay dark editorial interface.

## Architecture changes

| Area | v0.8.19 behavior | v0.8.20 behavior |
|---|---|---|
| Authentication | Session identity, token hydration, dialog state, and workspace UI state shared one Zustand store. | `sessionStore.ts` owns `anonymous`, `authenticating`, `authenticated`, and `error` state plus all session lifecycle actions. |
| Workspace state | Task, tool, event, navigation, and authentication actions were co-located. | `appStore.ts` owns only task, tool, event, view, draft, and submission lifecycle state. |
| Renderer actions | UI components could call store actions directly. | `commands.ts` exposes typed authentication, task, and navigation commands that validate inputs, map failures, and provide user feedback. |
| Offline assets | Renderer source referenced six legacy `/manus-storage/` resources. | CSS-native gradients, a CSS-drawn brand sigil, and an inline data-URI favicon are bundled without hosted asset dependencies. |

The session slice owns local token persistence and account lifecycle behavior. It deliberately does not own task history, navigation, tool discovery, or streaming signals. The feature store retains those workspace responsibilities and exposes narrowly scoped mutation functions used by the command layer.

> Commands are the renderer’s control boundary: visible controls validate intent, invoke the correct store or API operation, convert failures to a typed result, and present a consistent feedback message.

## Renderer controls migrated

| Command hook | Covered behavior |
|---|---|
| `useAuthCommands()` | Session hydration, sign-in, registration, sign-out, and dialog visibility. |
| `useTaskCommands()` | Draft validation, authenticated task submission, task normalization, submission state, and API-error feedback. |
| `useNavigationCommands()` | View selection, task detail selection, and account/settings access. |

The sidebar, header, composer, active task panel, history, settings controls, and authentication dialog are now command clients. The existing stream hook continues to consume only workspace task state, avoiding a hidden dependency on the session store.

## Offline boundary changes

Six legacy `/manus-storage/` references were removed from the favicon, sidebar texture, composer artwork, micro-stat texture, settings-note artwork, and brand mark. The unused template map loader was also deleted because it contained an executable external fallback endpoint that was not part of Aurora Relay’s local renderer.

The release now includes `pnpm check:offline`, a deterministic source-and-bundle guard that rejects legacy storage paths, template Forge endpoints, and Umami or remote analytics patterns. Browser coverage independently asserts that dashboard startup makes no requests beyond the local test origin.

## Validation evidence

| Validation | Result |
|---|---|
| `pnpm validate` | Passed: TypeScript check, Vite production build, and offline renderer guard. |
| `npx playwright test e2e/interaction.spec.ts` | Passed: 6 browser interaction and local-network tests. |
| `pytest -q` in `backend/` | Passed: 30 tests. |
| Legacy asset scan | Passed: no `/manus-storage/` references in renderer source or production bundle. |
| Release diff hygiene | Passed: `git diff --check` reported no whitespace errors before commit. |

The Vite build retains its existing advisory about a JavaScript chunk exceeding 500 kB after minification. This is a performance-follow-up item rather than a release blocker: the production build succeeds, and no remote asset or telemetry dependency is introduced by the renderer changes.

## Remaining release gates

The protected Windows workflow completed successfully for the immutable `v0.8.20` tag. Its source revision is `9aa859c3994f1061fff8b8028a09b913f9fdca4e`, and release workflow run `32159539046` published the installer, SHA-256 manifest, provenance record, and clean-machine evidence.

| Published check | Verified evidence |
|---|---|
| Installer identity | `Aurora-Relay-0.8.20-win-x64.exe` |
| SHA-256 | `234bb11b60b5f38dbdc4bc0b78102ba846a05ecee67348e81960dd7aaf951071` in both `SHA256SUMS` and provenance. |
| Signer pin | `223DEC322FF229C490C144320FB6B51EC23A6C2F` matched the protected expected internal certificate. |
| Timestamp | The clean-machine evidence confirms a timestamp certificate is present. |
| Installation path | Silent install succeeded, the app was present, its backend reached loopback health `200`, and silent uninstall removed the application while preserving user state. |

The raw Windows Authenticode status in the evidence is `UnknownError`. This is expected for the private self-signed certificate outside a machine-wide trust store; the verifier additionally validates the exact pinned signer certificate through a custom trust chain and rejects any unexpected signer. Users should install the corresponding public internal certificate through their organization’s approved trust-distribution process if they require Windows to display the publisher as trusted.
