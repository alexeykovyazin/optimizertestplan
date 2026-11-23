-- Test 78: the columns that depend on a primary key leave the key of the hash aggregation.
-- Change: optimizer notes 4.50. Plan: PLAN-hash-aggregate-improvements.md, step 2.3.
-- Every "diff" case compares the query with its sorted reference: the same query with COUNT(DISTINCT), which the
-- hash aggregation never takes.
-- Expected: every "diff" row gives 0; the "rows" rows give K1 20000, K2 20000, K3 1400, K4 19000, K5 16400.
-- Expected plans (the build with the change), the first branch of every case:
--   K1: Hash Aggregate (keys: 1, ...)   the primary key and three more columns of the table
--   K2: Hash Aggregate (keys: 2, ...)   a composite primary key and one more column
--   K3: no "keys: 1"                    a part of the composite key: nothing is left out
--   K4: Hash Aggregate (keys: 2, ...)   two tables of a join, each with its key
--   K5: no "keys: 1"                    a unique index with NULL keys is not taken: 2000 rows with a NULL key and
--                                       different texts stay 2000 groups
--   K6: Hash Aggregate (keys: 1, ...)   the keyed table on the null-supplying side of an outer join: its missing
--                                       rows give one NULL group
set bail off;
create database 'tst2def' user SYSDBA default character set utf8;
create table t (id int not null, k int not null, s varchar(60), c char(12), u varchar(40) collate unicode_ci,
  v numeric(18,2), constraint t_pk primary key (id));
create table p2 (a int not null, b int not null, s varchar(30), d int, constraint p2_pk primary key (a, b));
create table q (u int, s varchar(30), d int, constraint q_u unique (u));
create table mul (n int);
insert into mul values (1); insert into mul values (2); insert into mul values (3);
insert into mul values (4); insert into mul values (5);
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 20000) do begin
    insert into t values (:i, mod(:i, 400), 'name' || :i, 'c' || mod(:i, 30), 'Key' || mod(:i, 50), :i / 3.0);
    insert into p2 values (mod(:i, 100), :i / 100, 'txt' || mod(:i, 700), mod(:i, 40));
    insert into q values (iif(mod(:i, 10) = 0, null, :i), 'txt' || :i, mod(:i, 40));
    i = i + 1;
  end
end^
set term ;^
commit;
create index t_k on t (k); create index p2_d on p2 (d); create index q_d on q (d);
commit;
set statistics index t_k; set statistics index p2_d; set statistics index q_d;
set statistics index t_pk; set statistics index p2_pk; set statistics index q_u;
commit;

set explain on;
select 'K1 rows' as t, count(*) from (select id, s, c, u, count(*) n from t, mul group by id, s, c, u);
select 'K1 diff' as t, count(*) from (select id, s, c, u, n, w from (
    select id, s, c, u, count(*) n, sum(v) w from t, mul group by id, s, c, u
    union all
    select id, s, c, u, n, w from (select id, s, c, u, count(*) n, sum(v) w, count(distinct k) x from t, mul
      group by id, s, c, u))
  group by id, s, c, u, n, w having count(*) <> 2);
select 'K2 rows' as t, count(*) from (select a, b, s, count(*) n from p2, mul group by a, b, s);
select 'K2 diff' as t, count(*) from (select a, b, s, n, w from (
    select a, b, s, count(*) n, sum(d) w from p2, mul group by a, b, s
    union all
    select a, b, s, n, w from (select a, b, s, count(*) n, sum(d) w, count(distinct d) x from p2, mul group by a, b, s))
  group by a, b, s, n, w having count(*) <> 2);
select 'K3 rows' as t, count(*) from (select a, s, d, count(*) n from p2, mul group by a, s, d);
select 'K3 diff' as t, count(*) from (select a, s, n, w from (
    select a, s, count(*) n, sum(d) w from p2, mul group by a, s
    union all
    select a, s, n, w from (select a, s, count(*) n, sum(d) w, count(distinct b) x from p2, mul group by a, s))
  group by a, s, n, w having count(*) <> 2);
select 'K4 rows' as t, count(*) from (select x.id, x.s, y.id yid, y.u, count(*) n
  from t x join t y on y.id = x.id + 1000, mul group by x.id, x.s, y.id, y.u);
select 'K4 diff' as t, count(*) from (select id, s, yid, u, n from (
    select x.id, x.s, y.id yid, y.u, count(*) n from t x join t y on y.id = x.id + 1000, mul group by x.id, x.s, y.id, y.u
    union all
    select id, s, yid, u, n from (select x.id, x.s, y.id yid, y.u, count(*) n, count(distinct x.k) z
      from t x join t y on y.id = x.id + 1000, mul group by x.id, x.s, y.id, y.u))
  group by id, s, yid, u, n having count(*) <> 2);
select 'K5 rows' as t, count(*) from (select u, s, count(*) n from q, mul where u is null or u < 16001 group by u, s);
select 'K5 diff' as t, count(*) from (select u, s, n from (
    select u, s, count(*) n from q, mul group by u, s
    union all
    select u, s, n from (select u, s, count(*) n, count(distinct d) x from q, mul group by u, s))
  group by u, s, n having count(*) <> 2);
select 'K6 diff' as t, count(*) from (select id, s, n from (
    select y.id, y.s, count(*) n from t x left join t y on y.id = x.k and y.k > 5 group by y.id, y.s
    union all
    select id, s, n from (select y.id, y.s, count(*) n, count(distinct x.id) z
      from t x left join t y on y.id = x.k and y.k > 5 group by y.id, y.s))
  group by id, s, n having count(*) <> 2);
set explain off;
commit;
drop database;
