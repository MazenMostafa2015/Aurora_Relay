# Aurora Relay repository-backed agent loop

## Operating model

Aurora Relay’s agent loop is a **bounded Think → Act → Reflect workflow**, not an unattended deployment system. It is configured for five UTC schedule slots daily (`08:00`, `11:00`, `14:00`, `17:00`, and `20:00`) and must expire after a seven-day window. The GitHub Actions job is **disabled by default**; scheduled invocations run only when the repository variable `AGENT_LOOP_SCHEDULE_ENABLED` is exactly `true`.

The loop runs in dry-run mode. Its repository worker may inspect checkout status, compile `backend/app`, type-check the renderer, and write a plan plus report under `reports/agent-loop/`. It cannot modify source files, merge, deploy, release, delete, or perform provider/network mutations. The workflow can create one isolated `aurora-agent/loop/*` branch containing only those evidence files when `AGENT_LOOP_PUSH_REVIEW_BRANCH=true`. It never opens or merges a pull request.

## Required operator configuration

Before enabling the scheduled workflow, create the following **repository variables**. Do not place credentials, JWTs, provider tokens, or Revit bridge details in these values.

| Variable | Required value | Purpose |
| --- | --- | --- |
| `AGENT_LOOP_SCHEDULE_ENABLED` | `true` only after review | Enables scheduled runs; omitting it or any other value keeps scheduled jobs skipped. |
| `AGENT_LOOP_EXPIRES_AT` | ISO-8601 UTC timestamp | The hard expiry. Set it no later than seven days after enablement. |
| `AGENT_LOOP_PUSH_REVIEW_BRANCH` | `true` or `false` | Allows evidence-only review branch pushes after a successful run. |

Use **Run workflow** for a one-off reviewed execution. Supply an explicit ISO-8601 UTC expiry and choose whether to push an evidence-only branch. The job has a 20-minute timeout, serializes concurrent runs, and exits safely after three consecutive prior failures.

> Never enable the schedule until the expiry timestamp, current Actions usage, branch-protection policy, and review-branch policy have been reviewed by an operator.

## Dashboard and API controls

The **Agent Loop** dashboard is available to authenticated users. It exposes the persisted configuration, dry-run status, action cap, iteration/report history, and explicit lifecycle actions. Defaults are safe: dry run enabled, maximum eight actions per iteration, three consecutive failures stop subsequent work, and release/deployment approval disabled.

Use **Hard stop** only after typing the required confirmation. It immediately marks the user-scoped loop stopped; it does not cancel an already-running GitHub-hosted job. Disable `AGENT_LOOP_SCHEDULE_ENABLED` as the repository-side stop control, then review the latest workflow run and evidence branch.

## Approval boundaries

| Operation | Default | Approval rule |
| --- | --- | --- |
| Inspect repository and run allow-listed checks | Allowed | Dry-run only; eight-action ceiling. |
| Write local plan/report files | Allowed | Controlled `reports/agent-loop/` path only. |
| Push evidence-only review branch | Disabled | Explicit repository variable or manual workflow input. |
| Create implementation commits, merge, deploy, release, delete, or alter infrastructure | Blocked | Not implemented by this workflow; requires a separate operator-approved process. |
| Invoke GitHub provider mutation, Revit bridge, browser automation, or other connector action | Blocked | Must be planned and explicitly approved through the corresponding authenticated connector flow. |

## GitHub Actions budget boundary

GitHub Free includes 2,000 GitHub-hosted Actions minutes per month for private repositories, subject to GitHub’s current plan and billing policy. Thirty-five scheduled runs leave an average budget of roughly 57 minutes per run if no other Actions usage is counted. This workflow caps each job at 20 minutes, but the repository owner must check the current Actions usage page before enabling it because existing workflows share the quota. GitHub billing configuration can cause overage charges after included usage is exhausted.[^github-actions]

## Revit and connector boundary

The repository worker has no access to a local Revit model or desktop bridge. Keep Revit operation planning and the installed bridge’s plan → inspect → literal confirmation → apply path local to an authenticated desktop user. Do not add a Revit credential, a model path, or an external bridge address to repository variables.

## Recovery and troubleshooting

1. **Scheduled run is skipped:** Verify `AGENT_LOOP_SCHEDULE_ENABLED=true`; verify the workflow file exists on the default branch; check the expiry timestamp.
2. **Expiry check fails:** Disable the schedule, set a new timestamp within the reviewed seven-day window, then enable it again only after operator approval.
3. **Three failures stop work:** Inspect the three workflow runs and their reports. Fix the failing bounded validation before manually starting a new reviewed run.
4. **Evidence branch is absent:** Confirm `AGENT_LOOP_PUSH_REVIEW_BRANCH=true`, the dry-run succeeded, and the repository permits `GITHUB_TOKEN` contents writes. No source change is expected.
5. **Budget concern:** Disable the schedule, inspect Actions billing/usage, and use one manual run while investigating.

[^github-actions]: [GitHub Actions billing](https://docs.github.com/billing/managing-billing-for-github-actions/about-billing-for-github-actions) and [GitHub pricing](https://github.com/pricing).
