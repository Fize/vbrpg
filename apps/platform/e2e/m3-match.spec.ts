import { expect, test, type Browser, type Page } from "@playwright/test";

const adminPassword = "initial-password-1";
const playerName = "e2e-m3-player";
const playerPassword = "m3-player-password-1";
const watcherName = "e2e-m3-watcher";
const watcherPassword = "m3-watcher-password-1";
const origin = "http://127.0.0.1:5174";

let roomId = "";
let matchId = "";

async function login(page: Page, username: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("用户名").fill(username);
  await page.getByLabel("密码", { exact: true }).fill(password);
  await page.getByRole("button", { name: "登录" }).click();
  await expect(page).toHaveURL(/\/lobby$/);
}

async function csrf(page: Page): Promise<string> {
  const response = await page.request.get("/v1/auth/csrf");
  const { csrfToken } = (await response.json()) as { csrfToken: string };
  return csrfToken;
}

/**
 * A run needs its two accounts to exist with known passwords. A previous run may have left them
 * behind, so an existing name is reset rather than refused: the test is about playing, not about
 * database hygiene.
 */
async function provision(page: Page, username: string, password: string): Promise<void> {
  const token = await csrf(page);
  const created = await page.request.post("/v1/admin/users", {
    headers: { "x-csrf-token": token, origin },
    data: { username, temporaryPassword: password, role: "user" },
  });
  if (created.ok()) return;

  const listed = await page.request.get("/v1/admin/users");
  const { users } = (await listed.json()) as {
    users: Array<{ id: string; username: string }>;
  };
  const existing = users.find((user) => user.username === username);
  expect(existing, await created.text()).toBeTruthy();
  const patched = await page.request.patch(`/v1/admin/users/${existing?.id ?? ""}`, {
    headers: { "x-csrf-token": token, origin },
    data: { resetPassword: password },
  });
  expect(patched.ok(), await patched.text()).toBeTruthy();
}

/**
 * A room whose words are already known needs no model at all, which is what a test run can offer:
 * loopback providers are refused by design, so nothing here may call one. The room is created
 * through the API with its words, and everything a player does — sitting down, getting ready,
 * starting, playing — happens in the browser.
 */
async function createRoom(page: Page, seats: Array<Record<string, unknown>>): Promise<string> {
  const response = await page.request.post("/v1/rooms", {
    headers: { "x-csrf-token": await csrf(page), origin },
    data: {
      gameId: "undercover",
      seats,
      variables: { civilianWord: "咖啡", undercoverWord: "茶" },
    },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return ((await response.json()) as { roomId: string }).roomId;
}

/** A fresh browser context per account: two humans and a watcher in the same run. */
async function asUser(browser: Browser, username: string, password: string): Promise<Page> {
  const context = await browser.newContext();
  const page = await context.newPage();
  await login(page, username, password);
  return page;
}

test.describe.serial("M7 房间与对局", () => {
  test("建房、坐下、准备、开局，两个真人在浏览器里打起来", async ({ page, browser }) => {
    await login(page, "e2e-root", adminPassword);
    await provision(page, playerName, playerPassword);
    await provision(page, watcherName, watcherPassword);

    // The dialog asks for a category, not for words: the pair is generated when a match starts.
    await page.goto("/lobby");
    await page.getByRole("button", { name: "创建房间" }).first().click();
    await expect(page.getByLabel("分类")).toBeVisible();
    await expect(page.getByText("开局时才生成，现在是占位")).toBeVisible();
    await page.getByRole("button", { name: "取消" }).click();

    roomId = await createRoom(page, [
      { key: "s1", control: "human" },
      { key: "s2", control: "human" },
      { key: "s3", control: "ai" },
      { key: "s4", control: "ai" },
    ]);
    await page.goto(`/rooms/${roomId}`);

    // The room is the table: seats, AI placeholders, and why a start is not possible yet.
    await expect(page.getByTestId("room-seats")).toContainText("AI 占位");
    await expect(page.getByTestId("room-seats")).toContainText("不需要");
    await expect(page.getByTestId("room-blockers")).toContainText("还有空席位");
    await page.getByRole("button", { name: "我准备好了" }).click();
    await expect(page.getByTestId("room-seats")).toContainText("已准备");

    // The second human joins from their own console and gets ready.
    const player = await asUser(browser, playerName, playerPassword);
    await expect(player.getByTestId("room-list")).toContainText("等开局");
    await player.getByRole("button", { name: "坐下" }).click();
    await expect(player).toHaveURL(new RegExp(`/rooms/${roomId}$`));
    await expect(player.getByTestId("room-seats")).toContainText("我");
    await player.getByRole("button", { name: "我准备好了" }).click();
    await expect(player.getByTestId("room-seats")).toContainText("已准备");

    // With everyone seated and ready the owner starts; a match is dealt only now.
    await page.reload();
    await expect(page.getByTestId("room-blockers")).toHaveCount(0);
    await page.getByTestId("room-start").click();
    await expect(page).toHaveURL(/\/matches\/[0-9a-f-]{36}$/);
    matchId = page.url().split("/").pop() ?? "";

    await expect(page.getByText("当前阶段")).toBeVisible();
    await expect(page.getByPlaceholder("你要说的话")).toBeVisible();
    await page.getByPlaceholder("你要说的话").fill("我这东西很甜");
    await page.getByRole("button", { name: "提交" }).click();
    await expect(page.getByText("我这东西很甜").first()).toBeVisible();
    await expect(page.getByTestId("my-actions")).toContainText("现在轮不到你");

    const log = page.getByTestId("match-log");
    await expect(log).toContainText("对局创建");
    await expect(log).toContainText("你要说的话：我这东西很甜");

    // The second human reaches the same match from the room it belongs to.
    await player.goto(`/rooms/${roomId}`);
    await expect(player.getByText("对局中")).toBeVisible();
    await player.getByRole("button", { name: "进入" }).click();
    await expect(player).toHaveURL(new RegExp(`/matches/${matchId}$`));
    // The description phase asks one seat at a time, in seat order: s2 is next in line.
    await expect(player.getByText("等 s2")).toBeVisible();
    await player.getByPlaceholder("你要说的话").fill("我这东西长在树上");
    await player.getByRole("button", { name: "提交" }).click();
    await expect(player.getByText("我这东西长在树上").first()).toBeVisible();
    // Both humans have spoken; the seat left is the AI, which no browser suite drives.
    await expect(player.getByText("等 s3")).toBeVisible();

    await player.context().close();
  });

  test("第三个账号从房间旁观同一局，拿不到动作", async ({ browser }) => {
    const watcher = await asUser(browser, watcherName, watcherPassword);
    await watcher.goto(`/matches/${matchId}`);

    await expect(watcher.getByText("观战中")).toBeVisible();
    await expect(watcher.getByTestId("my-actions")).toContainText("旁观没有动作可提交");
    await expect(watcher.getByRole("button", { name: "提交" })).toHaveCount(0);
    await expect(watcher.getByTestId("my-secret")).toHaveCount(0);
    await expect(watcher.getByTestId("my-seat")).toHaveCount(0);
    await expect(watcher.getByTestId("seat").first()).toBeVisible();
    // Watching means reading: the shared transcript is there, the seats' own material is not.
    await expect(watcher.getByTestId("match-log")).toContainText("你要说的话：我这东西很甜");

    await watcher.context().close();
  });

  test("管理员在对局运维页暂停、恢复、取消这一局", async ({ page }) => {
    await login(page, "e2e-root", adminPassword);
    await page.getByRole("link", { name: "对局运维" }).click();
    await expect(page).toHaveURL(/\/admin\/matches$/);

    const row = page.getByRole("row", { name: new RegExp(matchId) });
    await expect(row).toBeVisible();

    await row.getByRole("button", { name: "暂停" }).click();
    await expect(row).toContainText("已暂停");
    await row.getByRole("button", { name: "恢复" }).click();
    await expect(row).toContainText("等待行动");

    await page.goto(`/rooms/${roomId}`);
    await expect(page.getByTestId("room-seats")).toBeVisible();

    await page.goto("/admin/matches");
    const again = page.getByRole("row", { name: new RegExp(matchId) });
    await again.getByRole("button", { name: "取消" }).click();
    await page.getByRole("button", { name: "确认取消" }).click();
    await expect(again).toContainText("已取消");

    // A cancelled match frees the table: the same room can be started again.
    await page.goto(`/rooms/${roomId}`);
    await expect(page.getByText("等开局")).toBeVisible();
  });
});
