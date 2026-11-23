-- Test 84: the price of the navigational walk to the first matching record (optimizer notes 4.8).
-- Change: the first-rows branch of the ORDER vs SORT choice. The walk to the first match was priced by its leaf
-- pages only (the share 1 / matching records of the index pages): 12 units for the ordering index of a table of
-- 400 000 rows with 16.6 matching rows, against 40 units of the sort. The walk really visits
-- keys / (matching + 1) keys, checks each against the bitmap, and visits the whole index when no row matches.
-- A LATERAL derived table with ORDER BY ... FETCH FIRST ROW ONLY, or with one MIN, walked the index by BYDATE
-- for every row of HORSE (horses_fdb_06 and horses_fdb_07).
-- The fix prices the walked keys (COST_NAV_KEY each), the records fetched during the walk and, on the sort side,
-- the fetch of all its records.
-- Expected plans (the build with the fix):
--   N1: "Sort" over "REGISTRATION_IDX_HORSE_REGTYPE", no "REGISTRATION_IDX_BYDATE";
--   N2: "Aggregate" over "REGISTRATION_IDX_HORSE_REGTYPE", no "REGISTRATION_IDX_BYDATE";
--   C1, C2, C3 (controls, many matching rows or no filter): the navigation by "REGISTRATION_IDX_BYDATE" stays.
-- The build before the fix: N1 and N2 walk "REGISTRATION_IDX_BYDATE" (85 s and 91 s here; under a second with
-- the fix). Expected results: N1 and N2 give 20000 and 4124 on both builds; in V the columns N1 and N2 are equal
-- to N1_REF and N2_REF (the values of the same queries in the forms that cannot navigate).
set bail off;
create database 'tst2def' user SYSDBA default character set utf8;
create table horse (code_horse int not null primary key);
create table registration (code_reg int not null primary key, code_horse int not null, code_regtype int not null,
  bydate date);
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 20000) do begin
    insert into horse values (:i);
    i = i + 1;
  end
  i = 0;
  while (i < 400000) do begin
    insert into registration values (:i, mod(:i * 7, 20000), iif(mod(:i, 97) = 0, 6, mod(:i, 5)),
      dateadd(mod(:i * 13, 5000) day to date '2010-01-01'));
    i = i + 1;
  end
end^
set term ;^
commit;
alter table registration add constraint fk_registration_horse foreign key (code_horse) references horse (code_horse);
create index registration_idx_horse_regtype on registration (code_horse, code_regtype);
create index registration_idx_bydate on registration (bydate);
commit;
alter database add extended statistics;
commit;
alter database refresh statistics;
commit;

set explain on;
set stats on;
-- N1: ORDER BY + FETCH FIRST in a lateral (horses_fdb_06)
select 'N1' as t, count(*), count(i.bydate) from horse h
  left join lateral (
    select r.bydate from registration r
    where r.code_horse = h.code_horse and r.code_regtype = 6
    order by r.bydate fetch first row only
  ) i on true;
-- N2: one MIN in a lateral (horses_fdb_07)
select 'N2' as t, count(*), count(i.bydate) from horse h
  left join lateral (
    select min(r.bydate) as bydate from registration r
    where r.code_horse = h.code_horse and r.code_regtype = 6
  ) i on true;
-- C1 (control): a non-indexed filter that a fifth of the rows passes - the navigation finds a row at once
select first 1 'C1' as t, r.bydate from registration r where r.code_regtype = 1 order by r.bydate;
-- C2 (control): no filter
select first 5 'C2' as t, r.bydate from registration r order by r.bydate;
-- C3 (control): an indexed filter that half of the rows passes
select first 1 'C3' as t, r.bydate from registration r where r.code_horse < 10000 order by r.bydate;
set stats off;
set explain off;
-- V: the values of N1 and N2 for 2000 horses against the forms that cannot navigate
select 'V' as t,
  (select sum(datediff(day from date '2010-01-01' to i.bydate)) from horse h left join lateral (
    select r.bydate as bydate from registration r
    where r.code_horse = h.code_horse and r.code_regtype = 6 order by r.bydate fetch first row only) i on true
    where h.code_horse < 2000) as n1,
  (select sum(datediff(day from date '2010-01-01' to i.bydate)) from horse h left join lateral (
    select r.bydate as bydate from registration r
    where r.code_horse = h.code_horse and r.code_regtype = 6 order by r.bydate + 0 fetch first row only) i on true
    where h.code_horse < 2000) as n1_ref,
  (select sum(datediff(day from date '2010-01-01' to i.bydate)) from horse h left join lateral (
    select min(r.bydate) as bydate from registration r
    where r.code_horse = h.code_horse and r.code_regtype = 6) i on true
    where h.code_horse < 2000) as n2,
  (select sum(datediff(day from date '2010-01-01' to i.bydate)) from horse h left join lateral (
    select min(r.bydate + 0) as bydate from registration r
    where r.code_horse = h.code_horse and r.code_regtype = 6) i on true
    where h.code_horse < 2000) as n2_ref
from rdb$database;
