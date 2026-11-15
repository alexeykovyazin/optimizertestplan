-- 43b_bhj_lost_rows_def.sql - Y1 (8a574656ba): Batch Hash Join loses rows when a probe batch follows a batch with <= 16384 leading rows (stale hash chunk). Alias tst10bhj_def (default config, no ExtendedStatistics).
-- Data: h = 4 200 000 rows (id 1..4200000), no index -> hashed side > 4M rows -> BHJ with 8 batches.
-- a = 4 500 000 rows; fk is not NULL in 20 000 rows (fk = i/225 for i mod 225 = 0), k8 is not NULL in 8 rows (k8 = 1..8).
-- Every not-NULL key matches exactly one row of h. Expected: fk -> 20000 rows, sum 200010000; k8 -> 8 rows, sum 36.
set bail on;
create database 'tst10bhj_def' user SYSDBA;
create table h (id int);
create table a (id int, fk int, k8 int);
commit;
set term ^;
execute block as declare i int = 1; begin
  while (i <= 4200000) do begin insert into h values (:i); i = i + 1; end
  i = 1;
  while (i <= 4500000) do begin
    insert into a values (:i, iif(mod(:i, 225) = 0, :i / 225, null), iif(mod(:i, 562500) = 0, :i / 562500, null));
    i = i + 1;
  end
end^
set term ;^
commit;
connect 'tst10bhj_def' user SYSDBA;
set bail off;

-- ===== R: independent reference (no join; every key 1..4200000 exists in h) =====
select 'R1 fk expected (20000 | 200010000)' as tag, count(*) as expected_cnt, sum(cast(fk as bigint)) as expected_sum
  from a where fk between 1 and 4200000;
select 'R2 k8 expected (8 | 36)' as tag, count(*) as expected_cnt, sum(cast(k8 as bigint)) as expected_sum
  from a where k8 between 1 and 4200000;

-- ===== plan: must be Batch Hash Join (batches: 8) =====
set explain on;
set planonly on;
select count(*), sum(cast(h.id as bigint)) from a join h on h.id = a.fk;
set planonly off;
set explain off;
set plan off;

-- ===== Q: the join =====
select 'Q1 a join h on fk' as tag, count(*) as cnt, sum(cast(h.id as bigint)) as sum_id from a join h on h.id = a.fk;
select 'Q2 a join h on k8' as tag, count(*) as cnt, sum(cast(h.id as bigint)) as sum_id from a join h on h.id = a.k8;
select 'Q3 duplicates check fk' as tag, count(*) as cnt, count(distinct a.id) as cnt_distinct from a join h on h.id = a.fk;
