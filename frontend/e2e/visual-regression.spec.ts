import { expect, test, type Page } from "@playwright/test";

const localUser = {
  id: "visual-test-user",
  username: "visual.operator",
  email: "visual.operator@aurora.local",
  is_admin: false,
};

async function mockVisualLocalApi(page: Page) {
  let authenticated = false;
  const extensions = [{
    id: "aurora.sandbox-echo",
    display_name: "Sandbox Echo",
    version: "1.0.0",
    description: "A reviewed local sample that proves extension code runs only inside the Docker sandbox.",
    kind: "sandboxed_tool",
    permissions: ["sandbox.execute"],
    entrypoint: "sandbox-echo.js",
    connector_provider: null,
    installed: false,
    status: "not_installed",
    enabled: false,
    configuration: {},
    last_error: null,
  }];

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/auth/login") && request.method() === "POST") {
      authenticated = true;
      await route.fulfill({ json: { access_token: "visual-local-token", token_type: "bearer", expires_in: 3600, user_id: localUser.id } });
      return;
    }
    if (path.endsWith("/auth/me")) {
      await route.fulfill(authenticated ? { json: localUser } : { status: 401, json: { detail: "Not authenticated" } });
      return;
    }
    if (path.endsWith("/extensions/catalog")) {
      await route.fulfill({ json: { extensions, count: extensions.length } });
      return;
    }
    await route.fulfill({ json: { tools: [], tasks: [], connectors: [], loops: [], count: 0 } });
  });
}

async function signInForVisualBaseline(page: Page) {
  await page.getByRole("button", { name: "Sign in" }).first().click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Username").fill("visual.operator");
  await dialog.getByLabel("Password").fill("visual-local-password");
  await dialog.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Welcome back, visual.operator." })).toBeVisible();
}

test("dashboard visual baselines remain stable for local overview, operations fallback, and reviewed extension catalog", async ({ page }) => {
  await mockVisualLocalApi(page);
  await page.goto("/");
  await signInForVisualBaseline(page);

  await expect(page).toHaveScreenshot("overview-local.png", { fullPage: true });

  await page.getByRole("button", { name: "Operations", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Operations", exact: true })).toBeVisible();
  await expect(page.getByText("Packaged local fallback", { exact: true })).toBeVisible();
  await expect(page).toHaveScreenshot("operations-fallback.png", { fullPage: true });

  await page.getByRole("button", { name: "Extensions", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Extensions", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sandbox Echo", exact: true })).toBeVisible();
  await expect(page).toHaveScreenshot("extensions-catalog.png", { fullPage: true });
});
