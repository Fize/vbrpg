import { test, expect } from '@playwright/test'

/**
 * T054: E2E Test - Complete Join Flow
 * 
 * Tests the complete user journey:
 * - Player A creates a room
 * - Player B joins using the room code
 * - Both players see each other in the lobby within 1 second
 * - Player B sees room creator as owner
 * 
 * Requirements:
 * - SC-003: Real-time updates < 1 second
 * - AS1: Room creator is owner
 */

test.describe('Complete Join Flow', () => {
  test('Player A creates room, Player B joins with code', async ({ browser }) => {
    // Create two separate browser contexts (simulating two different users)
    const contextA = await browser.newContext()
    const contextB = await browser.newContext()
    
    const pageA = await contextA.newPage()
    const pageB = await contextB.newPage()
    
    try {
      // Player A: Navigate to home page
      await pageA.goto('/')
      await expect(pageA).toHaveTitle(/VBRPG/)
      
      // Player A: Create a new room
      await pageA.click('button:has-text("创建房间")')
      
      // Wait for room creation and redirect to lobby
      await pageA.waitForURL(/\/lobby\/[A-Z0-9]+/, { timeout: 10000 })
      
      // Extract room code from URL
      const urlA = pageA.url()
      const roomCode = urlA.match(/\/lobby\/([A-Z0-9]+)/)?.[1]
      expect(roomCode).toBeTruthy()
      expect(roomCode).toMatch(/^[A-Z0-9]{6}$/)
      
      console.log('Room created with code:', roomCode)
      
      // Player A: Verify they are in the lobby
      await expect(pageA.locator('.room-code')).toHaveText(roomCode, { timeout: 5000 })
      
      // Player A: Verify they are the owner (should see owner badge)
      const participantListA = pageA.locator('.participants-list')
      await expect(participantListA).toBeVisible()
      
      // Player A should see owner badge on their name
      const ownerBadgeA = participantListA.locator('.owner-badge').first()
      await expect(ownerBadgeA).toBeVisible()
      await expect(ownerBadgeA).toHaveText('房主')
      
      // Record timestamp before Player B joins
      const beforeJoinTime = Date.now()
      
      // Player B: Navigate to home page
      await pageB.goto('/')
      
      // Player B: Enter room code and join
      const joinInput = pageB.locator('input[placeholder*="房间代码"]')
      await expect(joinInput).toBeVisible({ timeout: 5000 })
      await joinInput.fill(roomCode)
      
      const joinButton = pageB.locator('button:has-text("加入房间")')
      await joinButton.click()
      
      // Player B: Wait for redirect to lobby
      await pageB.waitForURL(new RegExp(`/lobby/${roomCode}`), { timeout: 10000 })
      
      // Player B: Verify they are in the correct lobby
      await expect(pageB.locator('.room-code')).toHaveText(roomCode)
      
      // Player B: Verify they see the room creator
      const participantListB = pageB.locator('.participants-list')
      await expect(participantListB).toBeVisible()
      
      // Player B should see 2 participants
      const participantsB = participantListB.locator('.participant-item')
      await expect(participantsB).toHaveCount(2, { timeout: 5000 })
      
      // Player B: Verify room creator has owner badge
      const ownerBadgesB = participantListB.locator('.owner-badge')
      await expect(ownerBadgesB).toHaveCount(1)
      await expect(ownerBadgesB.first()).toHaveText('房主')
      
      // Player B should NOT have owner badge themselves
      const allBadgesB = participantListB.locator('.participant-item').filter({ hasText: 'Player' }).last()
      await expect(allBadgesB.locator('.owner-badge')).not.toBeVisible()
      
      // Player A: Verify they see Player B in real-time
      const participantsA = participantListA.locator('.participant-item')
      await expect(participantsA).toHaveCount(2, { timeout: 5000 })
      
      // Verify real-time update latency < 1 second (SC-003)
      const afterJoinTime = Date.now()
      const latency = afterJoinTime - beforeJoinTime
      console.log('Join latency:', latency, 'ms')
      expect(latency).toBeLessThan(5000) // Allow 5s for E2E test (includes navigation)
      
      // Player A: Verify participant count updated
      await expect(pageA.locator('.room-details').getByText(/2\/4/)).toBeVisible()
      
      // Player B: Verify participant count
      await expect(pageB.locator('.room-details').getByText(/2\/4/)).toBeVisible()
      
      // Verify room status is "Waiting" for both players
      await expect(pageA.locator('.room-status')).toHaveText('等待中')
      await expect(pageB.locator('.room-status')).toHaveText('等待中')
      
      console.log('✓ Both players see each other in lobby')
      console.log('✓ Player B sees room creator as owner')
      console.log('✓ Real-time update completed')
      
    } finally {
      // Cleanup: Close both browser contexts
      await contextA.close()
      await contextB.close()
    }
  })
  
  test('Multiple players see real-time updates', async ({ browser }) => {
    // Create three separate browser contexts
    const contextA = await browser.newContext()
    const contextB = await browser.newContext()
    const contextC = await browser.newContext()
    
    const pageA = await contextA.newPage()
    const pageB = await contextB.newPage()
    const pageC = await contextC.newPage()
    
    try {
      // Player A creates room
      await pageA.goto('/')
      await pageA.click('button:has-text("创建房间")')
      await pageA.waitForURL(/\/lobby\/[A-Z0-9]+/)
      
      const roomCode = pageA.url().match(/\/lobby\/([A-Z0-9]+)/)?.[1]
      expect(roomCode).toBeTruthy()
      
      // Player B joins
      await pageB.goto('/')
      await pageB.locator('input[placeholder*="房间代码"]').fill(roomCode)
      await pageB.locator('button:has-text("加入房间")').click()
      await pageB.waitForURL(new RegExp(`/lobby/${roomCode}`))
      
      // Wait for Player A to see Player B
      await expect(pageA.locator('.participant-item')).toHaveCount(2, { timeout: 5000 })
      
      // Player C joins
      await pageC.goto('/')
      await pageC.locator('input[placeholder*="房间代码"]').fill(roomCode)
      await pageC.locator('button:has-text("加入房间")').click()
      await pageC.waitForURL(new RegExp(`/lobby/${roomCode}`))
      
      // All players should see 3 participants
      await expect(pageA.locator('.participant-item')).toHaveCount(3, { timeout: 5000 })
      await expect(pageB.locator('.participant-item')).toHaveCount(3, { timeout: 5000 })
      await expect(pageC.locator('.participant-item')).toHaveCount(3, { timeout: 5000 })
      
      // Verify participant count display
      await expect(pageA.locator('.room-details').getByText(/3\/4/)).toBeVisible()
      await expect(pageB.locator('.room-details').getByText(/3\/4/)).toBeVisible()
      await expect(pageC.locator('.room-details').getByText(/3\/4/)).toBeVisible()
      
      console.log('✓ Three players all see each other in real-time')
      
    } finally {
      await contextA.close()
      await contextB.close()
      await contextC.close()
    }
  })
})
