-- 60_corr_subq_outer_eq.sql - correlated subquery: the equality on the outer stream field keeps its index (fix y20). Alias tst10desc.
-- The outer stream of a correlated subquery is compiled after the subquery: its cardinality is zero there,
-- and the join pair estimate was floored to selectivity 1 (no filter). The equality index then lost to any
-- range index of the same dependency count.
-- item 30 000 rows: oid nearly unique (~30 000 values), pid skewed (1..3 hold 2 500 rows each, the rest 1..5000)
-- dup 5 000 rows (id 1..5000), empt empty (count(...) = 0, so pid >= 0 keeps every row).
-- Each query: tag with the real count and the run statistics, then the plan with estimates (set planonly).
set bail off;
set names utf8;
create database 'tst10desc' user SYSDBA;
create table item (id int not null primary key, oid int, pid int, n int);
create table dup (id int not null primary key, k int, v int);
create table empt (id int not null primary key, k int, s varchar(20));
commit;
set term ^;
execute block as declare i int = 1; begin
  while (i <= 30000) do begin
    insert into item values (:i, mod(:i*3,50000) + 1, iif(mod(:i,4) = 0, 1 + mod(:i,3), mod(:i*11,5000) + 1), mod(:i,50));
    i = i + 1; end
  i = 1;
  while (i <= 5000) do begin
    insert into dup values (:i, mod(:i,1000), mod(:i*7,5000) + 1);
    i = i + 1; end
end^
set term ;^
commit;
create index item_oid on item(oid);
create index item_pid on item(pid);
create index item_n on item(n);
commit;
alter database add extended statistics; commit;
alter database refresh statistics; commit;
connect 'tst10desc' user SYSDBA;
set local_timeout 120000;

-- ===== fixed cases =====
select 'F1 not exists, bound = invariant subquery (expected 1667)' as tag, count(*) as real_cnt from dup d where not exists (select 1 from item i where i.oid = d.id and i.pid >= (select count(e.k) from empt e where e.s containing 'K'));
set planonly on; set explain on;
select count(*) from dup d where not exists (select 1 from item i where i.oid = d.id and i.pid >= (select count(e.k) from empt e where e.s containing 'K'));
set explain off; set planonly off; set plan off;
set stats on;
select 'F1 timing' as tag, count(*) as real_cnt from dup d where not exists (select 1 from item i where i.oid = d.id and i.pid >= (select count(e.k) from empt e where e.s containing 'K'));
set stats off;
select 'F2 exists, bound = outer field d.k' as tag, count(*) as real_cnt from dup d where exists (select 1 from item i where i.oid = d.id and i.pid >= d.k);
set planonly on; set explain on;
select count(*) from dup d where exists (select 1 from item i where i.oid = d.id and i.pid >= d.k);
set explain off; set planonly off; set plan off;
set stats on;
select 'F2 timing' as tag, count(*) as real_cnt from dup d where exists (select 1 from item i where i.oid = d.id and i.pid >= d.k);
set stats off;
-- estimate only: the subquery equality alone (rows= per probe)
set planonly on; set explain on;
select 'F3' t, count(*) from dup d where exists (select 1 from item i where i.oid = d.id);
select 'F4' t, count(*) from dup d where exists (select 1 from item i where i.oid = d.id and i.pid >= ?);
select 'F5' t, count(*) from dup d where exists (select 1 from item i where i.oid = d.id and i.pid >= (select 0 from rdb$database));
set explain off; set planonly off; set plan off;

-- ===== controls (plans and estimates must not change) =====
set planonly on; set explain on;
select 'C1' t, count(*) from item i where i.oid = 5 and i.pid >= (select count(e.k) from empt e where e.s containing 'K');
select 'C2' t, count(*) from item i where i.oid = ? and i.pid >= ?;
select 'C3' t, count(*) from item i where i.oid = 5 and i.pid >= 0;
select 'C4' t, count(*) from dup d join item i on i.oid = d.id;
select 'C5' t, count(*) from dup d join item i on i.oid = d.id and i.pid >= d.k;
select 'C6' t, count(*) from dup d join item i on i.oid = d.id and i.pid >= d.k plan join (d natural, i index (item_oid));
select 'C7' t, count(*) from dup d where exists (select 1 from item i join dup d2 on d2.id = i.oid where i.pid >= d.k and d2.k = 5);
select 'C8' t, count(*) from dup d where not exists (select 1 from item i where i.oid = d.id and i.pid >= 0);
set explain off; set planonly off; set plan off;
