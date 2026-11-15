-- 55_blob_price_bounds.sql - blob predicate price (b69da49179): the cost is bounded (STAT$BLOB_AVG_PAGES = 1e308 must not give inf), the IN-list prices N comparisons. Alias tst10blob.
-- Data: e 50 000 rows, b0 = 'v' || mod(id, 50) (small text blobs, real count of each value 1 000); pr 5 000 probes, pr.e_id = mod(id * 7, 50000).
-- Real counts: pr join e where e.b0 like '%v1%' = 1 100 (v1, v10..v19 = 11 values of 50 -> 5000 * 11 / 50); in ('v1','v2','v3') = 300.
-- Part 1 (the bound): the same LIKE join with STAT$BLOB_AVG_PAGES = 1e300, 1e308, 2097152 (the cap: MAX_ULONG / 2048).
--   Before the fix: 1e300 -> PLAN JOIN (PR NATURAL, E INDEX (...)), 1e308 -> PLAN HASH (the cost is inf, inf <= inf picks the hash join).
--   After the fix: the three plans are the same (the nested loop of 1e300).
-- Part 2 (the IN-list, regression only): the IN-list now prices 3 blob comparisons per row instead of 2; the cost is not
--   printed and on this data the plan does not move: expected PLAN JOIN (PR NATURAL, E INDEX (RDB$PRIMARY1)),
--   Filter (rows=0.30) over E, count 300 - the same as before the fix. The N vs N-1 change is checked by the code.
set bail off;
create database 'tst10blob' user SYSDBA;
create table e (id int primary key, b0 blob sub_type text);
create table pr (id int primary key, e_id int);
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 50000) do begin insert into e values (:i, 'v' || mod(:i, 50)); i = i + 1; end
  i = 0;
  while (i < 5000) do begin insert into pr values (:i, mod(:i * 7, 50000)); i = i + 1; end
end^
set term ;^
commit;
alter database add extended statistics; commit;
alter database refresh statistics; commit;

select 'P1: AVG_PAGES = 1e300' as tag from rdb$database;
update STAT$COLUMNS set STAT$BLOB_AVG_PAGES = 1e300 where STAT$RELATION_NAME = 'E' and STAT$FIELD_NAME = 'B0'; commit;
connect 'tst10blob' user SYSDBA;
set planonly on;
select count(*) from pr join e on e.id = pr.e_id where e.b0 like '%v1%';
set planonly off;

select 'P1: AVG_PAGES = 1e308' as tag from rdb$database;
update STAT$COLUMNS set STAT$BLOB_AVG_PAGES = 1e308 where STAT$RELATION_NAME = 'E' and STAT$FIELD_NAME = 'B0'; commit;
connect 'tst10blob' user SYSDBA;
set planonly on;
select count(*) from pr join e on e.id = pr.e_id where e.b0 like '%v1%';
set planonly off;
select count(*) from pr join e on e.id = pr.e_id where e.b0 like '%v1%';

select 'P1: AVG_PAGES = 2097152 (the cap)' as tag from rdb$database;
update STAT$COLUMNS set STAT$BLOB_AVG_PAGES = 2097152 where STAT$RELATION_NAME = 'E' and STAT$FIELD_NAME = 'B0'; commit;
connect 'tst10blob' user SYSDBA;
set planonly on;
select count(*) from pr join e on e.id = pr.e_id where e.b0 like '%v1%';
set planonly off;

select 'P2: real AVG_PAGES, IN-list (regression: same plan and count)' as tag from rdb$database;
alter database refresh statistics; commit;
connect 'tst10blob' user SYSDBA;
set explain on;
set planonly on;
select count(*) from pr join e on e.id = pr.e_id where e.b0 in ('v1', 'v2', 'v3');
set planonly off;
set explain off;
select count(*) from pr join e on e.id = pr.e_id where e.b0 in ('v1', 'v2', 'v3');
