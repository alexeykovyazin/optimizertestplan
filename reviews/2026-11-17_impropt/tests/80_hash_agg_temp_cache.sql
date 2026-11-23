-- Test 80: the hash aggregation and the hash unique take the temp cache past AggregateHashMemory.
-- Change: hqbird PR #61, optimizer notes 4.47. Plan: PLAN-hash-aggregate-improvements.md, step 1.4.
-- The alias has no special settings: AggregateHashMemory = 8M, TempCacheLimit = 64M (SuperServer), so a node may
-- take up to 32M. The groupings of this test need 10M - 25M: more than AggregateHashMemory, less than the bound.
-- Every "diff" case compares the query with its sorted reference: the same query with COUNT(DISTINCT), which the
-- hash methods never take.
-- Expected: every "diff" row gives 0; the "rows" rows give C1 30000, C2 30000, C3 59994.
--   C4: three calls give the same row (call N 30000): the taken cache goes back at the close of every call.
--   C5: error caught (a division by zero in the middle of the input, handled inside the block); C6 gives 30000:
--       the cache goes back after an error too.
-- Expected plans (the build with the change): "Hash Aggregate" in the first branch of C1, "Hash Unique" in C2 and
-- in C3. Before the change the three are sorted: they do not fit 8M.
set bail off;
create database 'tst2def' user SYSDBA default character set utf8;
create table t (id int not null primary key, g int not null, h int not null, s varchar(50) character set none not null,
  v numeric(18,2));
set term ^;
execute block as declare i int = 0; begin
  while (i < 120000) do begin
    insert into t values (:i, mod(:i, 30000), mod(:i * 7, 30000), 'name' || mod(:i, 30000) || lpad('', mod(:i, 40), 'x'),
      :i / 3.0);
    i = i + 1;
  end
end^
create procedure p returns (n int) as
begin
  select count(*) from (select mod(id, 30000) g, count(*) c, sum(v) w, max(s) a from t group by 1) into :n;
  suspend;
end^
set term ;^
commit;
create index t_g on t (g); create index t_h on t (h); create index t_s on t (s);
commit;
set statistics index t_g; set statistics index t_h; set statistics index t_s;
commit;

set explain on;
select 'C1 rows' as t, count(*) from (select mod(id, 30000) g, count(*) c, sum(v) w, max(s) a from t group by 1);
select 'C1 diff' as t, count(*) from (select g, c, w, a from (
    select mod(id, 30000) g, count(*) c, sum(v) w, max(s) a from t group by 1
    union all
    select g, c, w, a from (select mod(id, 30000) g, count(*) c, sum(v) w, max(s) a, count(distinct id) x
      from t group by 1))
  group by g, c, w, a having count(*) <> 2);
select 'C2 rows' as t, count(*) from (select distinct g, s from t);
select 'C2 diff' as t, count(*) from (select g, s from (
    select g, s from (select distinct g, s from t)
    union all
    select g, s from (select g, s, count(distinct id) x from t group by 1, 2))
  group by g, s having count(*) <> 2);
select 'C3 rows' as t, count(*) from (select g, s from t union select h, s from t);
select 'C3 diff' as t, count(*) from (select g, s from (
    select g, s from (select g, s from t union select h, s from t)
    union all
    select g, s from (select g, s, count(distinct b) x from (
      select g, s, id b from t union all select h, s, id from t) group by 1, 2))
  group by g, s having count(*) <> 2);
set explain off;
select 'call 1' as t, n from p;
select 'call 2' as t, n from p;
select 'call 3' as t, n from p;
set term ^;
execute block returns (t varchar(10), msg varchar(20)) as
  declare n int;
begin
  t = 'C5';
  begin
    select count(*) from (select mod(id, 30000) g, max(s || cast(1 / (id - 100000) as varchar(10))) a
      from t group by 1) into :n;
    msg = 'no error';
  when any do
    msg = 'error caught';
  end
  suspend;
end^
set term ;^
select 'C6' as t, count(*) from (select mod(id, 30000) g, count(*) c, sum(v) w, max(s) a from t group by 1);
commit;
drop database;
