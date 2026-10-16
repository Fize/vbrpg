import { expect, test } from "@playwright/test";

const adminPassword = "initial-password-1";
const playerName = "e2e-m3-player";
const playerPassword = "m3-player-password-1";

async function login(page: import("@playwright/test").Page, username: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("用户名").fill(username);
  await page.getByLabel("密码", { exact: true }).fill(password);
  await page.getByRole("button", { name: "登录" }).click();
  await expect(page).toHaveURL(/\/lobby$/);
}

/**
 * 两个真人 + 一个 AI 的开局。AI 席位由 worker 驱动，浏览器套件里没有 worker，所以这一局停在
 * 「等 AI 发言」；两个真人那半局在浏览器里是真跑的，记录页看的也是真记录。
 */
test.describe.serial("M3 对局界面", () => {
  test("管理员开一局：两个真人席位 + 一个 AI 席位", async ({ page }) => {
    await login(page, "e2e-root", adminPassword);

    await page.goto("/admin/users");
    await page.getByLabel("用户名").fill(playerName);
    await page.getByLabel("临时密码").fill(playerPassword);
    await page.getByRole("button", { name: "创建" }).click();
    await expect(page.getByRole("cell", { name: playerName })).toBeVisible();

    await page.goto("/lobby");
    await page.getByRole("button", { name: "新建对局" }).click();
    const seatInputs = page.getByPlaceholder("留空表示自己占该席位");
    await expect(seatInputs).toHaveCount(2);
    await seatInputs.nth(1).fill(playerName);
    await page.getByRole("button", { name: "开局" }).click();

    await expect(page).toHaveURL(/\/matches\/[0-9a-f-]{36}$/);
    await expect(page.getByText("当前等待点")).toBeVisible();
    await expect(page.getByText("s3", { exact: true }).first()).toBeVisible();
    await expect(page.getByTestId("my-actions")).toContainText("seatMessage");
    await expect(page.getByPlaceholder("你要说的话")).toBeVisible();

    await page.getByPlaceholder("你要说的话").fill("我这东西很甜");
    await page.getByRole("button", { name: "提交" }).click();
    await expect(page.getByText("我这东西很甜").first()).toBeVisible();
    // The seat has spoken: the match is waiting for the other two now.
    await expect(page.getByTestId("my-actions")).toContainText("现在轮不到你");

    await page.getByRole("tab", { name: "记录" }).click();
    await expect(page.getByTestId("record-table")).toContainText("对局创建");
    await expect(page.getByTestId("record-table")).toContainText("席位发言");
    await expect(page.getByTestId("record-table")).toContainText("#1");
  });

  test("第二个真人在自己的控制台里接着玩", async ({ page }) => {
    await login(page, playerName, playerPassword);
    await expect(page.getByText("undercover@1.0.0").first()).toBeVisible();
    await page.getByRole("button", { name: "进入房间" }).first().click();

    await expect(page).toHaveURL(/\/matches\/[0-9a-f-]{36}$/);
    // Its own seat, its own waiting point, its own action.
    await expect(page.getByText("我的席位")).toBeVisible();
    await expect(page.getByText("等待 s2")).toBeVisible();
    await page.getByPlaceholder("你要说的话").fill("我这东西长在树上");
    await page.getByRole("button", { name: "提交" }).click();

    await expect(page.getByText("我这东西长在树上").first()).toBeVisible();
    await expect(page.getByText("我这东西很甜").first()).toBeVisible();
    // Both humans have spoken; the seat left is the AI, which no browser suite drives.
    await expect(page.getByText("等待 s3")).toBeVisible();
    await expect(page.getByTestId("my-actions")).toContainText("现在轮不到你");
  });

  test("管理员暂停、恢复、取消这一局", async ({ page }) => {
    await login(page, "e2e-root", adminPassword);
    await page.getByRole("button", { name: "进入房间" }).first().click();
    await expect(page.getByTestId("admin-ops")).toBeVisible();

    await page.getByTestId("admin-ops").getByRole("button", { name: "暂停" }).click();
    await expect(page.getByText("已暂停").first()).toBeVisible();
    // A suspended match takes no input, and the page says so instead of offering the form.
    await expect(page.getByTestId("my-actions")).toContainText("不接受输入");

    await page.getByTestId("admin-ops").getByRole("button", { name: "恢复" }).click();
    await expect(page.getByText("等待行动").first()).toBeVisible();

    await page.getByTestId("admin-ops").getByRole("button", { name: "取消对局" }).click();
    await page.getByRole("button", { name: "确认取消" }).click();
    await expect(page.getByText("已取消").first()).toBeVisible();

    // The record survives the lifecycle change: cancelling is not a game event.
    await page.getByRole("tab", { name: "记录" }).click();
    await expect(page.getByTestId("record-table")).toContainText("席位发言");
  });
});
