-- 33_sort_bhj.sql - a3cfa97218 (91564c44db): when the batched hash join gives
-- the sort back to the caller, the second formRiver pass loses the WHERE
-- filters of the streams it builds again: ORDER BY returns rows that fail WHERE.
-- f2888abf7c returns 36000000 rows (max 600000) in both queries.
-- a3cfa97218 returns 48000000 rows (max 800000) with ORDER BY.
-- Alias tst8sort: ExtendedStatistics = true, ShowExplainCardinality = true.
-- Setup inserts 5 million rows (about 1-2 minutes).
create database 'tst8sort' user SYSDBA page_size 8192;
alter database add extended statistics;
commit;
-- rc: 800k rows, x = id (index for the ORDER BY navigation), g = join key
create table rc (id int, x int, g int);
-- rb: 4.2M rows, 60 rows per key g
create table rb (id int, g int);
commit;
set term ^;
execute block as declare i int = 1; begin
  while (i <= 800000) do begin insert into rc values(:i, :i, mod(:i, 70000) + 1); i = i + 1; end
  i = 1;
  while (i <= 4200000) do begin insert into rb values(:i, mod(:i, 70000) + 1); i = i + 1; end
end^
set term ;^
commit;
create index rc_x on rc(x);
create index rb_g on rb(g);
commit;
alter database refresh statistics;
commit;

set explain on;
-- C1: with ORDER BY. Expected 36000000 / 600000.
select count(*), max(x) from (select rc.x from rc join rb on rb.g = rc.g where rc.x < 600001 order by rc.x);
-- C2: without ORDER BY. Expected 36000000 / 600000.
select count(*), max(x) from (select rc.x from rc join rb on rb.g = rc.g where rc.x < 600001);
