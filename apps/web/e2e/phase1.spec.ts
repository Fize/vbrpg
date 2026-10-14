import { expect, test } from "@playwright/test";

const initialPassword = "initial-password-1";
const newPassword = "changed-password-1";
const userPassword = "temporary-user-pw-1";
const providerApiKey = "sk-e2e-never-return-this";

async function login(page: import("@playwright/test").Page, username: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

test.describe.serial("Phase 1 browser acceptance", () => {
  test("admin must change the bootstrap password before reaching the lobby", async ({ page }) => {
    await login(page, "e2e-root", initialPassword);
    await expect(page).toHaveURL(/\/change-password$/);
    await expect(page.getByRole("heading", { name: /change password/i })).toBeVisible();

    await page.getByLabel("Current password").fill(initialPassword);
    await page.getByLabel("New password", { exact: true }).fill(newPassword);
    await page.getByLabel("Confirm new password").fill(newPassword);
    await page.getByRole("button", { name: "Save new password" }).click();
    await expect(page).toHaveURL(/\/lobby$/);
    await expect(page.getByText(/game lobby arrives in a later phase/i)).toBeVisible();
  });

  test("admin provisions a user and provider/model; secrets do not appear in the UI", async ({ page }) => {
    await login(page, "e2e-root", newPassword);
    await expect(page).toHaveURL(/\/lobby$/);

    await page.goto("/admin/users");
    await expect(page.getByRole("heading", { name: /users/i })).toBeVisible();
    await page.getByLabel("Username").fill("e2e-player");
    await page.getByLabel(/temporary password/i).fill(userPassword);
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.getByText(/temporary password is never displayed again/i)).toBeVisible();
    await expect(page.getByRole("cell", { name: "e2e-player" })).toBeVisible();

    await page.goto("/admin/providers");
    await page.getByLabel("Name").fill("e2e-provider");
    await page.getByLabel("Base URL").first().fill("https://api.openai.com/v1");
    await page.getByLabel("API key").first().fill(providerApiKey);
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.getByText("e2e-provider")).toBeVisible();
    await expect(page.getByText(/secret configured/i)).toBeVisible();
    await expect(page.getByText(providerApiKey)).toHaveCount(0);

    await page.getByLabel(/model id/i).fill("gpt-test");
    await page.getByLabel(/display name/i).fill("Test Model");
    await page.getByRole("button", { name: "Add model" }).click();
    await expect(page.getByRole("cell", { name: "Test Model" })).toBeVisible();

    await page.getByRole("button", { name: /test connection/i }).click();
    await expect(page.getByText(/unauthorized|provider_error|rate_limited/i)).toBeVisible();
    await expect(page.getByText(providerApiKey)).toHaveCount(0);

    const secretLeaks = await page.evaluate(() =>
      document.body.innerText.includes("sk-e2e-never-return-this"),
    );
    expect(secretLeaks).toBe(false);
  });

  test("user login/logout works and admin routes redirect non-admins", async ({ page }) => {
    await login(page, "e2e-player", userPassword);
    await expect(page).toHaveURL(/\/change-password$/);
    await page.getByLabel("Current password").fill(userPassword);
    await page.getByLabel("New password", { exact: true }).fill("player-changed-pw-1");
    await page.getByLabel("Confirm new password").fill("player-changed-pw-1");
    await page.getByRole("button", { name: "Save new password" }).click();
    await expect(page).toHaveURL(/\/lobby$/);

    await page.goto("/admin/users");
    await expect(page).toHaveURL(/\/lobby$/);

    await page.getByRole("banner").getByRole("button", { name: "Log out" }).click();
    await expect(page).toHaveURL(/\/login$/);
  });

  test("login form validates required inputs and displays generic auth errors", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByText("Username is required.")).toBeVisible();
    await expect(page.getByText("Password is required.")).toBeVisible();

    await page.getByLabel("Username").fill("e2e-root");
    await page.getByLabel("Password").fill("wrong-password");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("alert")).toContainText("Invalid username or password");
  });
});
