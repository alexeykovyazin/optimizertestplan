-- Test 77: a UNION without ALL through the hash unique.
-- Change: optimizer notes 4.49. Plan: PLAN-hash-aggregate-improvements.md, step 2.5.
-- The reference of every case is the sorted aggregation over UNION ALL: GROUP BY with COUNT(DISTINCT), which the
-- hash methods never take. The two results are put together; a row that does not come twice is a difference.
-- Expected: every "diff" row gives 0; the "rows" rows give U1 1000, U2 19463, U3 41, U4 60000, U5 1000.
-- Expected plans (the build with the change): "Hash Unique" over "Union" in U1, U2, U3, U5 (an expression in U5).
--   U4 is a union of almost unique rows: the choice depends on the memory, the result must not.
set bail off;
create database 'tst2def' user SYSDBA default character set utf8;
create table t (id int not null, k int not null, m int not null, s varchar(30) not null,
  constraint t_pk primary key (id));
set term ^;
execute block as declare i int = 0; begin
  while (i < 60000) do begin
    insert into t values (:i, mod(:i, 37), mod(:i * 7, 1000), 'name' || mod(:i, 500));
    i = i + 1;
  end
end^
set term ;^
commit;
create index t_k on t (k); create index t_m on t (m); create index t_s on t (s);
commit;
set statistics index t_k; set statistics index t_m; set statistics index t_s; set statistics index t_pk;
commit;

set explain on;
select 'U1 rows' as t, count(*) from (select m from t union select k from t);
select 'U1 diff' as t, count(*) from (select a from (
    select a from (select m a from t union select k from t)
    union all
    select a from (select a, count(distinct b) x from (select m a, id b from t union all select k, id from t) group by a))
  group by a having count(*) <> 2);
select 'U2 rows' as t, count(*) from (select m, s from t union select k, s from t where id < 30000);
select 'U2 diff' as t, count(*) from (select a, s from (
    select a, s from (select m a, s from t union select k, s from t where id < 30000)
    union all
    select a, s from (select a, s, count(distinct b) x from (
      select m a, s, id b from t union all select k, s, id from t where id < 30000) group by a, s))
  group by a, s having count(*) <> 2);
select 'U3 rows' as t, count(*) from (select k a, 'a' s from t union select 5, 'b' from rdb$database
  union select k, 'b' from t where k < 3);
select 'U3 diff' as t, count(*) from (select a, s from (
    select a, s from (select k a, 'a' s from t union select 5, 'b' from rdb$database
      union select k, 'b' from t where k < 3)
    union all
    select a, s from (select a, s, count(distinct b) x from (
      select k a, 'a' s, id b from t union all select 5, 'b', 0 from rdb$database
      union all select k, 'b', id from t where k < 3) group by a, s))
  group by a, s having count(*) <> 2);
select 'U4 rows' as t, count(*) from (select id, s from t union select id, s from t);
select 'U4 diff' as t, count(*) from (select a, s from (
    select a, s from (select id a, s from t union select id, s from t)
    union all
    select a, s from (select a, s, count(distinct b) x from (
      select id a, s, k b from t union all select id, s, k from t) group by a, s))
  group by a, s having count(*) <> 2);
select 'U5 rows' as t, count(*) from (select m + 0 a from t union select k * 1 from t);
select 'U5 diff' as t, count(*) from (select a from (
    select a from (select m + 0 a from t union select k * 1 from t)
    union all
    select a from (select a, count(distinct b) x from (
      select m + 0 a, id b from t union all select k * 1, id from t) group by a))
  group by a having count(*) <> 2);
set explain off;
commit;
drop database;
