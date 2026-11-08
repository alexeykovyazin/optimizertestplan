-- 34_eqjoin_min.sql - a3cfa97218 (57ff1378e1): min() of the two directional
-- totals of the equi-join estimate falls to 1 row when one side has all its
-- values in the MCV list and these values are in the tail of the other side.
-- Real COUNT = 1000. f2888abf7c estimates 1000 rows, a3cfa97218 estimates 1 row.
-- The partial-overlap case (pf2, pd2) is not affected: real 500500.
-- Alias tst8eq: ExtendedStatistics = true, ShowExplainCardinality = true.
create database 'tst8eq' user SYSDBA;
alter database add extended statistics;
commit;
-- pf: 50000 rows on 50 hot values 100001..100050 (1000 each), 50000 unique rows 1..50000
-- pd: 1000 rows, values 1..10 (100 each): all values in MCV, no tail
create table pf(k int);
create table pd(k int);
-- pf2/pd2: partial overlap: pf2 hot values 1..5 and 100001..100045, tail 6..50005
create table pf2(k int);
create table pd2(k int);
set term ^;
execute block as declare i int = 0; begin
  while (i < 100000) do begin
    insert into pf values(iif(:i < 50000, 100001 + mod(:i, 50), :i - 50000 + 1));
    insert into pf2 values(iif(:i < 50000, iif(mod(:i, 50) < 5, mod(:i, 50) + 1, 100001 + mod(:i, 50)), :i - 50000 + 6));
    if (i < 1000) then begin
      insert into pd values(mod(:i, 10) + 1);
      insert into pd2 values(mod(:i, 10) + 1);
    end
    i = i + 1;
  end
end^
set term ;^
commit;
alter database refresh statistics;
commit;

set explain on;
-- D1: real 1000
select count(*) from pf join pd on pf.k = pd.k;
-- D2: real 500500
select count(*) from pf2 join pd2 on pf2.k = pd2.k;
