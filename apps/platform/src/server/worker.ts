export interface WorkerConfig {
  workerId: string;
  pollIntervalMs: number;
}

export interface WorkerLogger {
  info(fields: Record<string, unknown>, message: string): void;
}

export interface WorkerRunResult {
  processed: number;
}

/**
 * There is no queue table: due work is derived from instance state. Instances that are `running` or
 * `waiting` get scanned, locked one at a time, and asked to advance — that scan arrives with the
 * match runtime, so this loop currently has nothing to poll.
 */
export function createWorker(config: WorkerConfig, logger: WorkerLogger = console) {
  return {
    config,
    async runOnce(): Promise<WorkerRunResult> {
      const result = { processed: 0 };
      logger.info({ workerId: config.workerId, ...result }, "worker poll completed");
      return result;
    },
  };
}
