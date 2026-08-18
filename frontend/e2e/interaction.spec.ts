import { expect, test, type Page } from "@playwright/test";

const user = {
  id: "local-test-user",
  username: "test.operator",
  email: "test.operator@aurora.local",
  is_admin: false,
};

async function mockLocalApi(page: Page) {
  let authenticated = false;
  let lastAuthorization = "";
  const connectors = [
    { id: "github-local", provider: "github", display_name: "Engineering GitHub", status: "connected", sort_order: 1, configuration: {}, credential_configured: true, capabilities: ["repository.read", "issue.write"], last_tested_at: "2026-08-18T08:30:00Z", last_error: null, created_at: "2026-08-18T08:00:00Z", updated_at: "2026-08-18T08:30:00Z" },
    { id: "revit-local", provider: "revit", display_name: "Local Revit mock", status: "connected", sort_order: 2, configuration: { mode: "mock" }, credential_configured: false, capabilities: ["model.read", "parameter.write", "transaction.preview", "transaction.apply"], last_tested_at: "2026-08-18T08:30:00Z", last_error: null, created_at: "2026-08-18T08:00:00Z", updated_at: "2026-08-18T08:30:00Z" },
  ];
  let agentLoop = {
    id: "loop-local-001", name: "Repository improvement loop", enabled: false, hard_stop: false, status: "idle", runs_completed: 0, consecutive_failures: 0,
    next_run_at: null, started_at: null, ends_at: "2026-08-25T20:00:00Z", last_error: null, latest_report: null,
    config: { enabled: false, dry_run: true, schedule: { frequency: "daily", times_per_day: 5, duration_days: 7, start_time: "08:00", end_time: "20:00", time_zone: "UTC" }, scope: { areas: ["code", "tests", "ui", "connectors"], max_actions_per_loop: 8, allow_destructive_actions: false }, guardrails: { max_loops_total: 35, max_consecutive_failures: 3, require_approval_for: ["deploy", "release", "delete", "external"], rollback_on_error: true }, reporting: { summary_after_each_loop: true, daily_digest: true, final_report: true, notification_channel: "ui" }, repository: { branch_prefix: "aurora-agent/loop", allow_review_branch_push: true, allow_merge: false, allow_deploy: false, allow_release: false } },
    created_at: "2026-08-18T08:00:00Z", updated_at: "2026-08-18T08:00:00Z",
  };
  let agentIterations: Array<Record<string, unknown>> = [];
  const extensions = [
    {
      id: "aurora.sandbox-echo", display_name: "Sandbox Echo", version: "1.0.0",
      description: "A reviewed local sample that proves extension code runs only inside the Docker sandbox.",
      kind: "sandboxed_tool", permissions: ["sandbox.execute"], entrypoint: "sandbox-echo.js", connector_provider: null,
      installed: false, status: "not_installed", enabled: false, configuration: {}, last_error: null,
    },
    {
      id: "aurora.connector.github", display_name: "GitHub Connector Adapter", version: "1.0.0",
      description: "A built-in compatibility adapter that routes GitHub operations through existing authenticated connector controls.",
      kind: "connector_adapter", permissions: ["connector.read"], entrypoint: null, connector_provider: "github",
      installed: false, status: "not_installed", enabled: false, configuration: {}, last_error: null,
    },
  ];

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    lastAuthorization = request.headers().authorization || "";

    if (path.endsWith("/auth/login") && request.method() === "POST") {
      authenticated = true;
      await route.fulfill({ json: { access_token: "test-local-token", token_type: "bearer", expires_in: 3600, user_id: user.id } });
      return;
    }
    if (path.endsWith("/auth/register") && request.method() === "POST") {
      await route.fulfill({ status: 201, json: user });
      return;
    }
    if (path.endsWith("/auth/me")) {
      await route.fulfill(authenticated
        ? { json: user }
        : { status: 401, json: { detail: "Not authenticated" } });
      return;
    }
    if (path.endsWith("/auth/logout") && request.method() === "POST") {
      authenticated = false;
      await route.fulfill({ json: { message: "Logged out" } });
      return;
    }
    if (path.endsWith("/tasks") && request.method() === "POST") {
      const body = request.postDataJSON() as { order: string };
      await route.fulfill({ status: 201, json: {
        id: "task-live-001", user_id: user.id, order: body.order, status: "executing", progress: 0.12,
        steps: [{ id: "step-1", task_id: "task-live-001", description: "Frame the request", status: "executing" }],
        created_at: "2026-08-18T08:30:00Z", context: {}, estimated_complexity: "moderate",
      } });
      return;
    }
    if (path.endsWith("/operations/health") && request.method() === "GET") {
      await route.fulfill({ json: {
        generated_at: "2026-08-18T09:15:00Z",
        system: { status: "operational", version: "0.8.22", uptime_seconds: 7260, last_loop_completion: "2026-08-18T08:55:00Z" },
        connectors: [
          { id: "github-local", display_name: "Engineering GitHub", provider: "github", status: "connected", last_connected: "2026-08-18T08:30:00Z", error: null },
          { id: "revit-local", display_name: "Local Revit mock", provider: "revit", status: "warning", last_connected: null, error: "Local bridge is awaiting an operator test" },
        ],
        agent_loop: { state: "idle", current_iteration: 0, total_iterations: 8, last_result: "Review-required evidence only", next_run: null, recent_iterations: [] },
        release: { version: "v0.8.22", sha256_verified: true, provenance_verified: true, signer_pinned: true, timestamp_present: true, clean_machine_verified: true, trust_note: "Internal self-signed signer pin is recorded; public trust is not asserted." },
        vault: { state: "ready", backend: "windows-credential-vault", fallback: false, message: "Credential protection is ready. Connector secret values are never returned to this dashboard." },
        activities: [{ id: "release-001", type: "success", message: "v0.8.22 evidence verified", source: "release ledger", timestamp: "2026-08-18T09:00:00Z" }],
        alerts: [{ id: "revit-bridge", severity: "warning", message: "Revit bridge needs a local operator test", recommendation: "Open Connectors and run the Revit mock test." }],
      } });
      return;
    }
    if (path.endsWith("/extensions/catalog") && request.method() === "GET") {
      await route.fulfill({ json: { extensions, count: extensions.length } });
      return;
    }
    if (path.endsWith("/extensions") && request.method() === "POST") {
      const body = request.postDataJSON() as { extension_id: string };
      const index = extensions.findIndex((item) => item.id === body.extension_id);
      if (index < 0) { await route.fulfill({ status: 404, json: { detail: "Unknown reviewed extension" } }); return; }
      extensions[index] = { ...extensions[index], installed: true, status: "disabled" };
      await route.fulfill({ status: 201, json: extensions[index] });
      return;
    }
    const extensionUpdate = path.match(/\/extensions\/([^/]+)$/);
    if (extensionUpdate && request.method() === "PATCH") {
      const extensionId = decodeURIComponent(extensionUpdate[1]);
      const index = extensions.findIndex((item) => item.id === extensionId);
      if (index < 0) { await route.fulfill({ status: 404, json: { detail: "Unknown reviewed extension" } }); return; }
      const body = request.postDataJSON() as { enabled?: boolean; configuration?: Record<string, unknown> };
      const current = extensions[index];
      extensions[index] = {
        ...current,
        enabled: typeof body.enabled === "boolean" ? body.enabled : current.enabled,
        status: typeof body.enabled === "boolean" ? (body.enabled ? "ready" : "disabled") : current.status,
        configuration: body.configuration ?? current.configuration,
      };
      await route.fulfill({ json: extensions[index] });
      return;
    }
    if (path.endsWith("/extensions/aurora.sandbox-echo/execute") && request.method() === "POST") {
      await route.fulfill({ json: { extension_id: "aurora.sandbox-echo", state: "completed", message: "Sandbox command completed without host execution.", exit_code: 0, stdout: "sandbox echo: Aurora Relay", stderr: "" } });
      return;
    }
    if (path.endsWith("/connectors") && request.method() === "GET") {
      await route.fulfill({ json: { connectors, count: connectors.length } });
      return;
    }
    if (path.endsWith("/agent-loops") && request.method() === "GET") {
      await route.fulfill({ json: { loops: [agentLoop], count: 1 } });
      return;
    }
    if (path.endsWith("/agent-loops/loop-local-001/start") && request.method() === "POST") {
      agentLoop = { ...agentLoop, enabled: true, status: "scheduled", next_run_at: "2026-08-19T08:00:00Z" };
      await route.fulfill({ json: agentLoop });
      return;
    }
    if (path.endsWith("/agent-loops/loop-local-001/pause") && request.method() === "POST") {
      agentLoop = { ...agentLoop, enabled: false, status: "paused" };
      await route.fulfill({ json: agentLoop });
      return;
    }
    if (path.endsWith("/agent-loops/loop-local-001/hard-stop") && request.method() === "POST") {
      agentLoop = { ...agentLoop, enabled: false, hard_stop: true, status: "stopped" };
      await route.fulfill({ json: agentLoop });
      return;
    }
    if (path.endsWith("/agent-loops/loop-local-001/run-dry") && request.method() === "POST") {
      const iteration = { id: "iteration-local-001", loop_id: agentLoop.id, sequence: agentIterations.length + 1, status: "completed", dry_run: true, branch_name: "aurora-agent/loop/20260818-080000", plan_path: "reports/agent-loop/plan.json", log_path: "reports/agent-loop/log.json", report_path: "reports/agent-loop/report.json", plan: {}, actions: [], reflection: {}, validation: { ok: true }, error: null, started_at: "2026-08-18T08:00:00Z", completed_at: "2026-08-18T08:01:00Z" };
      agentIterations = [iteration];
      agentLoop = { ...agentLoop, runs_completed: 1, latest_report: { status: "completed" } };
      await route.fulfill({ json: iteration });
      return;
    }
    if (path.endsWith("/agent-loops/loop-local-001/iterations") && request.method() === "GET") {
      await route.fulfill({ json: { iterations: agentIterations, count: agentIterations.length } });
      return;
    }
    if (path.endsWith("/revit/plan") && request.method() === "POST") {
      await route.fulfill({ json: { operation_id: "revit-plan-001", state: "planned", requires_confirmation: true, preview: { transaction: "Aurora Relay: set Comments", mode: "mock", operation: "set_parameter", element: { id: 101, name: "Exterior wall" }, parameter: "Comments", before: "", after: "Reviewed by Aurora Relay" }, message: "Review the model preview, then confirm with APPLY to execute this transaction." } });
      return;
    }
    if (path.endsWith("/revit/operations/revit-plan-001/apply") && request.method() === "POST") {
      const body = request.postDataJSON() as { confirmation: string };
      await route.fulfill(body.confirmation === "APPLY"
        ? { json: { operation_id: "revit-plan-001", state: "applied", message: "Parameter updated in the mock model", result: { mode: "mock" } } }
        : { status: 400, json: { detail: "Revit changes require the explicit APPLY confirmation" } });
      return;
    }
    await route.fulfill({ json: { tools: [], tasks: [] } });
  });

  return {
    authorization: () => lastAuthorization,
  };
}

async function signIn(page: Page) {
  await page.getByRole("button", { name: "Sign in" }).first().click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await dialog.getByLabel("Username").fill("test.operator");
  await dialog.getByLabel("Password").fill("correct-password");
  await dialog.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Welcome back, test.operator." })).toBeVisible();
}

test("renderer startup keeps network requests on the local origin", async ({ page }) => {
  const externalRequests: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if ((url.protocol === "http:" || url.protocol === "https:") && !["127.0.0.1", "localhost"].includes(url.hostname)) {
      externalRequests.push(request.url());
    }
  });
  await mockLocalApi(page);
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Sign in" }).first()).toBeVisible();
  expect(externalRequests).toEqual([]);
});

test("authentication controls sign in, persist the local session, and sign out", async ({ page }) => {
  const api = await mockLocalApi(page);
  await page.goto("/");

  await expect(page.getByRole("button", { name: "Sign in" }).first()).toBeVisible();
  await signIn(page);
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
  expect(api.authorization()).toBe("Bearer test-local-token");

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("button", { name: "Sign in" }).first()).toBeVisible();
});

test("navigation, task submission, attachment selection, and feedback controls are interactive", async ({ page }) => {
  await mockLocalApi(page);
  await page.goto("/");
  await signIn(page);

  await page.getByRole("button", { name: "Tool explorer", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Tool explorer" })).toBeVisible();
  await page.getByRole("button", { name: "Overview", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Welcome back, test.operator." })).toBeVisible();

  await page.getByLabel("Task direction").fill("Create a source-backed local release summary");
  await page.getByRole("button", { name: "Run task" }).click();
  await expect(page.getByRole("heading", { name: "Task desk" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Create a source-backed local release summary", exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await page.getByRole("button", { name: /Ollama · phi3:mini/ }).click();
  await expect(page.getByText("Model selection is managed by the local Ollama runtime.")).toBeVisible();
});

test("release evidence exposes the signed installer and locally inspectable verification ledger", async ({ page }) => {
  await page.context().grantPermissions(["clipboard-write"]);
  await mockLocalApi(page);
  await page.goto("/");
  await signIn(page);

  await page.getByRole("button", { name: "Release evidence", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Release evidence" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Release assets" })).toBeVisible();
  await expect(page.getByText("Aurora-Relay-0.8.22-win-x64.exe", { exact: true })).toBeVisible();
  await expect(page.getByText("Digest matched", { exact: true })).toBeVisible();
  await expect(page.getByText("Internal trust boundary", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Download Aurora-Relay-0.8.22-win-x64.exe" })).toHaveAttribute("href", /Aurora-Relay-0.8.22-win-x64.exe/);
  await page.getByRole("button", { name: "Copy Installer SHA-256" }).click();
  await expect(page.getByText("Installer SHA-256 copied")).toBeVisible();
});

test("operations health keeps a packaged fallback until the operator requests a local authenticated refresh", async ({ page }) => {
  await mockLocalApi(page);
  await page.goto("/");
  await signIn(page);

  await page.getByRole("button", { name: "Operations", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Operations", exact: true })).toBeVisible();
  await expect(page.getByText("Packaged local fallback", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Refresh operational status" }).click();
  await expect(page.getByLabel("Operational health summary").getByText("Operational", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Connectors", exact: true })).toBeVisible();
  await expect(page.getByText("Engineering GitHub", { exact: true })).toBeVisible();
  await expect(page.getByText("v0.8.22 evidence verified", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: /Dismiss alert: Revit bridge needs a local operator test/ }).click();
  await expect(page.getByText("No active operational alerts.", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Manage" }).click();
  await expect(page.getByRole("heading", { name: "Connectors", exact: true })).toBeVisible();
});

test("reviewed local extensions remain disabled by default and execute only through the Docker sandbox boundary", async ({ page }) => {
  await mockLocalApi(page);
  await page.goto("/");
  await signIn(page);

  await page.getByRole("button", { name: "Extensions", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Extensions", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sandbox Echo", exact: true })).toBeVisible();
  await expect(page.locator(".extension-hero-seal")).toContainText("Host execution");
  await expect(page.getByRole("button", { name: "Install disabled" })).toBeVisible();
  await page.getByRole("button", { name: "Install disabled" }).click();
  await expect(page.getByRole("button", { name: "Enable extension" })).toBeVisible();
  await expect(page.getByText("Disabled extensions cannot run.", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Enable extension" }).click();
  await expect(page.getByRole("button", { name: "Run in Docker" })).toBeEnabled();
  await page.getByRole("button", { name: "Run in Docker" }).click();
  await expect(page.getByText("Sandbox result", { exact: true })).toBeVisible();
  await expect(page.getByText("sandbox echo: Aurora Relay", { exact: true })).toBeVisible();
});

test("built-in connector adapters expose non-secret configuration without bypassing connector credential controls", async ({ page }) => {
  await mockLocalApi(page);
  await page.goto("/");
  await signIn(page);

  await page.getByRole("button", { name: "Extensions", exact: true }).click();
  await page.getByRole("button", { name: /GitHub Connector Adapter/ }).click();
  await expect(page.getByRole("heading", { name: "GitHub Connector Adapter", exact: true })).toBeVisible();
  await expect(page.getByText("Built-in adapter for the existing", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Install disabled" }).click();
  await page.getByLabel("Extension configuration JSON").fill('{\n  "repository_scope": "read"\n}');
  await page.getByRole("button", { name: "Save configuration" }).click();
  await expect(page.getByText("Extension configuration saved", { exact: true })).toBeVisible();
  await expect(page.getByText("Credentials, tokens, and passwords are rejected here", { exact: false })).toBeVisible();
  await expect(page.getByRole("button", { name: "Run in Docker" })).toHaveCount(0);
});

test("sign-in dialog supports local account creation", async ({ page }) => {
  await mockLocalApi(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Sign in" }).first().click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: "Create account" }).click();
  await dialog.getByLabel("Username").fill("new.operator");
  await dialog.getByLabel("Email").fill("new.operator@aurora.local");
  await dialog.getByLabel("Password").fill("safe-local-password");
  await dialog.getByRole("button", { name: "Create account" }).last().click();
  await expect(page.getByRole("heading", { name: "Welcome back, test.operator." })).toBeVisible();
});

test("connectors expose configured status and require a preview plus APPLY confirmation for Revit changes", async ({ page }) => {
  await mockLocalApi(page);
  await page.goto("/");
  await signIn(page);

  await page.getByRole("button", { name: "Connectors", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Connectors" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Engineering GitHub" })).toBeVisible();
  await page.getByRole("button", { name: /Local Revit mock/ }).click();
  await page.getByRole("button", { name: /Preview change/ }).click();
  await expect(page.getByText("Planned transaction")).toBeVisible();
  const apply = page.getByRole("button", { name: "Apply planned change" });
  await expect(apply).toBeDisabled();
  await page.getByPlaceholder("APPLY").fill("APPLY");
  await expect(apply).toBeEnabled();
  await apply.click();
  await expect(page.getByText("Parameter updated in the mock model")).toBeVisible();
});

test("repository agent loop remains dry-run only and requires STOP before hard-stop", async ({ page }) => {
  await mockLocalApi(page);
  await page.goto("/");
  await signIn(page);

  await page.getByRole("button", { name: "Agent loop", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Agent loop" })).toBeVisible();
  await expect(page.getByText("Dry-run only", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Run dry scan now" }).click();
  await expect(page.getByText("#1", { exact: true })).toBeVisible();
  const hardStop = page.getByRole("button", { name: "Hard stop" });
  await expect(hardStop).toBeDisabled();
  await page.getByLabel("Type STOP to hard stop loop").fill("STOP");
  await expect(hardStop).toBeEnabled();
  await hardStop.click();
  await expect(page.getByText("Hard stopped", { exact: true })).toBeVisible();
});

test("secondary workspace controls provide visible actions across the dashboard", async ({ page }) => {
  await mockLocalApi(page);
  await page.goto("/");
  await signIn(page);

  await page.getByRole("button", { name: "Help" }).click();
  await expect(page.getByText("Aurora Relay keeps execution on this device; sign in to submit tasks.")).toBeVisible();

  await page.getByRole("button", { name: "Open tool explorer" }).click();
  await expect(page.getByRole("heading", { name: "Tool explorer" })).toBeVisible();
  await page.getByRole("button", { name: /^Task desk/ }).click();
  await expect(page.getByRole("heading", { name: "Task desk" })).toBeVisible();
  await page.getByRole("button", { name: "Research sprint" }).click();
  await expect(page.getByText("Task desk opened")).toBeVisible();
  await page.getByRole("button", { name: "Approval queue" }).click();
  await expect(page.getByText("Approval queue opened")).toBeVisible();

  await page.getByRole("button", { name: "Overview", exact: true }).click();
  await page.locator('input[type="file"]').setInputFiles({
    name: "release-context.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("local context"),
  });
  await expect(page.getByRole("button", { name: "Attached: release-context.txt" })).toBeVisible();
  await page.getByRole("button", { name: "View full event stream" }).click();
  await expect(page.getByRole("heading", { name: "Task desk" })).toBeVisible();
  await page.getByRole("button", { name: "Open detail" }).first().click();
  await page.getByRole("button", { name: "View all" }).click();
  await expect(page.getByRole("heading", { name: "Task desk" })).toBeVisible();

  await page.getByRole("button", { name: "Open settings" }).click();
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await page.getByRole("button", { name: "Manage profile" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByRole("dialog")).toBeHidden();
  await page.getByRole("button", { name: /Ollama · phi3:mini/ }).click();
  await expect(page.getByText("Model selection is managed by the local Ollama runtime.")).toBeVisible();
  await page.getByRole("button", { name: /Always ask/ }).click();
  await expect(page.getByText("Approval mode is enforced by the local coordinator.")).toBeVisible();
  await page.getByRole("button", { name: /Aurora dark/ }).click();
  await expect(page.getByText("Aurora dark is active for this desktop workspace.")).toBeVisible();
});

test("mobile navigation toggle changes the sidebar state", async ({ page }) => {
  await mockLocalApi(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const sidebar = page.locator(".sidebar-wrap");
  await expect(sidebar).toHaveClass(/open/);
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await expect(sidebar).not.toHaveClass(/open/);
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await expect(sidebar).toHaveClass(/open/);
});
