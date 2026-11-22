-- Test 73: the prepare of a GROUP BY with columns of five or more streams crashed the server (DSB query 64).
-- Cause: ExtStatistics::getGroupCountEstimate kept the per-stream groups (each owns an array) in a plain
-- HalfStaticArray with 4 inline items. The fifth stream made the array grow: the items were moved as raw bytes and
-- the new item was assigned into raw memory. The same defect: the list of the seen candidates of a reversed
-- STARTING WITH / CONTAINING predicate (16 inline items, up to 64 candidates).
-- The alias needs ExtendedStatistics = true (tstbhj).
-- Expected: G4 and G5 return 3 rows each; G7 returns 3 rows; R1 and R2 return a count; no crash.
set bail off;
create database 'tstbhj' user SYSDBA default character set utf8;
create table t1 (id int not null primary key, v int);
create table t2 (id int not null primary key, v int);
create table t3 (id int not null primary key, v int);
create table t4 (id int not null primary key, v int);
create table t5 (id int not null primary key, v int);
create table t6 (id int not null primary key, v int);
create table t7 (id int not null primary key, v int);
create table s (id int not null primary key, w varchar(40));
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 300) do begin
    insert into t1 values (:i, mod(:i, 3)); insert into t2 values (:i, mod(:i, 3)); insert into t3 values (:i, mod(:i, 3));
    insert into t4 values (:i, mod(:i, 3)); insert into t5 values (:i, mod(:i, 3)); insert into t6 values (:i, mod(:i, 3));
    insert into t7 values (:i, mod(:i, 3));
    insert into s values (:i, substring('abcdefghijklmnopqrstuvwxyzabcdefghijkl' from 1 for 1 + mod(:i, 30)));
    i = i + 1;
  end
end^
set term ;^
commit;
alter database add extended statistics;
commit;
alter database refresh statistics;
commit;

select 'G4' as t, t1.v, t2.v, t3.v, t4.v, count(*)
  from t1 join t2 on t2.id = t1.id join t3 on t3.id = t1.id join t4 on t4.id = t1.id
  group by t1.v, t2.v, t3.v, t4.v;
select 'G5' as t, t1.v, t2.v, t3.v, t4.v, t5.v, count(*)
  from t1 join t2 on t2.id = t1.id join t3 on t3.id = t1.id join t4 on t4.id = t1.id join t5 on t5.id = t1.id
  group by t1.v, t2.v, t3.v, t4.v, t5.v;
select 'G7' as t, t1.v, t2.v, t3.v, t4.v, t5.v, t6.v, t7.v, count(*)
  from t1 join t2 on t2.id = t1.id join t3 on t3.id = t1.id join t4 on t4.id = t1.id join t5 on t5.id = t1.id
       join t6 on t6.id = t1.id join t7 on t7.id = t1.id
  group by t1.v, t2.v, t3.v, t4.v, t5.v, t6.v, t7.v;
select distinct 'D5' as t, t1.v, t2.v, t3.v, t4.v, t5.v
  from t1 join t2 on t2.id = t1.id join t3 on t3.id = t1.id join t4 on t4.id = t1.id join t5 on t5.id = t1.id;
select 'R1' as t, count(*) from s where 'abcdefghijklmnopqrstuvwxyzabcdef' starting with s.w;
select 'R2' as t, count(*) from s where 'abcdefghij' containing s.w;
commit;
drop database;
