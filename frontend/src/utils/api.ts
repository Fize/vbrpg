/**
 * API utilities with auto-retry logic
 */

interface RetryConfig {
  maxRetries?: number
  retryDelay?: number
  backoffMultiplier?: number
  retryableStatuses?: number[]
  onRetry?: (attempt: number, error: any) => void
}

const DEFAULT_RETRY_CONFIG: Required<RetryConfig> = {
  maxRetries: 3,
  retryDelay: 1000,
  backoffMultiplier: 2,
  retryableStatuses: [408, 429, 500, 502, 503, 504],
  onRetry: () => {}
}

/**
 * Sleep for specified milliseconds
 */
const sleep = (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * Check if error is retryable
 */
const isRetryableError = (error: any, retryableStatuses: number[]): boolean => {
  // Network errors
  if (!error.response && error.request) {
    return true
  }
  
  // HTTP status codes
  if (error.response?.status) {
    return retryableStatuses.includes(error.response.status)
  }
  
  return false
}

/**
 * Fetch with automatic retry logic
 */
export async function fetchWithRetry<T>(
  fetchFn: () => Promise<T>,
  config: RetryConfig = {}
): Promise<T> {
  const {
    maxRetries,
    retryDelay,
    backoffMultiplier,
    retryableStatuses,
    onRetry
  } = { ...DEFAULT_RETRY_CONFIG, ...config }
  
  let lastError: any
  let currentDelay = retryDelay
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fetchFn()
    } catch (error) {
      lastError = error
      
      // Don't retry if max attempts reached
      if (attempt === maxRetries) {
        break
      }
      
      // Don't retry if error is not retryable
      if (!isRetryableError(error, retryableStatuses)) {
        break
      }
      
      // Call retry callback
      onRetry(attempt + 1, error)
      
      // Wait before retrying with exponential backoff
      await sleep(currentDelay)
      currentDelay *= backoffMultiplier
    }
  }
  
  throw lastError
}

/**
 * API request wrapper with retry logic
 */
export async function apiRequest<T>(
  url: string,
  options: RequestInit = {},
  retryConfig: RetryConfig = {}
): Promise<T> {
  return fetchWithRetry(async () => {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    })
    
    if (!response.ok) {
      const error: any = new Error(`HTTP ${response.status}: ${response.statusText}`)
      error.response = response
      
      try {
        error.data = await response.json()
      } catch {
        // Ignore JSON parse errors
      }
      
      throw error
    }
    
    return response.json()
  }, retryConfig)
}

/**
 * GET request with retry
 */
export function apiGet<T>(
  url: string,
  retryConfig?: RetryConfig
): Promise<T> {
  return apiRequest<T>(url, { method: 'GET' }, retryConfig)
}

/**
 * POST request with retry
 */
export function apiPost<T>(
  url: string,
  data: any,
  retryConfig?: RetryConfig
): Promise<T> {
  return apiRequest<T>(
    url,
    {
      method: 'POST',
      body: JSON.stringify(data)
    },
    retryConfig
  )
}

/**
 * PUT request with retry
 */
export function apiPut<T>(
  url: string,
  data: any,
  retryConfig?: RetryConfig
): Promise<T> {
  return apiRequest<T>(
    url,
    {
      method: 'PUT',
      body: JSON.stringify(data)
    },
    retryConfig
  )
}

/**
 * DELETE request with retry
 */
export function apiDelete<T>(
  url: string,
  retryConfig?: RetryConfig
): Promise<T> {
  return apiRequest<T>(url, { method: 'DELETE' }, retryConfig)
}

/**
 * Batch retry failed requests
 */
export async function retryFailedRequests<T>(
  requests: Array<() => Promise<T>>,
  retryConfig?: RetryConfig
): Promise<Array<T | Error>> {
  const results = await Promise.allSettled(
    requests.map(req => fetchWithRetry(req, retryConfig))
  )
  
  return results.map(result => {
    if (result.status === 'fulfilled') {
      return result.value
    } else {
      return result.reason
    }
  })
}

/**
 * Create a retryable request queue
 */
export class RetryQueue {
  private queue: Array<() => Promise<any>> = []
  private processing = false
  private config: RetryConfig
  
  constructor(config: RetryConfig = {}) {
    this.config = config
  }
  
  /**
   * Add request to queue
   */
  add<T>(request: () => Promise<T>): Promise<T> {
    return new Promise((resolve, reject) => {
      this.queue.push(async () => {
        try {
          const result = await fetchWithRetry(request, this.config)
          resolve(result)
          return result
        } catch (error) {
          reject(error)
          throw error
        }
      })
      
      if (!this.processing) {
        this.process()
      }
    })
  }
  
  /**
   * Process queue
   */
  private async process(): Promise<void> {
    if (this.processing || this.queue.length === 0) {
      return
    }
    
    this.processing = true
    
    while (this.queue.length > 0) {
      const request = this.queue.shift()
      if (request) {
        try {
          await request()
        } catch {
          // Error already handled in add()
        }
      }
    }
    
    this.processing = false
  }
  
  /**
   * Clear queue
   */
  clear(): void {
    this.queue = []
  }
  
  /**
   * Get queue size
   */
  get size(): number {
    return this.queue.length
  }
}
