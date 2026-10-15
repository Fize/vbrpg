import {
  claimPendingCommands,
  claimScheduledJobs,
  completePendingCommand,
  completeScheduledJob,
  failLeasedTask,
  type DbExecutor,
} from "./db/index.js";

export interface WorkerConfig {
  workerId: string;
  pollIntervalMs: number;
  leaseMs: number;
}

export interface WorkerLogger {
  info(fields: Record<string, unknown>, message: string): void;
}

export interface WorkerRunResult {
  claimed: number;
  processed: number;
}

type PendingCommand = Awaited<ReturnType<typeof claimPendingCommands>>[number];
type ScheduledJob = Awaited<ReturnType<typeof claimScheduledJobs>>[number];

export interface WorkerHandlers {
  handleCommand?: (command: PendingCommand) => Promise<void>;
  handleScheduledJob?: (job: ScheduledJob) => Promise<void>;
}

export interface WorkerDependencies {
  db: DbExecutor;
  handlers: WorkerHandlers;
}

export function createWorker(
  config: WorkerConfig,
  logger: WorkerLogger = console,
  dependencies?: WorkerDependencies,
) {
  return {
    config,
    async runOnce(): Promise<WorkerRunResult> {
      const result = { claimed: 0, processed: 0 };
      if (!dependencies) {
        logger.info({ workerId: config.workerId, ...result }, "worker poll completed");
        return result;
      }

      if (dependencies.handlers.handleCommand) {
        const commands = await claimPendingCommands(dependencies.db, {
          workerId: config.workerId,
          leaseMs: config.leaseMs,
        });
        result.claimed += commands.length;
        for (const command of commands) {
          try {
            await dependencies.handlers.handleCommand(command);
            await completePendingCommand(dependencies.db, command.id, config.workerId);
            result.processed += 1;
          } catch (error) {
            await failLeasedTask(
              dependencies.db,
              "pending_commands",
              command.id,
              config.workerId,
              error instanceof Error ? error.message : String(error),
            );
          }
        }
      }

      if (dependencies.handlers.handleScheduledJob) {
        const jobs = await claimScheduledJobs(dependencies.db, {
          workerId: config.workerId,
          leaseMs: config.leaseMs,
        });
        result.claimed += jobs.length;
        for (const job of jobs) {
          try {
            await dependencies.handlers.handleScheduledJob(job);
            await completeScheduledJob(dependencies.db, job.id, config.workerId);
            result.processed += 1;
          } catch (error) {
            await failLeasedTask(
              dependencies.db,
              "scheduled_jobs",
              job.id,
              config.workerId,
              error instanceof Error ? error.message : String(error),
            );
          }
        }
      }

      logger.info({ workerId: config.workerId, ...result }, "worker poll completed");
      return result;
    },
  };
}
