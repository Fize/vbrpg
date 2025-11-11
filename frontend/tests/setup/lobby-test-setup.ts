/**
 * Lobby Test Setup
 * 
 * Provides test utilities for lobby components including:
 * - Mock Socket.IO client with event replay
 * - Mock API client for room endpoints
 * - Pinia store test harness for lobby state
 */

import { vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import type { Socket } from 'socket.io-client';

/**
 * Mock Socket.IO client with event replay capability
 */
export class MockSocketClient {
  private eventHandlers: Map<string, Array<(...args: any[]) => void>> = new Map();
  private emittedEvents: Array<{ event: string; data: any; timestamp: number }> = [];
  public connected = false;
  public id = 'mock-socket-id';

  /**
   * Register event handler
   */
  on(event: string, handler: (...args: any[]) => void): this {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, []);
    }
    this.eventHandlers.get(event)!.push(handler);
    return this;
  }

  /**
   * Remove event handler
   */
  off(event: string, handler?: (...args: any[]) => void): this {
    if (handler) {
      const handlers = this.eventHandlers.get(event) || [];
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    } else {
      this.eventHandlers.delete(event);
    }
    return this;
  }

  /**
   * Emit event to server (records for assertions)
   */
  emit(event: string, ...args: any[]): this {
    this.emittedEvents.push({
      event,
      data: args,
      timestamp: Date.now()
    });
    return this;
  }

  /**
   * Simulate receiving event from server
   */
  simulateEvent(event: string, ...args: any[]): void {
    const handlers = this.eventHandlers.get(event) || [];
    handlers.forEach(handler => handler(...args));
  }

  /**
   * Connect socket (simulated)
   */
  connect(): this {
    this.connected = true;
    this.simulateEvent('connect');
    return this;
  }

  /**
   * Disconnect socket (simulated)
   */
  disconnect(): this {
    this.connected = false;
    this.simulateEvent('disconnect');
    return this;
  }

  /**
   * Get all emitted events
   */
  getEmittedEvents(): Array<{ event: string; data: any; timestamp: number }> {
    return [...this.emittedEvents];
  }

  /**
   * Get emitted events by name
   */
  getEmittedEventsByName(eventName: string): any[] {
    return this.emittedEvents
      .filter(e => e.event === eventName)
      .map(e => e.data);
  }

  /**
   * Clear emitted events history
   */
  clearEmittedEvents(): void {
    this.emittedEvents = [];
  }

  /**
   * Clear all event handlers
   */
  clearHandlers(): void {
    this.eventHandlers.clear();
  }

  /**
   * Reset mock to initial state
   */
  reset(): void {
    this.clearEmittedEvents();
    this.clearHandlers();
    this.connected = false;
  }
}

/**
 * Mock API client for room endpoints
 */
export class MockRoomApiClient {
  private responses: Map<string, any> = new Map();
  private callHistory: Array<{ method: string; path: string; data?: any; timestamp: number }> = [];

  /**
   * Set mock response for endpoint
   */
  setResponse(endpoint: string, response: any): void {
    this.responses.set(endpoint, response);
  }

  /**
   * Mock GET request
   */
  async get(path: string): Promise<any> {
    this.recordCall('GET', path);
    
    const response = this.responses.get(`GET:${path}`);
    if (response instanceof Error) {
      throw response;
    }
    return response || { success: true, data: null };
  }

  /**
   * Mock POST request
   */
  async post(path: string, data?: any): Promise<any> {
    this.recordCall('POST', path, data);
    
    const response = this.responses.get(`POST:${path}`);
    if (response instanceof Error) {
      throw response;
    }
    return response || { success: true, data: null };
  }

  /**
   * Mock PUT request
   */
  async put(path: string, data?: any): Promise<any> {
    this.recordCall('PUT', path, data);
    
    const response = this.responses.get(`PUT:${path}`);
    if (response instanceof Error) {
      throw response;
    }
    return response || { success: true, data: null };
  }

  /**
   * Mock DELETE request
   */
  async delete(path: string): Promise<any> {
    this.recordCall('DELETE', path);
    
    const response = this.responses.get(`DELETE:${path}`);
    if (response instanceof Error) {
      throw response;
    }
    return response || { success: true, data: null };
  }

  /**
   * Record API call for assertions
   */
  private recordCall(method: string, path: string, data?: any): void {
    this.callHistory.push({
      method,
      path,
      data,
      timestamp: Date.now()
    });
  }

  /**
   * Get all API calls
   */
  getCallHistory(): Array<{ method: string; path: string; data?: any; timestamp: number }> {
    return [...this.callHistory];
  }

  /**
   * Get calls by method and path
   */
  getCalls(method: string, path: string): any[] {
    return this.callHistory
      .filter(c => c.method === method && c.path === path)
      .map(c => c.data);
  }

  /**
   * Clear call history
   */
  clearHistory(): void {
    this.callHistory = [];
  }

  /**
   * Reset mock to initial state
   */
  reset(): void {
    this.responses.clear();
    this.clearHistory();
  }
}

/**
 * Pinia store test harness for lobby state
 */
export interface LobbyStoreTestHarness {
  pinia: ReturnType<typeof createPinia>;
  socketClient: MockSocketClient;
  apiClient: MockRoomApiClient;
}

/**
 * Setup Pinia test environment with mocked dependencies
 */
export function setupLobbyStoreTest(): LobbyStoreTestHarness {
  // Create fresh Pinia instance
  const pinia = createPinia();
  setActivePinia(pinia);

  // Create mock clients
  const socketClient = new MockSocketClient();
  const apiClient = new MockRoomApiClient();

  // Setup default API responses
  apiClient.setResponse('GET:/api/rooms', { 
    success: true, 
    data: [] 
  });

  return {
    pinia,
    socketClient,
    apiClient
  };
}

/**
 * Cleanup test environment
 */
export function cleanupLobbyStoreTest(harness: LobbyStoreTestHarness): void {
  harness.socketClient.reset();
  harness.apiClient.reset();
  // Pinia cleanup is automatic via test isolation
}

/**
 * Wait for async state updates to complete
 */
export async function flushPromises(): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, 0));
}

/**
 * Wait for specific condition with timeout
 */
export async function waitFor(
  condition: () => boolean,
  timeout = 1000,
  checkInterval = 50
): Promise<void> {
  const startTime = Date.now();
  
  while (!condition()) {
    if (Date.now() - startTime > timeout) {
      throw new Error('waitFor timeout exceeded');
    }
    await new Promise(resolve => setTimeout(resolve, checkInterval));
  }
}

/**
 * Create mock lobby data for testing
 */
export function createMockLobbyData(overrides?: Partial<any>) {
  return {
    roomCode: 'TEST1234',
    status: 'waiting',
    maxPlayers: 6,
    minPlayers: 3,
    currentParticipantCount: 1,
    participants: [],
    ownerId: 'owner-123',
    ...overrides
  };
}

/**
 * Create mock participant data
 */
export function createMockParticipant(overrides?: Partial<any>) {
  return {
    id: `participant-${Math.random().toString(36).substr(2, 9)}`,
    playerId: `player-${Math.random().toString(36).substr(2, 9)}`,
    username: 'TestPlayer',
    isAiAgent: false,
    isOwner: false,
    joinTimestamp: new Date().toISOString(),
    ...overrides
  };
}

/**
 * Create mock AI agent participant
 */
export function createMockAiAgent(overrides?: Partial<any>) {
  return createMockParticipant({
    playerId: null,
    isAiAgent: true,
    aiPersonality: 'strategic',
    username: 'AI Agent',
    ...overrides
  });
}
