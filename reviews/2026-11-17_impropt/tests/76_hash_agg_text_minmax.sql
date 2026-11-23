-- Test 76: a MIN or a MAX of a text in the hash aggregation; the moves of the aggregate state.
-- Change: hqbird PR #61, optimizer notes 4.46 and 4.48. Plan: PLAN-hash-aggregate-improvements.md, steps 4.1, 2.2.
-- Every "diff" case compares the query with its sorted reference: the same query with COUNT(DISTINCT id).
-- Expected: every "diff" row gives 0.
--   M1 rows: 40. Three calls of the procedure give the same row: call N 40 name0 name9x
--   M6: error caught (a division by zero in the middle of the input, handled inside the block); then M7 rows
--       gives 40: the next query works after the error
--   M8: 5 (the fetch of the groups is interrupted); then M9 rows gives 3000
-- Expected plans (the build with the change): "Hash Aggregate" in the first branch of M1..M4.
set bail off;
create database 'tst2def' user SYSDBA default character set utf8;
create table t (id int not null primary key, k int not null, m int not null, s varchar(200), c char(12), u varchar(40) collate unicode_ci,
  v numeric(18,2));
set term ^;
execute block as declare i int = 0; begin
  while (i < 60000) do begin
    insert into t values (:i, mod(:i, 40), mod(:i * 7, 3000), 'name' || mod(:i, 100) || lpad('', mod(:i, 150), 'x'),
      'c' || mod(:i, 30), iif(mod(:i, 2) = 0, 'Key', 'KEY') || mod(:i, 50), :i / 3.0);
    i = i + 1;
  end
  update t set s = null where mod(id, 11) = 0;
end^
create procedure p returns (n int, a varchar(200), b varchar(200)) as
begin
  select count(*), min(x), max(y) from (select k, min(substring(s from 1 for 6)) x, max(substring(s from 1 for 6)) y,
    count(*) c from t group by k) into :n, :a, :b;
  suspend;
end^
set term ;^
commit;
create index t_k on t (k); create index t_m on t (m);
commit;
set statistics index t_k; set statistics index t_m;
commit;

set explain on;
select 'M1 rows' as t, count(*) from (select k, min(s) a, max(s) b from t group by k);
select 'M1 diff' as t, count(*) from (select k, a, b, c from (
    select k, min(s) a, max(s) b, count(*) c from t group by k
    union all
    select k, a, b, c from (select k, min(s) a, max(s) b, count(*) c, count(distinct id) x from t group by k))
  group by k, a, b, c having count(*) <> 2);
select 'M2 diff' as t, count(*) from (select m, a, b, c from (
    select m, min(s) a, max(c) b, count(s) c from t group by m
    union all
    select m, a, b, c from (select m, min(s) a, max(c) b, count(s) c, count(distinct id) x from t group by m))
  group by m, a, b, c having count(*) <> 2);
select 'M3 diff' as t, count(*) from (select k, m, a, b, c from (
    select k, m, min(u) a, max(u) b, sum(v) c from t group by k, m
    union all
    select k, m, a, b, c from (select k, m, min(u) a, max(u) b, sum(v) c, count(distinct id) x from t group by k, m))
  group by k, m, a, b, c having count(*) <> 2);
select 'M4 diff' as t, count(*) from (select k, a, b, c from (
    select k, min(case when mod(id, 7) = 0 then s end) a, max(case when id < 0 then s end) b, count(*) c
      from t group by k
    union all
    select k, a, b, c from (select k, min(case when mod(id, 7) = 0 then s end) a, max(case when id < 0 then s end) b,
      count(*) c, count(distinct id) x from t group by k))
  group by k, a, b, c having count(*) <> 2);
set explain off;
select 'call 1' as t, n, a, b from p;
select 'call 2' as t, n, a, b from p;
select 'call 3' as t, n, a, b from p;
set term ^;
execute block returns (t varchar(10), msg varchar(20)) as
  declare n int;
begin
  t = 'M6';
  begin
    select count(*) from (select k, max(s || cast(1 / (id - 30000) as varchar(10))) a from t group by k)
      into :n;
    msg = 'no error';
  when any do
    msg = 'error caught';
  end
  suspend;
end^
set term ;^
select 'M7 rows' as t, count(*) from (select k, min(s) a, max(s) b from t group by k);
select 'M8' as t, count(*) from (select first 5 m, max(s) a from t group by m);
select 'M9 rows' as t, count(*) from (select m, max(s) a, min(s) b from t group by m);
commit;
drop database;
