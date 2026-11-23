-- Test 75: a grouping expression without an expression index takes the hash aggregation.
-- Change: hqbird PR #60, optimizer notes 4.45. Plan: PLAN-hash-aggregate-improvements.md, step 2.1.
-- Every case compares the query with its sorted reference: the same query with COUNT(DISTINCT id), which the hash
-- aggregation never takes. The two results are put together and grouped; a row that does not come twice is a
-- difference.
-- Expected: every "diff" row gives 0; the "rows" rows give E1 50, E2 3, E3 12, E4 1850, E5 2, E6 500.
-- Expected plans (the build with the change): the first branch of every case is "Hash Aggregate", the second is
-- "Aggregate" over "Sort". Before the change both branches are sorted.
set bail off;
create database 'tst2def' user SYSDBA default character set utf8;
create table t (id int not null primary key, k int not null, m int not null, d date not null,
  s varchar(30) not null, v numeric(18,2));
set term ^;
execute block as declare i int = 0; begin
  while (i < 60000) do begin
    insert into t values (:i, mod(:i, 37), mod(:i * 7, 1000), dateadd(mod(:i, 900) day to date '2024-01-01'),
      'name' || mod(:i, 500), :i / 3.0);
    i = i + 1;
  end
end^
set term ;^
commit;
create index t_k on t (k); create index t_m on t (m); create index t_d on t (d); create index t_s on t (s);
commit;
set statistics index t_k; set statistics index t_m; set statistics index t_d; set statistics index t_s;
commit;

set explain on;
select 'E1 rows' as t, count(*) from (select mod(id, 50) g, count(*) c from t group by 1);
select 'E1 diff' as t, count(*) from (select g, c, s from (
    select mod(id, 50) g, count(*) c, sum(v) s from t group by 1
    union all
    select g, c, s from (select mod(id, 50) g, count(*) c, sum(v) s, count(distinct id) x from t group by 1))
  group by g, c, s having count(*) <> 2);
select 'E2 rows' as t, count(*) from (select extract(year from d) g, count(*) c from t group by 1);
select 'E2 diff' as t, count(*) from (select g, c, s from (
    select extract(year from d) g, count(*) c, sum(v) s from t group by 1
    union all
    select g, c, s from (select extract(year from d) g, count(*) c, sum(v) s, count(distinct id) x from t group by 1))
  group by g, c, s having count(*) <> 2);
select 'E3 rows' as t, count(*) from (select extract(month from d) g, count(*) c from t group by 1);
select 'E3 diff' as t, count(*) from (select g, c, s from (
    select extract(month from d) g, count(*) c, min(id) s from t group by 1
    union all
    select g, c, s from (select extract(month from d) g, count(*) c, min(id) s, count(distinct id) x from t group by 1))
  group by g, c, s having count(*) <> 2);
select 'E4 rows' as t, count(*) from (select k, mod(id, 50) g, count(*) c from t group by 1, 2);
select 'E4 diff' as t, count(*) from (select k, g, c, s from (
    select k, mod(id, 50) g, count(*) c, sum(v) s from t group by 1, 2
    union all
    select k, g, c, s from (select k, mod(id, 50) g, count(*) c, sum(v) s, count(distinct id) x from t group by 1, 2))
  group by k, g, c, s having count(*) <> 2);
select 'E5 rows' as t, count(*) from (select (k > 20) g, count(*) c from t group by 1);
select 'E5 diff' as t, count(*) from (select g, c, s from (
    select (k > 20) g, count(*) c, max(id) s from t group by 1
    union all
    select g, c, s from (select (k > 20) g, count(*) c, max(id) s, count(distinct id) x from t group by 1))
  group by g, c, s having count(*) <> 2);
select 'E6 rows' as t, count(*) from (select upper(s) g, count(*) c from t group by 1);
select 'E6 diff' as t, count(*) from (select g, c, s from (
    select upper(s) g, count(*) c, sum(m) s from t group by 1
    union all
    select g, c, s from (select upper(s) g, count(*) c, sum(m) s, count(distinct id) x from t group by 1))
  group by g, c, s having count(*) <> 2);
set explain off;
commit;
drop database;
