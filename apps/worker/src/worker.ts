import {
  claimOutboxEvents,
  claimPendingCommands,
  claimScheduledJobs,
  completeOutboxEvent,
  completePendingCommand,
  completeScheduledJob,
  failLeasedTask,
  listActiveTenantIds,
  type DbExecutor,
} from "@vbrpg/db";

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
type OutboxEvent = Awaited<ReturnType<typeof claimOutboxEvents>>[number];

export interface WorkerHandlers {
  handleCommand?: (command: PendingCommand) => Promise<void>;
  handleScheduledJob?: (job: ScheduledJob) => Promise<void>;
  publishOutbox?: (event: OutboxEvent) => Promise<void>;
}

export interface WorkerDependencies {
  db: DbExecutor;
  listTenantIds?: () => Promise<string[]>;
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

      const tenantIds = dependencies.listTenantIds
        ? await dependencies.listTenantIds()
        : await listActiveTenantIds(dependencies.db);
      for (const tenantId of tenantIds) {
        if (dependencies.handlers.handleCommand) {
          const commands = await claimPendingCommands(dependencies.db, {
            tenantId,
            workerId: config.workerId,
            leaseMs: config.leaseMs,
          });
          result.claimed += commands.length;
          for (const command of commands) {
            try {
              await dependencies.handlers.handleCommand(command);
              await completePendingCommand(dependencies.db, { tenantId }, command.id, config.workerId);
              result.processed += 1;
            } catch (error) {
              await failLeasedTask(
                dependencies.db,
                { tenantId },
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
            tenantId,
            workerId: config.workerId,
            leaseMs: config.leaseMs,
          });
          result.claimed += jobs.length;
          for (const job of jobs) {
            try {
              await dependencies.handlers.handleScheduledJob(job);
              await completeScheduledJob(dependencies.db, { tenantId }, job.id, config.workerId);
              result.processed += 1;
            } catch (error) {
              await failLeasedTask(
                dependencies.db,
                { tenantId },
                "scheduled_jobs",
                job.id,
                config.workerId,
                error instanceof Error ? error.message : String(error),
              );
            }
          }
        }

        if (dependencies.handlers.publishOutbox) {
          const events = await claimOutboxEvents(dependencies.db, {
            tenantId,
            workerId: config.workerId,
            leaseMs: config.leaseMs,
          });
          result.claimed += events.length;
          for (const event of events) {
            try {
              await dependencies.handlers.publishOutbox(event);
              await completeOutboxEvent(dependencies.db, { tenantId }, event.id, config.workerId);
              result.processed += 1;
            } catch (error) {
              await failLeasedTask(
                dependencies.db,
                { tenantId },
                "outbox_events",
                event.id,
                config.workerId,
                error instanceof Error ? error.message : String(error),
              );
            }
          }
        }
      }
      logger.info({ workerId: config.workerId, ...result }, "worker poll completed");
      return result;
    },
  };
}
