-- 63_bhj_spilled_batch.sql - the batched hash join over a spilled hashed side. Alias tst12bhjlow (TempCacheLimit = 64M,
-- ShowExplainCardinality = true).
-- p: 20 000 rows. l: 1 000 000 rows, pid = mod(i, 100000) (10 rows per pid). g: 8 000 000 rows, pid = mod(i * 7919, 100000)
-- (80 rows per pid, the rows of one pid are scattered over the table). g is above the in-memory hash capacity: BHJ.
-- The join p - l - g returns 20000 * 10 * 80 = 16 000 000 rows. The buffers of g (200 MB) do not fit the temp cache.
-- Before: every matched row of g was fetched by its position, one chunk of the temp file per fetch (minutes).
-- After: a spilled batch within TempCacheLimit / 4 is loaded into the memory at the build (seconds).
-- Expected: the plan is Batch Hash Join with g hashed, 16000000 rows, the elapsed time in seconds, not in minutes.
set bail off;
create database 'tst12bhjlow' user SYSDBA;
create table p (id int not null primary key, f int);
create table l (id int not null, pid int not null);
create table g (id int not null, pid int not null, pad varchar(40));
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 20000) do begin insert into p values (:i, mod(:i, 100)); i = i + 1; end
  i = 0;
  while (i < 1000000) do begin insert into l values (:i, mod(:i, 100000)); i = i + 1; end
  i = 0;
  while (i < 8000000) do begin insert into g values (:i, mod(:i * 7919, 100000), 'pad pad pad pad pad pad pad ' || mod(:i, 97)); i = i + 1; end
end^
set term ;^
commit;
create index l_pid on l (pid); create index g_pid on g (pid);
commit;

select 'B1: the plan' as tag from rdb$database;
set explain on; set planonly on;
select count(*) from p, l, g where p.id = l.pid and p.id = g.pid;
set planonly off; set explain off;
select 'B2: the results' as tag from rdb$database;
set stats on;
select count(*), sum(cast(g.id as bigint)), sum(cast(l.id as bigint)) from p, l, g where p.id = l.pid and p.id = g.pid;
select count(*), sum(cast(g.id as bigint)), max(g.pad), min(g.pad) from p, l, g where p.id = l.pid and p.id = g.pid and p.f < 10;
set stats off;
commit;
drop database;
