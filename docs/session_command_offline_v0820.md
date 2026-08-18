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

The protected Windows workflow remains the source of record for native signing, checksum generation, provenance manifest publication, and clean-machine installer verification. The v0.8.20 tag must be pushed without changing any previous immutable release tag; the installer evidence must be reviewed before this corrective release is presented as a completed signed desktop package.
