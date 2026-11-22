-- Test 71: defects of the hash aggregation and of the hash unique (commits 6c7c834cd6, 9fb180d41b, 8d6c1d0568).
-- Review: REVIEW-hash-aggregate.md. The database alias has no special settings (AggregateHashMemory = 8M by default).
-- The reference is the same script on an alias with AggregateHashMemory = 0 (the sorted path).
-- Expected (the sorted path):
--   A2: 1 zzz yy / 2 a a / 3 bbbbbbbbbb bbbbbbbbbb
--   A3v, A3d, A3f, A3z: 1 row each
--   A6: Max memory about the same as before the query (the hash path: more than 1 GB)
--   A7: Max memory about the same as before the query (the hash path: about 1 GB)
--   B1a, B1b, B1c: about 28 000 fetches (the hash path: more than 1 000 000)
--   B2: 100, no error (the hash path: "index T_A cannot be used in the specified plan")
--   B3: one Unique Sort (the hash path: Sort over Unique Sort)
--   B5: a plan text that the PLAN clause accepts (the hash path: PLAN HASH UNIQUE (U NATURAL), a syntax error)
--   A1: 150000 150000 (the hash path: a wrong sum; with 1 000 000 groups the process crashes)
set bail off;
create database 'tst2def' user SYSDBA default character set utf8;
create table e (d integer, n varchar(20));
insert into e values (1, 'zzz');
insert into e values (2, 'a');
insert into e values (3, 'bbbbbbbbbb');
insert into e values (1, 'yy');
commit;
create index e_d on e (d);
commit;
create table u (v varchar(10) character set utf8, d double precision, f decfloat(16), z timestamp with time zone);
insert into u values ('a', 0e0, 1.0, timestamp '2026-01-01 10:00 +00:00');
insert into u values ('a ', -0e0, 1.00, timestamp '2026-01-01 12:00 +02:00');
commit;
create table t (id int not null, a int not null, b int);
create table t3 (id int, a int, b int, c int);
create table t1 (id int);
create table t2 (x int, g int);
set term ^;
execute block as declare i int = 0; begin
  while (i < 1000000) do begin insert into t values (:i, mod(:i, 100), :i); i = i + 1; end
  i = 0;
  while (i < 100000) do begin insert into t3 values (:i, mod(:i, 1000), mod(:i * 7, 1000), mod(:i * 13, 1000)); i = i + 1; end
  i = 0;
  while (i < 20000) do begin insert into t1 values (:i); i = i + 1; end
  i = 0;
  while (i < 100) do begin insert into t2 values (:i, mod(:i, 10)); i = i + 1; end
end^
set term ;^
commit;
create index t_a on t (a);
create index ta on t3 (a); create index tb on t3 (b); create index tc on t3 (c);
create index t2_g on t2 (g);
commit;
set statistics index t_a; set statistics index ta; set statistics index tb; set statistics index tc; set statistics index t2_g;
commit;

set explain on;
select 'A2' as t, d, max(n), min(n) from e group by d;
select 'A3v' as t, count(*) from (select distinct v from u);
select 'A3d' as t, count(*) from (select distinct d from u);
select 'A3f' as t, count(*) from (select distinct f from u);
select 'A3z' as t, count(*) from (select distinct z from u);
set stats on;
select 'A6' as t, count((select first 1 g from t2 where t2.x <= t1.id group by g)) from t1;
select 'A7' as t, count(*) from (select distinct a, b, c from t3);
select 'B1a' as t, x.* from (select first 1 a, count(*) c from t group by a) x;
select 'B1b' as t, 1 from rdb$database where exists (select a from t group by a having count(*) > 1);
select 'B1c' as t, x.* from (select first 1 a, count(*) c from t group by a order by a) x;
set stats off;
select 'B2' as t, count(*) from (select a, count(*) c from t group by a plan (t order t_a));
set planonly on;
select distinct id, b from t order by id, b;
set planonly off;
set explain off;
set plan on;
set planonly on;
select distinct v from u;
set planonly off;
set plan off;
set explain on;
select 'A1' as t, count(*), sum(c) from (select id, count(*) c from t where id < 150000 group by id);
set explain off;
commit;
drop database;
