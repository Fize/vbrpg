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

export type WorkerTick = () => Promise<{ turns: number; failures: number }>;

/**
 * There is no queue table: due work is derived from instance state. Each tick hands the instance
 * scan to the caller — the AI seat runner today, potentially more than one job later.
 */
export function createWorker(
  config: WorkerConfig,
  logger: WorkerLogger = console,
  tick?: WorkerTick,
) {
  return {
    config,
    async runOnce(): Promise<WorkerRunResult> {
      if (!tick) {
        const idle = { processed: 0 };
        logger.info({ workerId: config.workerId, ...idle }, "worker poll completed");
        return idle;
      }
      const result = await tick();
      logger.info(
        { workerId: config.workerId, turns: result.turns, failures: result.failures },
        "worker poll completed",
      );
      return { processed: result.turns };
    },
  };
}
