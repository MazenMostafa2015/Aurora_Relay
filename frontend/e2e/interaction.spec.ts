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
    if (path.endsWith("/connectors") && request.method() === "GET") {
      await route.fulfill({ json: { connectors, count: connectors.length } });
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
