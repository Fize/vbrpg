export interface RateLimiter {
  /** Records an attempt for `key` and reports whether it is within the window budget. */
  allow(key: string, now?: number): boolean;
}

export function createRateLimiter(options: { limit: number; windowMs: number }): RateLimiter {
  const attempts = new Map<string, number[]>();
  return {
    allow(key, now = Date.now()) {
      const cutoff = now - options.windowMs;
      const recent = (attempts.get(key) ?? []).filter((timestamp) => timestamp > cutoff);
      if (recent.length >= options.limit) {
        attempts.set(key, recent);
        return false;
      }
      recent.push(now);
      attempts.set(key, recent);
      return true;
    },
  };
}

export interface ConcurrencyLimiter {
  /** Runs `operation` when a slot is free, or returns `undefined` when saturated. */
  run<T>(operation: () => Promise<T>): Promise<T> | undefined;
}

export function createConcurrencyLimiter(limit: number): ConcurrencyLimiter {
  let active = 0;
  return {
    run<T>(operation: () => Promise<T>): Promise<T> | undefined {
      if (active >= limit) return undefined;
      active += 1;
      return operation().finally(() => {
        active -= 1;
      });
    },
  };
}
