drop index if exists audit_logs_created_idx;
drop table if exists audit_logs;

drop index if exists provider_models_enabled_idx;
drop table if exists provider_models;

drop index if exists providers_enabled_idx;
drop table if exists providers;

drop index if exists auth_sessions_active_idx;
drop index if exists auth_sessions_token_hash_idx;
drop table if exists auth_sessions;

drop table if exists users;
