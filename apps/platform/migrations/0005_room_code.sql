-- A room needs a短号 people can say out loud and type in: the uuid is an identifier, not a name.
-- The alphabet leaves out the characters that get confused when read aloud (0/O, 1/I).
alter table rooms add column code text;

update rooms
   set code = upper(substr(translate(md5(random()::text), '01oil', '23456'), 1, 6))
 where code is null;

alter table rooms alter column code set not null;
create unique index rooms_code_key on rooms (code);
