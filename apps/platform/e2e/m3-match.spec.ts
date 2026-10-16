import { expect, test } from "@playwright/test";

const adminPassword = "initial-password-1";
const playerName = "e2e-m3-player";
const playerPassword = "m3-player-password-1";
const watcherName = "e2e-m3-watcher";
const watcherPassword = "m3-watcher-password-1";

/** Shared across the serial cases: which match this run created. */
let matchId = "";

async function login(page: import("@playwright/test").Page, username: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("用户名").fill(username);
  await page.getByLabel("密码", { exact: true }).fill(password);
  await page.getByRole("button", { name: "登录" }).click();
  await expect(page).toHaveURL(/\/lobby$/);
}

async function provision(page: import("@playwright/test").Page, username: string, password: string) {
  await page.goto("/admin/users");
  await page.getByLabel("用户名").fill(username);
  await page.getByLabel("临时密码").fill(password);
  await page.getByRole("button", { name: "创建" }).click();
  await expect(page.getByRole("cell", { name: username })).toBeVisible();
}

/**
 * 两个真人 + 一个 AI 的开局，加上一个旁观账号。AI 席位由 worker 驱动，浏览器套件里没有 worker，
 * 所以这一局停在「等 AI 发言」；两个真人那半局在浏览器里是真跑的，记录页看的也是真记录。
 */
test.describe.serial("M3 对局界面", () => {
  test("管理员开一局：两个真人席位 + 一个 AI 席位", async ({ page }) => {
    await login(page, "e2e-root", adminPassword);
    await provision(page, playerName, playerPassword);
    await provision(page, watcherName, watcherPassword);

    await page.goto("/lobby");
    await page.getByRole("button", { name: "新建对局" }).click();
    const seatInputs = page.getByPlaceholder("留空表示自己占该席位");
    await expect(seatInputs).toHaveCount(2);
    await seatInputs.nth(1).fill(playerName);
    await page.getByRole("button", { name: "开局" }).click();

    await expect(page).toHaveURL(/\/matches\/[0-9a-f-]{36}$/);
    matchId = page.url().split("/").pop() ?? "";
    await expect(page.getByText("当前阶段")).toBeVisible();
    await expect(page.getByText("s3", { exact: true }).first()).toBeVisible();
    await expect(page.getByTestId("my-actions")).toContainText("描述");
    await expect(page.getByPlaceholder("你要说的话")).toBeVisible();

    await page.getByPlaceholder("你要说的话").fill("我这东西很甜");
    await page.getByRole("button", { name: "提交" }).click();
    await expect(page.getByText("我这东西很甜").first()).toBeVisible();
    // The seat has spoken: the match is waiting for the other two now.
    await expect(page.getByTestId("my-actions")).toContainText("现在轮不到你");

    // The record is the room's log, not a separate page.
    const log = page.getByTestId("match-log");
    await expect(log).toContainText("对局创建");
    // Rows read in the game's own words, not in event names.
    await expect(log).toContainText("描述");
    await expect(log).toContainText("你要说的话：我这东西很甜");
    await expect(log).toContainText("#1");
  });

  test("第二个真人在自己的控制台里接着玩", async ({ page }) => {
    await login(page, playerName, playerPassword);
    await expect(page.getByText("谁是卧底").first()).toBeVisible();
    await page.getByRole("button", { name: "进入房间" }).first().click();

    await expect(page).toHaveURL(/\/matches\/[0-9a-f-]{36}$/);
    // Its own seat, its own waiting point, its own action.
    await expect(page.getByText("我的席位", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("等 s2、s3")).toBeVisible();
    await page.getByPlaceholder("你要说的话").fill("我这东西长在树上");
    await page.getByRole("button", { name: "提交" }).click();

    await expect(page.getByText("我这东西长在树上").first()).toBeVisible();
    await expect(page.getByText("我这东西很甜").first()).toBeVisible();
    // Both humans have spoken; the seat left is the AI, which no browser suite drives.
    await expect(page.getByText("等 s3")).toBeVisible();
    await expect(page.getByTestId("my-actions")).toContainText("现在轮不到你");
  });

  test("管理员在对局运维页暂停、恢复、取消这一局", async ({ page }) => {
    await login(page, "e2e-root", adminPassword);
    // The lifecycle lives on its own page, not inside the room the admin plays in.
    await page.getByRole("link", { name: "对局运维" }).click();
    await expect(page).toHaveURL(/\/admin\/matches$/);

    const row = page.getByRole("row", { name: new RegExp(matchId) });
    await expect(row).toBeVisible();

    await row.getByRole("button", { name: "暂停" }).click();
    await expect(row).toContainText("已暂停");

    await row.getByRole("button", { name: "恢复" }).click();
    await expect(row).toContainText("等待行动");

    await row.getByRole("button", { name: "取消" }).click();
    await page.getByRole("button", { name: "确认取消" }).click();
    await expect(row).toContainText("已取消");
  });

  test("第三个账号能旁观同一局，但拿不到动作", async ({ page }) => {
    await login(page, watcherName, watcherPassword);
    // The lobby is the match hall: every match is listed, and this account holds no seat anywhere.
    await expect(page.getByText("谁是卧底").first()).toBeVisible();
    await page.getByRole("button", { name: "旁观" }).first().click();
    await expect(page).toHaveURL(new RegExp(`/matches/${matchId}$`));

    await expect(page.getByText("观战中")).toBeVisible();
    await expect(page.getByTestId("my-actions")).toContainText("旁观没有动作可提交");
    await expect(page.getByRole("button", { name: "提交" })).toHaveCount(0);
    // No seat means no private state and no rules: those belong to the seats playing.
    await expect(page.getByText("只给你看的信息")).toHaveCount(0);

    // The table and the record survive the lifecycle change: cancelling is not a game event.
    await expect(page.getByTestId("seat").first()).toBeVisible();
    await expect(page.getByTestId("match-log")).toContainText("描述");
  });
});
