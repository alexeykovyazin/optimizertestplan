-- 67_hj_price_form.sql - the hash join is priced in the form it is built in. Alias tst17hjprice
-- (ShowExplainCardinality = true, TempCacheLimit by default).
-- big: 5 000 000 rows (above the capacity of the hash table, 4 000 012), id is the primary key, f = mod(id, 100).
-- lead: 3 000 000 rows, id only.
-- The filter big.f < 5 leaves 250 000 rows: the hashed side fits the hash table, formRiver() builds the plain
-- hash join. Before: estimateCost() priced the join as the batched one, because the table (not its filtered rows)
-- is above the capacity - every leader row paid the write and the read of the leader buffer. The nested loop of
-- 3 000 000 primary key lookups looked cheaper and was chosen.
-- Expected: Hash Join in P1 and P2; the count of R1 is 150 000 on every build.
-- P3 is the control: without the filter and without a usable index the smaller table (lead) is hashed, the plan
-- is the same on both builds.
set bail off;
create database 'tst17hjprice' user SYSDBA;
create table big (id int not null primary key, f int);
create table lead (id int not null);
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 5000000) do begin insert into big values (:i, mod(:i, 100)); i = i + 1; end
  i = 0;
  while (i < 3000000) do begin insert into lead values (:i); i = i + 1; end
end^
set term ;^
commit;

select 'P: the plans' as tag from rdb$database;
set explain on; set planonly on;
-- P1: the filter leaves 5% of the big table
select count(*) from lead join big on big.id = lead.id where big.f < 5;
-- P2: the filter leaves 1%
select count(*) from lead join big on big.id = lead.id where big.f = 5;
-- P3: no filter, no index on the key expression
select count(*) from lead join big on big.id + 0 = lead.id;
set planonly off; set explain off;

select 'R: the results' as tag from rdb$database;
set stats on;
select 'R1', count(*), sum(cast(big.id as bigint)) from lead join big on big.id = lead.id where big.f < 5;
select 'R2', count(*), sum(cast(big.id as bigint)) from lead join big on big.id = lead.id where big.f = 5;
set stats off;
commit;
drop database;
