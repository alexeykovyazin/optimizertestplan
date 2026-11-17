-- 64_hash_join_condition.sql - the verification condition of the hash joins of one river. Alias tst12hj (ShowExplainCardinality = true).
-- Before: the condition of every hash join held the equalities of all the prior joins of the river, and the filter above the
-- river evaluated all of them once more per joined row. After: a join verifies its own equalities only, the ones implied by
-- the prefix are dropped, the filter does not repeat them. The results must not change.
-- p: 20 000 rows (id 0..19999, 100 rows with id NULL). b: 400 000 rows, pid = mod(i, 20000), every 1000th pid NULL.
-- g: 4 500 000 rows, pid = mod(i * 7919, 100000), every 1000th pid NULL (more than the in-memory hash capacity: BHJ).
-- Expected counts are computed by the nested loop plans of the same queries (section N) and by the arithmetic in the comments.
set bail off;
create database 'tst12hj' user SYSDBA;
create table p (id int, f int);
create table b (id int not null, pid int, pid8 bigint, pids varchar(10));
create table g (id int not null, pid int, pid8 bigint, pids varchar(10));
create table c1 (id int not null, s varchar(10) character set utf8 collate unicode_ci);
create table c2 (id int not null, s varchar(10) character set utf8);
create table c3 (id int not null, s varchar(10) character set utf8);
commit;
set term ^;
execute block as declare i int = 0; declare k int; begin
  while (i < 20000) do begin insert into p values (:i, mod(:i, 100)); i = i + 1; end
  i = 0;
  while (i < 100) do begin insert into p values (null, :i); i = i + 1; end
  i = 0;
  while (i < 400000) do begin
    k = iif(mod(i, 1000) = 999, null, mod(i, 20000));
    insert into b values (:i, :k, :k, :k);
    i = i + 1;
  end
  i = 0;
  while (i < 4500000) do begin
    k = iif(mod(i, 1000) = 999, null, mod(i * 7919, 100000));
    insert into g values (:i, :k, :k, :k);
    i = i + 1;
  end
  i = 0;
  while (i < 30000) do begin
    insert into c1 values (:i, 'k' || mod(:i, 3000));
    insert into c2 values (:i, iif(mod(:i, 2) = 0, 'k', 'K') || mod(:i, 3000));
    insert into c3 values (:i, iif(mod(:i, 3) = 0, 'k', 'K') || mod(:i, 3000));
    i = i + 1;
  end
end^
set term ;^
commit;
create index p_id on p (id); create index b_pid on b (pid); create index g_pid on g (pid);
create index b_pid8 on b (pid8); create index g_pid8 on g (pid8);
create index b_pids on b (pids); create index g_pids on g (pids);
create index c1_s on c1 (s); create index c2_s on c2 (s); create index c3_s on c3 (s);
commit;

select 'H1: star join on one key, plans' as tag from rdb$database;
set explain on; set planonly on;
select count(*) from p, b, g where p.id = b.pid and p.id = g.pid;
select count(*) from p, b, g where p.id = b.pid and b.pid = g.pid;
set planonly off; set explain off;

select 'H1: star join on one key, results' as tag from rdb$database;
select count(*), sum(cast(g.id as bigint)), sum(cast(b.id as bigint)), sum(cast(p.f as bigint)) from p, b, g where p.id = b.pid and p.id = g.pid;
select count(*), sum(cast(g.id as bigint)), sum(cast(b.id as bigint)), sum(cast(p.f as bigint)) from p, b, g where p.id = b.pid and b.pid = g.pid;
select count(*), sum(cast(g.id as bigint)) from p, b, g where p.id = b.pid and p.id = g.pid and b.pid = g.pid and g.id < 2000000;

select 'H2: IS NOT DISTINCT FROM keeps the NULL keys' as tag from rdb$database;
select count(*) from p, b where p.id is not distinct from b.pid and p.f < 2;
select count(*) from p, b, g where p.id = b.pid and p.id = g.pid and g.pid is not distinct from b.pid and g.id < 1000000;

select 'H3: mixed types in one class (int, bigint, varchar): nothing is dropped' as tag from rdb$database;
set explain on; set planonly on;
select count(*) from p, b, g where p.id = b.pid8 and p.id = g.pid8;
select count(*) from p, b, g where p.id = b.pids and p.id = g.pids and g.id < 1000000;
set planonly off; set explain off;
select count(*), sum(cast(g.id as bigint)) from p, b, g where p.id = b.pid8 and p.id = g.pid8;
select count(*), sum(cast(g.id as bigint)) from p, b, g where p.id = b.pid and b.pid = g.pid8 and g.id < 2000000;
select count(*), sum(cast(g.id as bigint)) from p, b, g where p.id = b.pids and p.id = g.pids and g.id < 1000000;

select 'H4: mixed collations in one class (unicode_ci, utf8, utf8)' as tag from rdb$database;
set explain on; set planonly on;
select count(*) from c1, c2, c3 where c1.s = c2.s and c1.s = c3.s;
set planonly off; set explain off;
select count(*), sum(c2.id), sum(c3.id) from c1, c2, c3 where c1.s = c2.s and c1.s = c3.s;
select count(*), sum(c2.id), sum(c3.id) from c1, c2, c3 where c2.s = c1.s and c2.s = c3.s;
select count(*), sum(c1.id), sum(c3.id) from c1, c2, c3 where c3.s = c1.s and c3.s = c2.s;

select 'H5: two classes on one stream' as tag from rdb$database;
select count(*), sum(cast(g.id as bigint)) from p, b, g where p.id = b.pid and p.id = g.pid and b.pid8 = g.pid8 and g.id < 2000000;
select count(*), sum(cast(g.id as bigint)) from p, b, g where p.id = b.pid and p.f = g.pid and b.pid8 = g.pid8 + 0 and g.id < 2000000;

select 'N: the same results by the nested loops' as tag from rdb$database;
select count(*), sum(cast(g.id as bigint)) from p, b, g where p.id = b.pid and p.id = g.pid and b.pid = g.pid and g.id < 2000000
  plan join (p natural, b index (b_pid), g index (g_pid));
select count(*), sum(cast(g.id as bigint)) from p, b, g where p.id = b.pid and b.pid = g.pid8 and g.id < 2000000
  plan join (p natural, b index (b_pid), g index (g_pid8));
select count(*), sum(c2.id), sum(c3.id) from c1, c2, c3 where c1.s = c2.s and c1.s = c3.s
  plan join (c1 natural, c2 index (c2_s), c3 index (c3_s));
commit;
drop database;
