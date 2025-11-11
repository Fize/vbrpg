import { test, expect } from '@playwright/test'

/**
 * T055: E2E Test - Room Capacity
 * 
 * Tests room capacity limits:
 * - Fill room to max capacity (4 players)
 * - Attempt to join when room is full
 * - Verify error message "Room is full" displayed
 * 
 * Requirements:
 * - AS3: Room full error handling
 * - FR-004: Max 4 players per room
 */

test.describe('Room Capacity', () => {
  test('Fill room to max capacity and reject additional joins', async ({ browser }) => {
    // Create 5 separate browser contexts (4 players + 1 rejected)
    const contexts = []
    const pages = []
    
    for (let i = 0; i < 5; i++) {
      contexts[i] = await browser.newContext()
      pages[i] = await contexts[i].newPage()
    }
    
    try {
      // Player 1 creates room
      await pages[0].goto('/')
      await pages[0].click('button:has-text("创建房间")')
      await pages[0].waitForURL(/\/lobby\/[A-Z0-9]+/)
      
      const roomCode = pages[0].url().match(/\/lobby\/([A-Z0-9]+)/)?.[1]
      expect(roomCode).toBeTruthy()
      
      console.log('Room created with code:', roomCode)
      
      // Verify room shows 1/4 participants
      await expect(pages[0].locator('.room-details').getByText(/1\/4/)).toBeVisible()
      
      // Players 2, 3, 4 join successfully
      for (let i = 1; i < 4; i++) {
        await pages[i].goto('/')
        await pages[i].locator('input[placeholder*="房间代码"]').fill(roomCode)
        await pages[i].locator('button:has-text("加入房间")').click()
        await pages[i].waitForURL(new RegExp(`/lobby/${roomCode}`), { timeout: 10000 })
        
        console.log(`Player ${i + 1} joined successfully`)
        
        // Verify participant count increased
        const expectedCount = i + 1
        await expect(pages[i].locator('.room-details').getByText(new RegExp(`${expectedCount}/4`))).toBeVisible({ timeout: 5000 })
      }
      
      // Verify all 4 players see 4/4 participants
      for (let i = 0; i < 4; i++) {
        await expect(pages[i].locator('.participant-item')).toHaveCount(4, { timeout: 5000 })
        await expect(pages[i].locator('.room-details').getByText(/4\/4/)).toBeVisible()
      }
      
      console.log('Room is now full (4/4 participants)')
      
      // Player 5 attempts to join (should fail)
      await pages[4].goto('/')
      await pages[4].locator('input[placeholder*="房间代码"]').fill(roomCode)
      await pages[4].locator('button:has-text("加入房间")').click()
      
      // Should see error message instead of redirecting to lobby
      // Wait a bit to ensure we don't redirect
      await pages[4].waitForTimeout(2000)
      
      // Should still be on home page (not redirected)
      expect(pages[4].url()).toContain('/')
      expect(pages[4].url()).not.toContain('/lobby/')
      
      // Should see error message
      const errorMessage = pages[4].locator('.error-message, .el-message--error, [role="alert"]')
      await expect(errorMessage).toBeVisible({ timeout: 3000 })
      
      const errorText = await errorMessage.textContent()
      expect(errorText).toMatch(/房间已满|已满|满员|full/i)
      
      console.log('✓ Player 5 correctly rejected with "Room is full" error')
      
      // Verify existing players still see 4/4 (no phantom 5th player)
      for (let i = 0; i < 4; i++) {
        await expect(pages[i].locator('.participant-item')).toHaveCount(4)
        await expect(pages[i].locator('.room-details').getByText(/4\/4/)).toBeVisible()
      }
      
    } finally {
      // Cleanup: Close all browser contexts
      for (const context of contexts) {
        await context.close()
      }
    }
  })
  
  test('Room capacity enforced with AI agents', async ({ browser }) => {
    const contextA = await browser.newContext()
    const contextB = await browser.newContext()
    
    const pageA = await contextA.newPage()
    const pageB = await contextB.newPage()
    
    try {
      // Player A creates room
      await pageA.goto('/')
      await pageA.click('button:has-text("创建房间")')
      await pageA.waitForURL(/\/lobby\/[A-Z0-9]+/)
      
      const roomCode = pageA.url().match(/\/lobby\/([A-Z0-9]+)/)?.[1]
      expect(roomCode).toBeTruthy()
      
      // Player A adds 3 AI agents (1 human + 3 AI = 4/4)
      const addAIButton = pageA.locator('button:has-text("添加AI玩家")')
      
      for (let i = 0; i < 3; i++) {
        await expect(addAIButton).toBeVisible()
        await expect(addAIButton).toBeEnabled()
        await addAIButton.click()
        
        // Wait for AI to appear in participant list
        await pageA.waitForTimeout(1000)
      }
      
      // Verify room is now 4/4
      await expect(pageA.locator('.participant-item')).toHaveCount(4, { timeout: 5000 })
      await expect(pageA.locator('.room-details').getByText(/4\/4/)).toBeVisible()
      
      // Add AI button should now be disabled
      await expect(addAIButton).toBeDisabled()
      
      console.log('Room full with 1 human + 3 AI agents')
      
      // Player B attempts to join (should fail - room full)
      await pageB.goto('/')
      await pageB.locator('input[placeholder*="房间代码"]').fill(roomCode)
      await pageB.locator('button:has-text("加入房间")').click()
      
      // Should see error message
      await pageB.waitForTimeout(2000)
      expect(pageB.url()).not.toContain('/lobby/')
      
      const errorMessage = pageB.locator('.error-message, .el-message--error, [role="alert"]')
      await expect(errorMessage).toBeVisible({ timeout: 3000 })
      
      console.log('✓ Human player correctly rejected when room full with AI agents')
      
    } finally {
      await contextA.close()
      await contextB.close()
    }
  })
})
