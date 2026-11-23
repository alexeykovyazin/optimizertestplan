-- Test 81: a single MIN or MAX without GROUP BY over a join keeps the counted streams.
-- Change: the fix of step 3.1 (optimizer notes 4.51, 4.40). An aggregate with a single MIN or MAX requests a sort
-- block before the compilation of its input (the index shortcut of MIN/MAX). The rule of the row weights refuses
-- such an aggregate at that moment. The optimizer drops the block when no index delivers the order, and the rule
-- must be asked again after the compilation. Step 3.1 kept the first answer, and the join lost its counting.
-- Found on the suite job (IMDb): 18 queries of 113 with a single MIN lost the mark "counted streams".
-- Every "diff" case joins the query with its reference: the same query with COUNT(DISTINCT), which the counting
-- never takes. The join condition keeps the rows whose values differ.
-- Expected: every "diff" row gives 0; "M5 val" gives 0.
-- Expected plans (the build with the fix): the mark "counted streams: 1" of the hash join in the first derived
-- table of M1 and M2 (a single MIN, a single MAX), of M3 (two aggregates: the control case, counted before the
-- fix too) and of M4 (the hashed table of 40 rows). M5 (one table, MIN of the primary key) keeps the index
-- shortcut: no join, no mark.
set bail off;
create database 'tst2def' user SYSDBA default character set utf8;
create table t (id int not null primary key, k int not null, m int not null, s varchar(30), v numeric(18,2));
create table d (id int not null primary key, name varchar(20));
set term ^;
execute block as declare i int = 0; begin
  while (i < 60000) do begin
    insert into t values (:i, mod(:i, 40), mod(:i * 7, 3000), 'name' || mod(:i, 500), :i / 3.0);
    i = i + 1;
  end
  i = 0;
  while (i < 40) do begin
    insert into d values (:i, 'd' || :i);
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
-- the join gives 1 200 000 rows; the table B is hashed and nothing refers to it
select 'M1 diff' as t, count(*) from (select min(a.s) x from t a join t b on b.m = a.m) p
  join (select x from (select min(a.s) x, count(distinct b.m) y from t a join t b on b.m = a.m)) q
    on q.x is distinct from p.x;
select 'M2 diff' as t, count(*) from (select max(a.v) x from t a join t b on b.m = a.m) p
  join (select x from (select max(a.v) x, count(distinct b.m) y from t a join t b on b.m = a.m)) q
    on q.x is distinct from p.x;
select 'M3 diff' as t, count(*) from (select min(a.s) x, max(a.v) z from t a join t b on b.m = a.m) p
  join (select x, z from (select min(a.s) x, max(a.v) z, count(distinct b.m) y from t a join t b on b.m = a.m)) q
    on q.x is distinct from p.x or q.z is distinct from p.z;
select 'M4 diff' as t, count(*) from (select min(a.s) x from t a join d on d.id = a.k + 0) p
  join (select x from (select min(a.s) x, count(distinct d.id) y from t a join d on d.id = a.k + 0)) q
    on q.x is distinct from p.x;
select 'M5 val' as t, min(a.id) from t a;
set explain off;
