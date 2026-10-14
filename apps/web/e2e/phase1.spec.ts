import { expect, test } from "@playwright/test";

const initialPassword = "initial-password-1";
const newPassword = "changed-password-1";
const userPassword = "temporary-user-pw-1";
const providerApiKey = "sk-e2e-never-return-this";

async function login(page: import("@playwright/test").Page, username: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("用户名").fill(username);
  await page.getByLabel("密码", { exact: true }).fill(password);
  await page.getByRole("button", { name: "登录" }).click();
}

test.describe.serial("Phase 1 browser acceptance", () => {
  test("admin must change the bootstrap password before reaching the lobby", async ({ page }) => {
    await login(page, "e2e-root", initialPassword);
    await expect(page).toHaveURL(/\/change-password$/);
    await expect(page.getByRole("heading", { name: "修改密码" })).toBeVisible();

    await page.getByLabel("当前密码").fill(initialPassword);
    await page.getByLabel("新密码", { exact: true }).fill(newPassword);
    await page.getByLabel("确认新密码").fill(newPassword);
    await page.getByRole("button", { name: "保存新密码" }).click();
    await expect(page).toHaveURL(/\/lobby$/);
    await expect(page.getByText("游戏大厅将在后续阶段开放")).toBeVisible();
  });

  test("admin provisions a user and provider/model; secrets do not appear in the UI", async ({ page }) => {
    await login(page, "e2e-root", newPassword);
    await expect(page).toHaveURL(/\/lobby$/);

    await page.goto("/admin/users");
    await expect(page.getByRole("heading", { name: "用户管理" })).toBeVisible();
    await page.getByLabel("用户名").fill("e2e-player");
    await page.getByLabel("临时密码").fill(userPassword);
    await page.getByRole("button", { name: "创建" }).click();
    await expect(page.getByTestId("created-notice")).toContainText("临时密码不会再次显示");
    await expect(page.getByRole("cell", { name: "e2e-player" })).toBeVisible();

    await page.goto("/admin/providers");
    await page.getByLabel("名称").fill("e2e-provider");
    await page.getByLabel("Base URL").first().fill("https://api.openai.com/v1");
    await page.getByLabel("API 密钥").first().fill(providerApiKey);
    await page.getByRole("button", { name: "创建" }).click();
    await expect(page.getByText("e2e-provider")).toBeVisible();
    await expect(page.getByText("密钥已配置").first()).toBeVisible();
    await expect(page.getByText(providerApiKey)).toHaveCount(0);

    await page.getByLabel("模型 ID", { exact: true }).last().fill("gpt-test");
    await page.getByLabel("显示名").last().fill("Test Model");
    await page.getByRole("button", { name: "添加模型" }).click();
    await expect(page.getByRole("cell", { name: "Test Model" })).toBeVisible();

    await page.getByRole("button", { name: "测试连接" }).click();
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
    await page.getByLabel("当前密码").fill(userPassword);
    await page.getByLabel("新密码", { exact: true }).fill("player-changed-pw-1");
    await page.getByLabel("确认新密码").fill("player-changed-pw-1");
    await page.getByRole("button", { name: "保存新密码" }).click();
    await expect(page).toHaveURL(/\/lobby$/);

    await page.goto("/admin/users");
    await expect(page).toHaveURL(/\/lobby$/);

    await page.getByRole("banner").getByRole("button", { name: "退出登录" }).click();
    await expect(page).toHaveURL(/\/login$/);
  });

  test("login form validates required inputs and displays generic auth errors", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: "登录" }).click();
    await expect(page.getByText("请输入用户名")).toBeVisible();
    await expect(page.getByText("请输入密码")).toBeVisible();

    await page.getByLabel("用户名").fill("e2e-root");
    await page.getByLabel("密码", { exact: true }).fill("wrong-password");
    await page.getByRole("button", { name: "登录" }).click();
    await expect(page.getByTestId("auth-error")).toContainText("用户名或密码不正确");
  });
});
