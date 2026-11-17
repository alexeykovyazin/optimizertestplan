-- 66_hj_spilled_side.sql - the plain hash join whose hashed side spilled to the temp file.
-- Aliases (all with ShowExplainCardinality = true, TempCacheLimit = 8M):
--   tst16hjtemp    - HashJoinBatchMemory by default (16M), SubQueryConversion = true (the hash semi-join of T7)
--   tst16hjtemp64k - HashJoinBatchMemory = 65536: the side is split into 64 parts, every part is above the limit
--   tst16hjtemp0   - HashJoinBatchMemory = 0: the load and the clustering are off
-- d: 1 000 000 rows, k = mod(id, 200000) (the rows with k < 20000 find matches: 100 000 rows, 5 per k), u = id,
--    nk = k, NULL in 20 rows.
-- w: 600 000 rows of ~130 bytes (78 MB), k = mod(i * 7919, 20000) (30 rows per k, scattered over the table),
--    u = i (unique), nk = k, NULL in 12 000 rows. Above HashJoinBatchMemory: clustered by the hash.
-- s: 100 000 rows of ~130 bytes (13 MB), k as in w (5 rows per k). Within HashJoinBatchMemory: loaded.
-- z: 300 000 rows of ~130 bytes, k = 7 in a half of the rows (one part is above the limit), the rest 7.5 per k.
-- No indexes on the join keys: the hash join is the only method, the smaller table is hashed.
-- Every query must return the same numbers on every build and on every alias. The expected counts:
--   T1 3 000 000; T2 500 000; T3 600 000; T4a 2 940 000; T4b 3 180 000; T5 1 500 000; T6 1 460 000 / 1 200 000;
--   T7 100 000; T8 3 000 000; T9 9 000 000.
set bail off;
create database 'tst16hjtemp' user SYSDBA;
create table d (id int not null, k int, u int, nk int);
create table w (id int not null, k int, u int, nk int, pad varchar(100));
create table s (id int not null, k int, pad varchar(100));
create table z (id int not null, k int, pad varchar(100));
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 1000000) do begin
    insert into d values (:i, mod(:i, 200000), :i, iif(mod(:i, 50000) = 49999, null, mod(:i, 200000)));
    i = i + 1;
  end
  i = 0;
  while (i < 600000) do begin
    insert into w values (:i, mod(:i * 7919, 20000), :i, iif(mod(:i, 50) = 49, null, mod(:i * 7919, 20000)),
      'pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad ' || mod(:i, 97));
    i = i + 1;
  end
  i = 0;
  while (i < 100000) do begin
    insert into s values (:i, mod(:i * 7919, 20000),
      'pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad ' || mod(:i, 97));
    i = i + 1;
  end
  i = 0;
  while (i < 300000) do begin
    insert into z values (:i, iif(:i < 150000, 7, mod(:i, 20000)),
      'pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad ' || mod(:i, 97));
    i = i + 1;
  end
end^
set term ;^
commit;

select 'P: the plans' as tag from rdb$database;
set explain on; set planonly on;
select count(*) from d, w where d.k = w.k;
select count(*) from d, s where d.k = s.k;
select count(*) from d, w where d.u = w.u;
select count(*) from d, z where d.k = z.k;
select count(*), count(w.u) from d left join w on d.k = w.k where d.id < 300000;
select count(*) from d where exists (select 1 from w where w.k = d.k);
select count(*) from d, w, s where d.k = w.k and d.k = s.k and d.id < 20000;
select count(*) from d, w, z where d.k = w.k and d.k = z.k and d.id < 20000;
set planonly off; set explain off;

select 'T: the results' as tag from rdb$database;
set stats on;
-- T1: the side above the limit, 30 rows per key: clustered
select 'T1', count(*), sum(cast(w.u as bigint)), max(w.pad), min(w.pad) from d, w where d.k = w.k;
-- T2: the side within the limit: loaded
select 'T2', count(*), sum(cast(s.id as bigint)), max(s.pad), min(s.pad) from d, s where d.k = s.k;
-- T3: unique keys: not clustered, one record per leader row
select 'T3', count(*), sum(cast(w.u as bigint)), max(w.pad), min(w.pad) from d, w where d.u = w.u;
-- T4: NULL keys. The strict equality drops them, IS NOT DISTINCT FROM matches NULL with NULL
select 'T4a', count(*), sum(cast(w.u as bigint)) from d, w where d.nk = w.nk;
select 'T4b', count(*), sum(cast(w.u as bigint)) from d, w where d.nk is not distinct from w.nk;
-- T5: a half of the side under one key: its part is above the limit
select 'T5', count(*), sum(cast(z.id as bigint)), max(z.pad), min(z.pad) from d, z where d.k = z.k;
-- T6: the outer hash join
select 'T6', count(*), count(w.u), sum(cast(w.u as bigint)) from d left join w on d.k = w.k where d.id < 300000;
-- T7: the hash semi-join
select 'T7', count(*) from d where exists (select 1 from w where w.k = d.k);
-- T8: three rivers, two spilled hashed sides
select 'T8', count(*), sum(cast(w.u as bigint)), sum(cast(s.id as bigint)) from d, w, s
  where d.k = w.k and d.k = s.k and d.id < 20000;
-- T9: three rivers, the skewed side among the hashed ones
select 'T9', count(*), sum(cast(w.u as bigint)), sum(cast(z.id as bigint)) from d, w, z
  where d.k = w.k and d.k = z.k and d.id < 20000;
set stats off;
commit;
drop database;

-- The same d and w under HashJoinBatchMemory = 65536: 64 parts, every part above the limit
create database 'tst16hjtemp64k' user SYSDBA;
create table d (id int not null, k int, u int, nk int);
create table w (id int not null, k int, u int, nk int, pad varchar(100));
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 1000000) do begin
    insert into d values (:i, mod(:i, 200000), :i, iif(mod(:i, 50000) = 49999, null, mod(:i, 200000)));
    i = i + 1;
  end
  i = 0;
  while (i < 600000) do begin
    insert into w values (:i, mod(:i * 7919, 20000), :i, iif(mod(:i, 50) = 49, null, mod(:i * 7919, 20000)),
      'pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad ' || mod(:i, 97));
    i = i + 1;
  end
end^
set term ;^
commit;
select 'K: HashJoinBatchMemory = 65536' as tag from rdb$database;
set stats on;
select 'T1', count(*), sum(cast(w.u as bigint)), max(w.pad), min(w.pad) from d, w where d.k = w.k;
select 'T3', count(*), sum(cast(w.u as bigint)), max(w.pad), min(w.pad) from d, w where d.u = w.u;
select 'T4a', count(*), sum(cast(w.u as bigint)) from d, w where d.nk = w.nk;
select 'T4b', count(*), sum(cast(w.u as bigint)) from d, w where d.nk is not distinct from w.nk;
select 'T6', count(*), count(w.u), sum(cast(w.u as bigint)) from d left join w on d.k = w.k where d.id < 300000;
set stats off;
commit;
drop database;

-- The same d and w under HashJoinBatchMemory = 0: the side stays as it spilled
create database 'tst16hjtemp0' user SYSDBA;
create table d (id int not null, k int, u int, nk int);
create table w (id int not null, k int, u int, nk int, pad varchar(100));
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 1000000) do begin
    insert into d values (:i, mod(:i, 200000), :i, iif(mod(:i, 50000) = 49999, null, mod(:i, 200000)));
    i = i + 1;
  end
  i = 0;
  while (i < 600000) do begin
    insert into w values (:i, mod(:i * 7919, 20000), :i, iif(mod(:i, 50) = 49, null, mod(:i * 7919, 20000)),
      'pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad pad ' || mod(:i, 97));
    i = i + 1;
  end
end^
set term ;^
commit;
select 'Z: HashJoinBatchMemory = 0' as tag from rdb$database;
set stats on;
select 'T1', count(*), sum(cast(w.u as bigint)), max(w.pad), min(w.pad) from d, w where d.k = w.k;
select 'T3', count(*), sum(cast(w.u as bigint)), max(w.pad), min(w.pad) from d, w where d.u = w.u;
select 'T4b', count(*), sum(cast(w.u as bigint)) from d, w where d.nk is not distinct from w.nk;
set stats off;
commit;
drop database;
