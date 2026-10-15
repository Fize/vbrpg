drop index if exists scheduled_jobs_claim_idx;
drop table if exists scheduled_jobs;

drop index if exists pending_commands_claim_idx;
drop table if exists pending_commands;

drop index if exists game_events_instance_sequence_idx;
drop table if exists game_snapshots;

drop table if exists game_events;

drop table if exists game_participants;

drop index if exists game_instances_status_updated_idx;
drop table if exists game_instances;
