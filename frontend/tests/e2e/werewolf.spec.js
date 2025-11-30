import { test, expect } from '@playwright/test'

/**
 * T06: 狼人杀游戏 E2E 测试
 * 
 * 测试狼人杀游戏的完整启动流程
 * - 选择狼人杀游戏模式
 * - 快速开始游戏
 * - 游戏界面渲染
 */

test.describe('狼人杀游戏启动流程', () => {
  // 跳过实际的 E2E 测试（需要后端服务运行）
  // 这些测试仅在集成测试环境中运行
  
  test.skip('从首页选择狼人杀游戏类型', async ({ page }) => {
    // 1. 导航到首页
    await page.goto('/')
    await expect(page).toHaveTitle(/VBRPG/)
    
    // 2. 查找狼人杀游戏卡片
    const werewolfCard = page.locator('.game-card:has-text("狼人杀")')
    await expect(werewolfCard).toBeVisible({ timeout: 5000 })
    
    // 3. 点击狼人杀游戏卡片
    await werewolfCard.click()
    
    // 4. 应该显示模式选择对话框
    const modeDialog = page.locator('.werewolf-mode-dialog')
    await expect(modeDialog).toBeVisible({ timeout: 3000 })
    
    // 5. 验证对话框标题
    await expect(modeDialog.locator('.el-dialog__title')).toHaveText('选择游戏模式')
  })

  test.skip('选择玩家模式并开始游戏', async ({ page }) => {
    // 1. 导航到首页
    await page.goto('/')
    
    // 2. 点击狼人杀游戏
    const werewolfCard = page.locator('.game-card:has-text("狼人杀")')
    await werewolfCard.click()
    
    // 3. 等待模式选择对话框
    const modeDialog = page.locator('.werewolf-mode-dialog')
    await expect(modeDialog).toBeVisible({ timeout: 3000 })
    
    // 4. 选择玩家模式（默认已选中）
    const playerModeCard = modeDialog.locator('.mode-card:has-text("玩家模式")')
    await expect(playerModeCard).toHaveClass(/active/)
    
    // 5. 选择角色（可选）
    const roleSelector = modeDialog.locator('.role-selector')
    if (await roleSelector.isVisible()) {
      // 选择狼人角色
      const werewolfRole = roleSelector.locator('.role-option:has-text("狼人")')
      await werewolfRole.click()
    }
    
    // 6. 点击开始游戏
    const startButton = modeDialog.locator('button:has-text("开始游戏")')
    await expect(startButton).toBeEnabled()
    await startButton.click()
    
    // 7. 等待游戏界面加载
    await expect(page.locator('.werewolf-game-view')).toBeVisible({ timeout: 10000 })
  })

  test.skip('选择观战模式并开始游戏', async ({ page }) => {
    // 1. 导航到首页
    await page.goto('/')
    
    // 2. 点击狼人杀游戏
    const werewolfCard = page.locator('.game-card:has-text("狼人杀")')
    await werewolfCard.click()
    
    // 3. 等待模式选择对话框
    const modeDialog = page.locator('.werewolf-mode-dialog')
    await expect(modeDialog).toBeVisible({ timeout: 3000 })
    
    // 4. 选择观战模式
    const spectatorModeCard = modeDialog.locator('.mode-card:has-text("观战模式")')
    await spectatorModeCard.click()
    await expect(spectatorModeCard).toHaveClass(/active/)
    
    // 5. 点击开始游戏
    const startButton = modeDialog.locator('button:has-text("开始游戏")')
    await expect(startButton).toBeEnabled()
    await startButton.click()
    
    // 6. 等待游戏界面加载
    await expect(page.locator('.werewolf-game-view')).toBeVisible({ timeout: 10000 })
  })

  test.skip('取消游戏模式选择', async ({ page }) => {
    // 1. 导航到首页
    await page.goto('/')
    
    // 2. 点击狼人杀游戏
    const werewolfCard = page.locator('.game-card:has-text("狼人杀")')
    await werewolfCard.click()
    
    // 3. 等待模式选择对话框
    const modeDialog = page.locator('.werewolf-mode-dialog')
    await expect(modeDialog).toBeVisible({ timeout: 3000 })
    
    // 4. 点击取消按钮
    const cancelButton = modeDialog.locator('button:has-text("取消")')
    await cancelButton.click()
    
    // 5. 对话框应该关闭
    await expect(modeDialog).not.toBeVisible({ timeout: 3000 })
    
    // 6. 应该仍然在首页
    await expect(page).toHaveURL('/')
  })
})

test.describe('狼人杀游戏界面', () => {
  test.skip('游戏界面包含必要组件', async ({ page }) => {
    // 假设已经进入游戏（通过 quick-start API）
    // 这个测试需要 mock 后端或使用测试环境
    
    // 验证座位圆环
    await expect(page.locator('.seat-circle')).toBeVisible()
    
    // 验证游戏日志
    await expect(page.locator('.game-log')).toBeVisible()
    
    // 验证主持人公告区域
    await expect(page.locator('.host-announcement')).toBeVisible()
    
    // 验证阶段指示器
    await expect(page.locator('.phase-indicator')).toBeVisible()
  })

  test.skip('玩家座位正确显示', async ({ page }) => {
    // 验证 10 个座位都显示
    const seats = page.locator('.player-seat')
    await expect(seats).toHaveCount(10)
    
    // 验证玩家自己的座位有高亮
    const selfSeat = page.locator('.player-seat.is-self')
    await expect(selfSeat).toBeVisible()
  })

  test.skip('夜晚行动面板显示', async ({ page }) => {
    // 假设是夜晚阶段且玩家是特殊角色
    const nightPanel = page.locator('.night-action-panel')
    
    // 如果是夜晚且有行动权，面板应该可见
    // 这取决于当前游戏状态
    if (await nightPanel.isVisible()) {
      // 验证面板包含行动按钮
      const actionButton = nightPanel.locator('.action-button')
      await expect(actionButton).toBeVisible()
    }
  })

  test.skip('投票面板显示', async ({ page }) => {
    // 假设是投票阶段
    const votePanel = page.locator('.vote-panel')
    
    if (await votePanel.isVisible()) {
      // 验证可以看到投票选项
      const voteOptions = votePanel.locator('.vote-option')
      await expect(voteOptions.first()).toBeVisible()
    }
  })
})

test.describe('游戏日志功能', () => {
  test.skip('日志自动滚动到底部', async ({ page }) => {
    const gameLog = page.locator('.game-log')
    await expect(gameLog).toBeVisible()
    
    // 获取初始滚动位置
    const initialScrollTop = await gameLog.locator('.log-content').evaluate(
      el => el.scrollTop
    )
    
    // 等待新日志添加（可能需要等待游戏进行）
    await page.waitForTimeout(5000)
    
    // 验证滚动位置更新
    const newScrollTop = await gameLog.locator('.log-content').evaluate(
      el => el.scrollTop
    )
    
    // 如果有新日志，滚动位置应该改变
    // 注意：这个断言可能需要根据实际情况调整
  })

  test.skip('流式输出显示打字光标', async ({ page }) => {
    // 等待流式输出开始
    const streamingEntry = page.locator('.log-entry.is-streaming')
    
    if (await streamingEntry.isVisible({ timeout: 10000 })) {
      // 验证打字光标存在
      const cursor = streamingEntry.locator('.typing-cursor')
      await expect(cursor).toBeVisible()
    }
  })
})

test.describe('主持人公告', () => {
  test.skip('公告正确显示', async ({ page }) => {
    const announcement = page.locator('.host-announcement')
    await expect(announcement).toBeVisible()
    
    // 验证公告包含主持人标识
    await expect(announcement.locator('.host-name')).toHaveText('主持人')
  })

  test.skip('公告完成后可关闭', async ({ page }) => {
    const announcement = page.locator('.host-announcement:not(.is-streaming)')
    
    if (await announcement.isVisible()) {
      const closeButton = announcement.locator('.close-btn')
      
      if (await closeButton.isVisible()) {
        await closeButton.click()
        // 验证公告被关闭或隐藏
      }
    }
  })
})

test.describe('游戏状态同步', () => {
  test.skip('WebSocket 连接建立', async ({ page }) => {
    // 监听 WebSocket 连接
    const wsPromise = page.waitForEvent('websocket')
    
    // 导航到游戏页面
    await page.goto('/werewolf/game/TEST123')
    
    const ws = await wsPromise
    
    // 验证 WebSocket URL
    expect(ws.url()).toContain('socket.io')
  })

  test.skip('实时状态更新', async ({ page }) => {
    // 这个测试需要模拟后端推送状态更新
    // 可以通过观察页面元素变化来验证
    
    const phaseIndicator = page.locator('.phase-indicator')
    const initialPhase = await phaseIndicator.textContent()
    
    // 等待状态更新
    await page.waitForTimeout(10000)
    
    // 验证阶段可能已变化（取决于游戏进行）
  })
})
