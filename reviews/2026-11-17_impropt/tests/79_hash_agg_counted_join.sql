-- Test 79: the counted streams of a join under the hash aggregation.
-- Change: optimizer notes 4.51. Plan: PLAN-hash-aggregate-improvements.md, step 3.1.
-- A join under a counting aggregate passes the number of the rows of a table nothing refers to instead of the
-- rows. With a GROUP BY this needs the hash aggregation.
-- Every "diff" case compares the query with its sorted reference: the same query with COUNT(DISTINCT), which the
-- hash aggregation and the counting never take.
-- Expected: every "diff" row gives 0; "W1 rows" gives 40 1200000 (40 groups, the join gives 1 200 000 rows).
-- Expected plans (the build with the change): the mark "counted streams: 1" of a hash join under "Hash Aggregate"
-- in the first branch of the cases where the optimizer hashes the table nothing refers to (W4 and W5 here; in
-- W1 and W2 it hashes the other table, in W3 both tables are referred to).
set bail off;
create database 'tst2def' user SYSDBA default character set utf8;
create table t (id int not null primary key, k int not null, m int not null, s varchar(30), v numeric(18,2));
set term ^;
execute block as declare i int = 0; begin
  while (i < 60000) do begin
    insert into t values (:i, mod(:i, 40), mod(:i * 7, 3000), 'name' || mod(:i, 500), :i / 3.0);
    i = i + 1;
  end
end^
set term ;^
commit;
create index t_k on t (k); create index t_m on t (m);
commit;
set statistics index t_k; set statistics index t_m;
commit;

set explain on;
select 'W1 rows' as t, count(*), sum(n) from (select b.k, count(*) n from t a join t b on b.m = a.m group by b.k);
select 'W1 diff' as t, count(*) from (select k, n, w from (
    select b.k, count(*) n, sum(b.v) w from t a join t b on b.m = a.m group by b.k
    union all
    select k, n, w from (select b.k, count(*) n, sum(b.v) w, count(distinct a.m) x
      from t a join t b on b.m = a.m group by b.k))
  group by k, n, w having count(*) <> 2);
select 'W2 diff' as t, count(*) from (select k, n, w, y, z from (
    select b.k, count(*) n, sum(b.v) w, min(b.s) y, avg(b.v) z from t a join t b on b.m = a.m group by b.k
    union all
    select k, n, w, y, z from (select b.k, count(*) n, sum(b.v) w, min(b.s) y, avg(b.v) z, count(distinct a.m) x
      from t a join t b on b.m = a.m group by b.k))
  group by k, n, w, y, z having count(*) <> 2);
select 'W3 diff' as t, count(*) from (select k, n, w from (
    select b.k, count(*) n, sum(a.v) w from t a join t b on b.m = a.m group by b.k
    union all
    select k, n, w from (select b.k, count(*) n, sum(a.v) w, count(distinct a.m) x
      from t a join t b on b.m = a.m group by b.k))
  group by k, n, w having count(*) <> 2);
select 'W4 diff' as t, count(*) from (select g, n, w from (
    select mod(b.id, 9) g, count(*) n, count(b.s) w from t a join t b on b.m = a.m where a.id < 20000 group by 1
    union all
    select g, n, w from (select mod(b.id, 9) g, count(*) n, count(b.s) w, count(distinct a.m) x
      from t a join t b on b.m = a.m where a.id < 20000 group by 1))
  group by g, n, w having count(*) <> 2);
select 'W5 diff' as t, count(*) from (select k, n from (
    select b.k, count(*) n from t a join t b on b.m = a.m join t c on c.id = a.k group by b.k
    union all
    select k, n from (select b.k, count(*) n, count(distinct a.m) x
      from t a join t b on b.m = a.m join t c on c.id = a.k group by b.k))
  group by k, n having count(*) <> 2);
set explain off;
commit;
drop database;
