import { test, expect } from '@playwright/test'

/**
 * T057: E2E Test - Ownership Transfer
 * 
 * Tests ownership transfer scenarios:
 * - Owner leaves room with 2+ other humans present
 * - Ownership transfers to earliest-joined human
 * - All clients receive ownership_transferred event
 * - New owner sees owner badge and controls
 * 
 * Requirements:
 * - FR-014: Automatic ownership transfer on owner leave
 * - AS2: Real-time ownership update events
 */

test.describe('Ownership Transfer', () => {
  test('Owner leaves room, ownership transfers to earliest human', async ({ browser }) => {
    // Create three contexts: owner, player2 (should become owner), player3
    const contextOwner = await browser.newContext()
    const contextPlayer2 = await browser.newContext()
    const contextPlayer3 = await browser.newContext()
    
    const pageOwner = await contextOwner.newPage()
    const pagePlayer2 = await contextPlayer2.newPage()
    const pagePlayer3 = await contextPlayer3.newPage()
    
    try {
      // Original owner creates room
      await pageOwner.goto('/')
      await pageOwner.click('button:has-text("创建房间")')
      await pageOwner.waitForURL(/\/lobby\/[A-Z0-9]+/)
      
      const roomCode = pageOwner.url().match(/\/lobby\/([A-Z0-9]+)/)?.[1]
      expect(roomCode).toBeTruthy()
      
      console.log('Room created by owner:', roomCode)
      
      // Owner should see owner badge and controls
      await expect(pageOwner.locator('.owner-badge').first()).toBeVisible()
      await expect(pageOwner.locator('button:has-text("添加AI玩家")')).toBeVisible()
      
      // Player 2 joins (will become new owner)
      await pagePlayer2.goto('/')
      await pagePlayer2.locator('input[placeholder*="房间代码"]').fill(roomCode)
      await pagePlayer2.locator('button:has-text("加入房间")').click()
      await pagePlayer2.waitForURL(new RegExp(`/lobby/${roomCode}`))
      
      console.log('Player 2 joined')
      
      // Player 2 should NOT see owner badge or AI controls yet
      await expect(pagePlayer2.locator('.participant-item')).toHaveCount(2, { timeout: 5000 })
      const player2OwnBadge = pagePlayer2.locator('.participant-item').last().locator('.owner-badge')
      await expect(player2OwnBadge).not.toBeVisible()
      await expect(pagePlayer2.locator('button:has-text("添加AI玩家")')).not.toBeVisible()
      
      // Small delay to ensure Player 2 joined first
      await pagePlayer2.waitForTimeout(1000)
      
      // Player 3 joins
      await pagePlayer3.goto('/')
      await pagePlayer3.locator('input[placeholder*="房间代码"]').fill(roomCode)
      await pagePlayer3.locator('button:has-text("加入房间")').click()
      await pagePlayer3.waitForURL(new RegExp(`/lobby/${roomCode}`))
      
      console.log('Player 3 joined')
      
      // All players should see 3 participants
      await expect(pageOwner.locator('.participant-item')).toHaveCount(3, { timeout: 5000 })
      await expect(pagePlayer2.locator('.participant-item')).toHaveCount(3, { timeout: 5000 })
      await expect(pagePlayer3.locator('.participant-item')).toHaveCount(3, { timeout: 5000 })
      
      // Record timestamp before owner leaves
      const beforeLeaveTime = Date.now()
      
      // Original owner leaves room
      const leaveButton = pageOwner.locator('button:has-text("离开房间")')
      await expect(leaveButton).toBeVisible()
      await leaveButton.click()
      
      // Owner should be redirected to home
      await pageOwner.waitForURL('/', { timeout: 10000 })
      console.log('Original owner left room')
      
      // Player 2 (earliest-joined) should become new owner
      // Check for owner badge
      const player2NewOwnerBadge = pagePlayer2.locator('.owner-badge').first()
      await expect(player2NewOwnerBadge).toBeVisible({ timeout: 5000 })
      await expect(player2NewOwnerBadge).toHaveText('房主')
      
      // Player 2 should now see AI management controls
      await expect(pagePlayer2.locator('button:has-text("添加AI玩家")')).toBeVisible({ timeout: 3000 })
      
      console.log('✓ Player 2 (earliest-joined) became new owner')
      
      // Player 3 should see Player 2 as owner
      const player3ViewOwnerBadge = pagePlayer3.locator('.owner-badge')
      await expect(player3ViewOwnerBadge).toHaveCount(1, { timeout: 5000 })
      
      // Player 3 should NOT see AI controls (not owner)
      await expect(pagePlayer3.locator('button:has-text("添加AI玩家")')).not.toBeVisible()
      
      console.log('✓ Player 3 sees Player 2 as new owner')
      
      // Both remaining players should see 2 participants
      await expect(pagePlayer2.locator('.participant-item')).toHaveCount(2, { timeout: 5000 })
      await expect(pagePlayer3.locator('.participant-item')).toHaveCount(2, { timeout: 5000 })
      
      // Verify real-time update latency
      const afterTransferTime = Date.now()
      const latency = afterTransferTime - beforeLeaveTime
      console.log('Ownership transfer latency:', latency, 'ms')
      expect(latency).toBeLessThan(5000) // Allow 5s for E2E
      
      console.log('✓ Ownership transfer completed in real-time')
      
    } finally {
      await contextOwner.close()
      await contextPlayer2.close()
      await contextPlayer3.close()
    }
  })
  
  test('Ownership transfers multiple times as players leave', async ({ browser }) => {
    // Create four contexts
    const contexts = []
    const pages = []
    
    for (let i = 0; i < 4; i++) {
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
      
      // Players 2, 3, 4 join in sequence
      for (let i = 1; i < 4; i++) {
        await pages[i].goto('/')
        await pages[i].locator('input[placeholder*="房间代码"]').fill(roomCode)
        await pages[i].locator('button:has-text("加入房间")').click()
        await pages[i].waitForURL(new RegExp(`/lobby/${roomCode}`))
        await pages[i].waitForTimeout(500) // Small delay between joins
      }
      
      // All should see 4 participants
      for (let i = 0; i < 4; i++) {
        await expect(pages[i].locator('.participant-item')).toHaveCount(4, { timeout: 5000 })
      }
      
      console.log('All 4 players in room')
      
      // Player 1 (owner) leaves
      await pages[0].locator('button:has-text("离开房间")').click()
      await pages[0].waitForURL('/')
      
      // Player 2 should become owner
      await expect(pages[1].locator('.owner-badge').first()).toBeVisible({ timeout: 5000 })
      await expect(pages[1].locator('button:has-text("添加AI玩家")')).toBeVisible()
      
      console.log('✓ Player 2 became owner after Player 1 left')
      
      // Player 2 (now owner) leaves
      await pages[1].locator('button:has-text("离开房间")').click()
      await pages[1].waitForURL('/')
      
      // Player 3 should become owner
      await expect(pages[2].locator('.owner-badge').first()).toBeVisible({ timeout: 5000 })
      await expect(pages[2].locator('button:has-text("添加AI玩家")')).toBeVisible()
      
      console.log('✓ Player 3 became owner after Player 2 left')
      
      // Final check: Player 4 sees Player 3 as owner
      await expect(pages[3].locator('.owner-badge')).toHaveCount(1)
      await expect(pages[3].locator('button:has-text("添加AI玩家")')).not.toBeVisible()
      
      console.log('✓ Multiple ownership transfers successful')
      
    } finally {
      for (const context of contexts) {
        await context.close()
      }
    }
  })
  
  test('Ownership does NOT transfer to AI agents', async ({ browser }) => {
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
      
      // Owner adds 2 AI agents
      const addAIButton = pageOwner.locator('button:has-text("添加AI玩家")')
      await addAIButton.click()
      await pageOwner.waitForTimeout(1500)
      await addAIButton.click()
      await pageOwner.waitForTimeout(1500)
      
      // Human player joins
      await pagePlayer.goto('/')
      await pagePlayer.locator('input[placeholder*="房间代码"]').fill(roomCode)
      await pagePlayer.locator('button:has-text("加入房间")').click()
      await pagePlayer.waitForURL(new RegExp(`/lobby/${roomCode}`))
      
      // Should have 1 owner + 2 AI + 1 human = 4 participants
      await expect(pageOwner.locator('.participant-item')).toHaveCount(4, { timeout: 5000 })
      
      // Owner leaves
      await pageOwner.locator('button:has-text("离开房间")').click()
      await pageOwner.waitForURL('/')
      
      // Human player should become owner (NOT AI)
      await expect(pagePlayer.locator('.owner-badge').first()).toBeVisible({ timeout: 5000 })
      await expect(pagePlayer.locator('button:has-text("添加AI玩家")')).toBeVisible()
      
      // Should still have AI agents and human player
      await expect(pagePlayer.locator('.participant-item')).toHaveCount(3, { timeout: 5000 })
      await expect(pagePlayer.locator('.ai-badge, .badge-ai')).toHaveCount(2)
      
      console.log('✓ Ownership correctly transferred to human, not AI')
      
    } finally {
      await contextOwner.close()
      await contextPlayer.close()
    }
  })
})
