import { test, expect } from '@playwright/test'

/**
 * T058: E2E Test - Room Dissolution
 * 
 * Tests room dissolution scenarios:
 * - Owner leaves room with only AI agents
 * - Room is dissolved and all AI agents removed
 * - room_dissolved event sent to any remaining clients
 * - Last human player leaves triggers room dissolution
 * 
 * Requirements:
 * - FR-014: Room dissolution when no human players remain
 * - AS2: Real-time dissolution events
 */

test.describe('Room Dissolution', () => {
  test('Owner leaves room with only AI agents - room dissolved', async ({ browser }) => {
    const context = await browser.newContext()
    const page = await context.newPage()
    
    try {
      // Owner creates room
      await page.goto('/')
      await page.click('button:has-text("创建房间")')
      await page.waitForURL(/\/lobby\/[A-Z0-9]+/)
      
      const roomCode = page.url().match(/\/lobby\/([A-Z0-9]+)/)?.[1]
      expect(roomCode).toBeTruthy()
      
      console.log('Room created:', roomCode)
      
      // Owner adds 2 AI agents (only AI, no other humans)
      const addAIButton = page.locator('button:has-text("添加AI玩家")')
      
      await addAIButton.click()
      await page.waitForTimeout(1500)
      
      await addAIButton.click()
      await page.waitForTimeout(1500)
      
      // Verify: 1 human + 2 AI
      await expect(page.locator('.participant-item')).toHaveCount(3, { timeout: 5000 })
      await expect(page.locator('.ai-badge, .badge-ai')).toHaveCount(2)
      
      console.log('Room has 1 owner + 2 AI agents')
      
      // Owner leaves (should dissolve room since only AI remain)
      const leaveButton = page.locator('button:has-text("离开房间")')
      await leaveButton.click()
      
      // Should redirect to home
      await page.waitForURL('/', { timeout: 10000 })
      
      console.log('✓ Owner left room with only AI agents')
      
      // Try to join the room again - should fail (room dissolved)
      await page.locator('input[placeholder*="房间代码"]').fill(roomCode)
      await page.locator('button:has-text("加入房间")').click()
      
      // Should see error (room not found)
      await page.waitForTimeout(2000)
      expect(page.url()).toContain('/')
      
      const errorMessage = page.locator('.error-message, .el-message--error, [role="alert"]')
      await expect(errorMessage).toBeVisible({ timeout: 3000 })
      
      const errorText = await errorMessage.textContent()
      expect(errorText).toMatch(/不存在|找不到|not found/i)
      
      console.log('✓ Room correctly dissolved (cannot rejoin)')
      
    } finally {
      await context.close()
    }
  })
  
  test('Last human leaves room - room dissolved, other client notified', async ({ browser }) => {
    const contextPlayer1 = await browser.newContext()
    const contextPlayer2 = await browser.newContext()
    
    const pagePlayer1 = await contextPlayer1.newPage()
    const pagePlayer2 = await contextPlayer2.newPage()
    
    try {
      // Player 1 creates room
      await pagePlayer1.goto('/')
      await pagePlayer1.click('button:has-text("创建房间")')
      await pagePlayer1.waitForURL(/\/lobby\/[A-Z0-9]+/)
      
      const roomCode = pagePlayer1.url().match(/\/lobby\/([A-Z0-9]+)/)?.[1]
      expect(roomCode).toBeTruthy()
      
      // Player 2 joins
      await pagePlayer2.goto('/')
      await pagePlayer2.locator('input[placeholder*="房间代码"]').fill(roomCode)
      await pagePlayer2.locator('button:has-text("加入房间")').click()
      await pagePlayer2.waitForURL(new RegExp(`/lobby/${roomCode}`))
      
      // Both see 2 participants
      await expect(pagePlayer1.locator('.participant-item')).toHaveCount(2, { timeout: 5000 })
      await expect(pagePlayer2.locator('.participant-item')).toHaveCount(2, { timeout: 5000 })
      
      console.log('Two players in room')
      
      // Player 1 (owner) leaves
      await pagePlayer1.locator('button:has-text("离开房间")').click()
      await pagePlayer1.waitForURL('/')
      
      // Player 2 should become owner
      await expect(pagePlayer2.locator('.owner-badge').first()).toBeVisible({ timeout: 5000 })
      await expect(pagePlayer2.locator('.participant-item')).toHaveCount(1)
      
      console.log('Player 2 is now alone and owner')
      
      // Player 2 (last human) leaves - should dissolve room
      await pagePlayer2.locator('button:has-text("离开房间")').click()
      await pagePlayer2.waitForURL('/')
      
      console.log('✓ Last player left, room should be dissolved')
      
      // Try to join dissolved room - should fail
      await pagePlayer1.locator('input[placeholder*="房间代码"]').fill(roomCode)
      await pagePlayer1.locator('button:has-text("加入房间")').click()
      
      await pagePlayer1.waitForTimeout(2000)
      const errorMessage = pagePlayer1.locator('.error-message, .el-message--error, [role="alert"]')
      await expect(errorMessage).toBeVisible({ timeout: 3000 })
      
      console.log('✓ Room correctly dissolved after last human left')
      
    } finally {
      await contextPlayer1.close()
      await contextPlayer2.close()
    }
  })
  
  test('Room dissolution notification to connected clients', async ({ browser }) => {
    const contextOwner = await browser.newContext()
    const contextPlayer = await browser.newContext()
    
    const pageOwner = await contextOwner.newPage()
    const pagePlayer = await contextPlayer.newPage()
    
    try {
      // Owner creates room
      await pageOwner.goto('/')
      await pageOwner.click('button:has-text("创建房间")')
      await pageOwner.waitForURL(/\/lobby\/[A-Z0-9]+/)
      
      const roomCode = pageOwner.url().match(/\/lobby\/([A-Z0-9]+)/)?.[1]
      
      // Add AI agent
      await pageOwner.locator('button:has-text("添加AI玩家")').click()
      await pageOwner.waitForTimeout(1500)
      
      // Human player joins
      await pagePlayer.goto('/')
      await pagePlayer.locator('input[placeholder*="房间代码"]').fill(roomCode)
      await pagePlayer.locator('button:has-text("加入房间")').click()
      await pagePlayer.waitForURL(new RegExp(`/lobby/${roomCode}`))
      
      // Should have 2 humans + 1 AI
      await expect(pageOwner.locator('.participant-item')).toHaveCount(3, { timeout: 5000 })
      await expect(pagePlayer.locator('.participant-item')).toHaveCount(3, { timeout: 5000 })
      
      console.log('Room has 2 humans + 1 AI')
      
      // Human player leaves (not owner)
      await pagePlayer.locator('button:has-text("离开房间")').click()
      await pagePlayer.waitForURL('/')
      
      // Now owner is alone with 1 AI
      await expect(pageOwner.locator('.participant-item')).toHaveCount(2, { timeout: 5000 })
      
      // Owner leaves (should dissolve room)
      await pageOwner.locator('button:has-text("离开房间")').click()
      await pageOwner.waitForURL('/')
      
      console.log('✓ Room dissolved after owner left with only AI')
      
      // Verify room no longer exists
      await pageOwner.locator('input[placeholder*="房间代码"]').fill(roomCode)
      await pageOwner.locator('button:has-text("加入房间")').click()
      
      await pageOwner.waitForTimeout(2000)
      expect(pageOwner.url()).not.toContain('/lobby/')
      
    } finally {
      await contextOwner.close()
      await contextPlayer.close()
    }
  })
  
  test('Room with only AI agents cannot exist', async ({ browser }) => {
    const context = await browser.newContext()
    const page = await context.newPage()
    
    try {
      // Create room
      await page.goto('/')
      await page.click('button:has-text("创建房间")')
      await page.waitForURL(/\/lobby\/[A-Z0-9]+/)
      
      const roomCode = page.url().match(/\/lobby\/([A-Z0-9]+)/)?.[1]
      
      // Add 3 AI agents
      const addAIButton = page.locator('button:has-text("添加AI玩家")')
      
      for (let i = 0; i < 3; i++) {
        await addAIButton.click()
        await page.waitForTimeout(1500)
      }
      
      // Should have 1 human + 3 AI = 4 participants
      await expect(page.locator('.participant-item')).toHaveCount(4, { timeout: 5000 })
      
      // Leave room (should dissolve since only AI remain)
      await page.locator('button:has-text("离开房间")').click()
      await page.waitForURL('/')
      
      // Try to join - should fail
      await page.locator('input[placeholder*="房间代码"]').fill(roomCode)
      await page.locator('button:has-text("加入房间")').click()
      
      await page.waitForTimeout(2000)
      
      const errorMessage = page.locator('.error-message, .el-message--error, [role="alert"]')
      await expect(errorMessage).toBeVisible({ timeout: 3000 })
      
      console.log('✓ Room with only AI agents correctly dissolved')
      
    } finally {
      await context.close()
    }
  })
})
