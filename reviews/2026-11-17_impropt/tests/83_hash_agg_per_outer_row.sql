-- Test 83: a hash aggregation opened once per outer row sizes its table by its input.
-- Change: the fix of the suite horses-fdb, defect 2 (optimizer notes 4.55). A derived table with GROUP BY under
-- a nested loop gets the grouping column bound to the outer row: an open reads a few rows of an index range.
-- HashAggregateStream created the hash table of every open with the size of the estimate of the groups, and the
-- estimate comes from the whole table. 60 000 opens paid 60 000 allocations of the whole-table size
-- (horses_fdb_08: 3.96 s on the build before the hash aggregation, 54 s with it). The fix sizes the table of an
-- open by MIN(estimate, budget, rows of the compiled input); an estimate too low costs a rehash only.
-- Every "diff" case compares the derived table with its reference: the correlated subquery of the same value.
-- Expected: every "diff" row gives 0.
-- The second fix (optimizer notes 4.56): the gate of the hash aggregation sees the conjunct of the query above
-- that binds a grouped column to the outer row (G1, G2): one value per open, the index navigation delivers the
-- groups in order and needs no table at all - the plan of the build before the hash aggregation.
-- Expected plans: "Nested Loop Join (outer)" with "Aggregate" over the index navigation of REGISTRATION in G1 and
-- G2; "Hash Aggregate" in G3.
-- Expected times (set stats): every query below 1 s; the build before the fixes: about 7 s for G1 and G2.
set bail off;
create database 'tst2def' user SYSDBA default character set utf8;
create table horse (code_horse int not null primary key, name varchar(40));
create table registration (code_reg int not null primary key, code_horse int not null, code_regtype int not null,
  bydate date);
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 60000) do begin
    insert into horse values (:i, 'horse ' || :i);
    i = i + 1;
  end
  i = 0;
  while (i < 120000) do begin
    insert into registration values (:i, mod(:i * 7, 60000), mod(:i, 8),
      dateadd(mod(:i, 3000) day to date '2015-01-01'));
    i = i + 1;
  end
end^
set term ;^
commit;
alter table registration add constraint fk_registration_horse foreign key (code_horse) references horse (code_horse);
create index registration_idx_horse_regtype on registration (code_horse, code_regtype);
commit;
-- the gate of the hash aggregation takes the distinct counts of the extended statistics
alter database add extended statistics;
commit;
alter database refresh statistics;
commit;

set explain on;
set stats on;
-- G1: MIN by a group of one column, joined by the grouping column
select 'G1 diff' as t, count(*) from horse h
  left join (
    select r.code_horse, min(r.bydate) as bydate from registration r
    where r.code_regtype = 6 group by r.code_horse
  ) g on g.code_horse = h.code_horse
where g.bydate is distinct from (select min(r.bydate) from registration r
                                  where r.code_horse = h.code_horse and r.code_regtype = 6);

-- G2: COUNT and MAX by a group of two columns
select 'G2 diff' as t, count(*) from horse h
  left join (
    select r.code_horse, r.code_regtype, count(*) as regs, max(r.bydate) as bydate from registration r
    group by r.code_horse, r.code_regtype
  ) g on g.code_horse = h.code_horse and g.code_regtype = 6
where g.regs is distinct from (select nullif(count(*), 0) from registration r
                                where r.code_horse = h.code_horse and r.code_regtype = 6)
   or g.bydate is distinct from (select max(r.bydate) from registration r
                                  where r.code_horse = h.code_horse and r.code_regtype = 6);

-- G3: a lateral grouped by a column the outer row does not bind: the hash aggregation stays, every open reads
-- the few rows of one horse and its table is sized by them
select 'G3 diff' as t,
  (select sum(iif(c = 0, 1, c)) from (select (select count(distinct r.bydate) from registration r
                                               where r.code_horse = h.code_horse) c from horse h)) - count(*)
from horse h
  left join lateral (
    select r.bydate, count(*) as regs, max(r.code_regtype) as regtype from registration r
    where r.code_horse = h.code_horse
    group by r.bydate
  ) g on true;
set stats off;
set explain off;
