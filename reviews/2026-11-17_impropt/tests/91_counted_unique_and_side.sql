-- Test 91: the counted streams of a join: a stream with one match at most is not counted; the stream nothing
-- refers to is the hashed side of the first hash join.
-- Change: optimizer notes 4.67 and 4.68. Plan: PLAN-hash-aggregate-improvements.md, step 3.5 (the special case).
-- Every "diff" case compares the query with its sorted reference: the same query with COUNT(DISTINCT), which the
-- hash aggregation and the counting never take. Expected: every "diff" row gives 0.
-- Expected plans (the first branch of every case, the build with the change):
--   U1, U2, U5 - the table D or C is joined by all the columns of its primary key or unique index: no "Count"
--                node and no "counted streams" mark for it;
--   U3 - the unique index of U is matched by IS NOT DISTINCT FROM (the NULLs match, U has three rows with NULL):
--        the stream is counted as before;
--   U4 - one column of the two of a primary key: the stream is counted as before;
--   S1 - "counted streams: 1", the leader is B, the hashed table is A (before the change: A is the leader, no
--        mark);
--   S2 - the table nothing refers to (F, 1 000 000 rows) is much larger than the other one (D, 1 000 rows):
--        "counted streams: 1", the leader is D, the hashed table is F (before the change: F is the leader);
--   S3 - a text key: the stream would keep all its rows, the sides stay as the sizes choose (F is the leader);
--   S4 - three tables, a third table takes its key from A: the results only;
--   S5 - F has 500 000 key values and T matches 60 000 of them: the count does not pay, the sides stay (F is
--        the leader, no mark).
set bail off;
create database 'tst2def' user SYSDBA default character set utf8;
create table t (id int not null primary key, k int not null, m int not null, s varchar(30), v numeric(18,2), z int);
create table d (id int not null primary key, g int not null, m int not null, name varchar(30));
create table u (id int not null primary key, x int, constraint u_x unique (x));
create table p (a int not null, b int not null, w int, constraint p_pk primary key (a, b));
create table f (id int not null primary key, dim_id int not null, s int not null, c varchar(10) not null);
set term ^;
execute block as declare i int = 0; begin
  while (i < 60000) do begin
    insert into t values (:i, mod(:i, 40), mod(:i * 7, 3000), 'name' || mod(:i, 500), :i / 3.0,
      iif(mod(:i, 50) = 0, null, mod(:i, 700)));
    i = i + 1;
  end
  i = 0;
  while (i < 1000) do begin
    insert into d values (:i, mod(:i, 40), :i, 'd' || :i);
    i = i + 1;
  end
  i = 0;
  while (i < 600) do begin
    insert into u values (:i, iif(:i < 3, null, :i));
    i = i + 1;
  end
  i = 0;
  while (i < 4000) do begin
    insert into p values (mod(:i, 40), :i / 40, :i);
    i = i + 1;
  end
  i = 0;
  while (i < 1000000) do begin
    insert into f values (:i, mod(:i * 7, 1000), mod(:i * 11, 500000), 'd' || mod(:i * 7, 1000));
    i = i + 1;
  end
end^
set term ;^
commit;
create index t_k on t (k); create index t_m on t (m); create index t_z on t (z);
create index d_m on d (m); create index d_g on d (g);
create index f_dim on f (dim_id); create index f_s on f (s); create index f_c on f (c);
commit;

set explain on;
select 'U1 diff' as t, count(*) from (select k, n, w from (
    select a.k, count(*) n, sum(a.v) w from t a join d on d.id = a.k group by a.k
    union all
    select k, n, w from (select a.k, count(*) n, sum(a.v) w, count(distinct a.m) x
      from t a join d on d.id = a.k group by a.k))
  group by k, n, w having count(*) <> 2);
select 'U2 diff' as t, count(*) from (select k, n, w from (
    select a.k, count(*) n, sum(a.v) w from t a join t c on c.id = a.m where a.id < 300 group by a.k
    union all
    select k, n, w from (select a.k, count(*) n, sum(a.v) w, count(distinct a.m) x
      from t a join t c on c.id = a.m where a.id < 300 group by a.k))
  group by k, n, w having count(*) <> 2);
select 'U3 diff' as t, count(*) from (select k, n, w from (
    select a.k, count(*) n, sum(a.v) w from t a join u on u.x is not distinct from a.z group by a.k
    union all
    select k, n, w from (select a.k, count(*) n, sum(a.v) w, count(distinct a.m) x
      from t a join u on u.x is not distinct from a.z group by a.k))
  group by k, n, w having count(*) <> 2);
select 'U4 diff' as t, count(*) from (select k, n, w from (
    select a.k, count(*) n, sum(a.v) w from t a join p on p.a = a.k group by a.k
    union all
    select k, n, w from (select a.k, count(*) n, sum(a.v) w, count(distinct a.m) x
      from t a join p on p.a = a.k group by a.k))
  group by k, n, w having count(*) <> 2);
select 'U5 diff' as t, count(*) from (select k, n, w from (
    select a.k, count(*) n, sum(a.v) w from t a join u on u.x = a.z group by a.k
    union all
    select k, n, w from (select a.k, count(*) n, sum(a.v) w, count(distinct a.m) x
      from t a join u on u.x = a.z group by a.k))
  group by k, n, w having count(*) <> 2);
select 'S1 diff' as t, count(*) from (select k, n, w from (
    select b.k, count(*) n, sum(b.v) w from t a join t b on b.m = a.m group by b.k
    union all
    select k, n, w from (select b.k, count(*) n, sum(b.v) w, count(distinct a.m) x
      from t a join t b on b.m = a.m group by b.k))
  group by k, n, w having count(*) <> 2);
select 'S2 diff' as t, count(*) from (select g, n, w from (
    select d.g, count(*) n, sum(d.id) w from f join d on d.m = f.dim_id group by d.g
    union all
    select g, n, w from (select d.g, count(*) n, sum(d.id) w, count(distinct f.dim_id) x
      from f join d on d.m = f.dim_id group by d.g))
  group by g, n, w having count(*) <> 2);
select 'S3 diff' as t, count(*) from (select g, n, w from (
    select d.g, count(*) n, sum(d.id) w from f join d on d.name = f.c group by d.g
    union all
    select g, n, w from (select d.g, count(*) n, sum(d.id) w, count(distinct f.dim_id) x
      from f join d on d.name = f.c group by d.g))
  group by g, n, w having count(*) <> 2);
select 'S4 diff' as t, count(*) from (select k, n, w from (
    select b.k, count(*) n, sum(b.v) w from t a join t b on b.m = a.m join p on p.b = a.k + 0 and p.a = 1 group by b.k
    union all
    select k, n, w from (select b.k, count(*) n, sum(b.v) w, count(distinct a.m) x
      from t a join t b on b.m = a.m join p on p.b = a.k + 0 and p.a = 1 group by b.k))
  group by k, n, w having count(*) <> 2);
select 'S5 diff' as t, count(*) from (select k, n, w from (
    select b.k, count(*) n, sum(b.v) w from f join t b on b.id = f.s group by b.k
    union all
    select k, n, w from (select b.k, count(*) n, sum(b.v) w, count(distinct f.dim_id) x
      from f join t b on b.id = f.s group by b.k))
  group by k, n, w having count(*) <> 2);
set explain off;
select 'S1 rows' as t, count(*), sum(n) from (select b.k, count(*) n from t a join t b on b.m = a.m group by b.k);
select 'S2 rows' as t, count(*), sum(n) from (select d.g, count(*) n from f join d on d.m = f.dim_id group by d.g);
commit;
drop database;
