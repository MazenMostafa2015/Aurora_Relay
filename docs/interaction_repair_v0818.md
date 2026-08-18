# Aurora Relay Interaction Repair — v0.8.18

**Author:** Manus AI  
**Status:** Implemented and validated  
**Scope:** Desktop renderer authentication, navigation, task submission, visible controls, and browser interaction coverage.

## Executive summary

The unresponsive-controls report was caused by a disconnected renderer interaction layer rather than one faulty button. The dashboard rendered navigation, authentication, task, and settings affordances, but the authentication dialog was not mounted in the application shell, the Zustand store did not expose API-backed sign-in, sign-out, or task actions, and several visible controls had no meaningful callback. The renderer now connects those controls to typed Zustand actions and the existing local FastAPI contract.

The repair preserves the desktop product’s **local-only** session boundary. Credentials are submitted only to the configured local API base URL, the returned bearer token is retained in `localStorage` as `aurora-token`, and it is cleared during sign-out even if the server-side logout request is unavailable. The test suite exercises the user-visible flows against mocked local API responses and separately confirms that the real backend authentication and task route contract still passes.

## Changes applied

| Area | Previous behavior | Repair | Primary files |
|---|---|---|---|
| Authentication shell | A sign-in dialog existed but was not rendered by the dashboard page. | The dialog is mounted in `Home`, receives typed store callbacks, displays API failures, supports registration, and now has an explicit **Cancel** action. | `frontend/client/src/pages/Home.tsx`; `frontend/client/src/components/ManusDialog.tsx` |
| Authentication state | No typed actions connected UI controls to `/auth/login`, `/auth/register`, `/auth/me`, or `/auth/logout`. | Added local token hydration, login, registration, sign-out, loading, error, and dialog actions to the Zustand store. | `frontend/client/src/store/appStore.ts`; `frontend/client/src/lib/api.ts`; `frontend/client/src/types/app.ts` |
| Task submission | The composer could update local state without submitting a task to the service. | The composer now calls `POST /api/v1/tasks`, maps the response into the task state, selects the new task, and shows success or failure feedback. | `frontend/client/src/store/appStore.ts`; `frontend/client/src/pages/Home.tsx`; `backend/app/api/routes/tasks.py` |
| Navigation and visible controls | Several header, sidebar, history, settings, attachment, and mobile actions lacked a state transition or feedback. | Navigation calls `setView`; secondary actions select views/tasks or emit explicit local feedback; attachment selection updates the composer; the mobile toggle updates sidebar state. | `frontend/client/src/pages/Home.tsx` |
| Build integrity | Duplicate imports in the application shell and sign-in dialog blocked the renderer type check. | Removed duplicate imports and used a type-only React `FormEvent` import. | `frontend/client/src/App.tsx`; `frontend/client/src/components/ManusDialog.tsx` |
| Regression coverage | The repository did not include a project-owned interaction suite for these flows. | Added a Playwright configuration and five browser tests with deterministic local API mocks. | `frontend/playwright.config.ts`; `frontend/e2e/interaction.spec.ts` |

## Interaction inventory and validation

The Playwright suite now covers the repaired public interaction inventory. It validates that sign-in persists a local bearer token, `/auth/me` receives the authorization header, and sign-out restores the signed-out UI. It also verifies account creation, dashboard navigation, header tool explorer and help controls, pinned task controls, attachment selection, task submission, task detail and history controls, settings/profile dialog dismissal, informational settings actions, and the responsive mobile navigation toggle.

| Validation activity | Result | Evidence |
|---|---:|---|
| Browser interaction inventory | **5 passed** | `pnpm test:e2e -- --reporter=line` |
| TypeScript validation | **Passed** | `pnpm check` |
| Frontend production build | **Passed** | `pnpm build` |
| Backend authentication/task API contract | **3 passed** | `pytest -q tests/test_api/test_api.py` |
| Diff whitespace validation | **Passed** | `git diff --check` |

> The browser suite routes requests only under `/api/v1/**` and supplies local deterministic responses. It exercises renderer behavior without contacting a remote identity or analytics service.

## Functional behavior after the repair

The sign-in button opens the credential dialog. A successful sign-in stores the returned token locally, retrieves the current user through `/auth/me`, closes the dialog, and renders the authenticated dashboard. Registration creates a local account and then signs in through the same session flow. Sign-out calls the local logout endpoint when available, clears the persisted token in all cases, and restores the guest interface.

The task composer requires a non-empty direction. It submits the direction and optional attachment name to the existing task endpoint, inserts the returned task into the store, makes that task active, and opens the Task desk. Navigation and detail controls now use typed `ViewKey` and task-selection state rather than relying on inert visual affordances.

## Remaining limits

The **Default model**, **Approval mode**, and **Theme** setting rows currently provide transparent informational feedback rather than editable persistent preferences. This is intentional in the repair: pretending that those selections changed a runtime configuration would be misleading. Turning them into real settings requires backend configuration endpoints, validation rules, persistence, and first-run policy handling.

The production build still reports unresolved legacy `/manus-storage/` image references. They do not prevent the interaction build or the new tests from passing, but they should be replaced by packaged local assets or CSS artwork before treating the desktop distribution as strictly self-contained. The build also reports a JavaScript bundle above the default size threshold; this is a performance concern, not an interaction failure.

## Recommended architecture improvements

| Priority | Recommendation | Rationale |
|---|---|---|
| High | Create a dedicated `authStore` or `authSlice` with a discriminated session state: `checking`, `anonymous`, `authenticated`, and `error`. | It makes route guards, loading UI, token expiry, and error recovery explicit instead of distributing them across page-level effects. |
| High | Introduce a renderer command layer, such as `commands.signIn`, `commands.submitTask`, and `commands.openView`, between components and the Zustand store. | Components stay declarative, all side effects share one error/telemetry-free policy, and each command can be tested independently. |
| High | Keep the local API contract generated or shared from backend schemas. | Typed request and response models will prevent silent drift between FastAPI routes and renderer assumptions as authentication and task fields evolve. |
| Medium | Add stable `data-testid` attributes only to complex controls whose accessible names intentionally overlap. | Accessibility-first role/name queries should remain the default; stable IDs prevent future test fragility around repeated task titles and header/sidebar actions. |
| Medium | Implement real persisted preferences only after defining backend policy ownership. | Model, approval, and theme controls should save through a typed endpoint and receive confirmed runtime state rather than relying on informational toasts. |
| Medium | Split the renderer bundle by view and remove legacy external asset references. | Dynamic view imports reduce the first render payload, while local assets maintain the intended no-telemetry, local-only packaging boundary. |

## Maintainer checklist

Before merging subsequent renderer changes, run the following commands from `frontend/`:

```bash
pnpm check
pnpm build
pnpm test:e2e -- --reporter=line
```

Run the backend route contract check from the repository root:

```bash
pytest -q tests/test_api/test_api.py
```

For any new visible button, require a deliberate command, navigation transition, state mutation, or explicit informational response. A button that only renders visual affordance without one of those outcomes should be treated as incomplete.
