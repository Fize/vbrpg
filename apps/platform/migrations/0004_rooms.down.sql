drop index if exists rooms_status_updated_idx;
alter table rooms drop constraint if exists rooms_current_instance_fk;
drop index if exists game_instances_room_idx;
alter table game_instances drop column if exists room_id;
drop table if exists room_members;
drop table if exists rooms;
