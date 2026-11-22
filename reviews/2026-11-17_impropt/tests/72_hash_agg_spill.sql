-- Test 72: the spill of the hash aggregation takes the dbkey of a stream from another stream (commit 8d6c1d0568).
-- Review: REVIEW-hash-aggregate.md, finding A4.
-- The database alias needs AggregateHashMemory = 512K (alias tsthagg512 in databases.conf).
-- The reference is the same script on an alias with AggregateHashMemory = 0 (the sorted path).
-- Expected: A4a 20000 10000; A4b 20000 10000 100010000; A4c 10000 10000.
-- The hash path gives a wrong sum for A4a (17720 on the review build).
-- With TempCacheLimit = 0 added to the alias the first query crashes the process (finding A5).
set bail off;
create database 'tsthagg512' user SYSDBA default character set utf8;
create table a (id integer, g integer);
create table b (id integer);
set term ^;
execute block as declare i int = 1; begin
  while (i <= 20000) do begin
    insert into a values (:i, :i);
    if (mod(:i, 2) = 0) then insert into b values (:i);
    i = i + 1;
  end
end^
set term ;^
commit;
create index b_id on b (id);
commit;
set explain on;
select 'A4a' as t, count(*), sum(c) from (select a.g, count(b.rdb$db_key) c from a left join b on b.id = a.id group by a.g);
select 'A4b' as t, count(*), sum(c), sum(s) from (select a.g, count(b.id) c, sum(b.id) s from a left join b on b.id = a.id group by a.g);
select 'A4c' as t, count(*), sum(c) from (select a.g, count(*) c from a join b on b.id = a.id join b b2 on b2.id = a.id group by a.g);
set explain off;
commit;
drop database;
