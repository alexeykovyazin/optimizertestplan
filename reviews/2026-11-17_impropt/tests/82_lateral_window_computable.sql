-- Test 82: a LATERAL derived table with a window function or an aggregate keeps the join above it.
-- Change: the fix of the suite horses-fdb, defect 1 (optimizer notes 4.54). The merge of v5.0-release
-- (02cd04a4f7, the fix of #8628 extended to aggregates and window functions) checks the expressions of the map
-- of a window or of an aggregate by computable(). The streams of the select of the derived table are active only
-- inside rse->computable(), so a reference to a table of that select read as not computable. The whole LATERAL
-- source was refused for ever: the join with the next table (COVER) became a nested loop with a full scan of
-- COVER for every row of HORSE (horses_fdb_01: 9.96 s on vanilla 5.0, no end in 2 hours on the branch).
-- The fix activates the streams of the select around the check of the map.
-- Every "diff" case compares the count of the query with its reference: the lateral gives one row per horse
-- (LEFT JOIN, FETCH FIRST ROW ONLY or an aggregate), so the count is the sum of MAX(1, covers of the horse).
-- Expected: every "diff" row gives 0.
-- Expected plans (the build with the fix): the top join of L1 is "Hash Join (outer)" with "Table "COVER" Full
-- Scan" under its "Record Buffer"; the build before the fix gives "Nested Loop Join (outer)" with "Table "COVER"
-- Full Scan" as the inner stream of the loop (6 s here, 828 s at 60 000 horses). L2 (an aggregate) and L3 (COVER
-- by an inner join) are the control cases: the same plans on both builds.
set bail off;
create database 'tst2def' user SYSDBA default character set utf8;
create table horse (code_horse int not null primary key, name varchar(40));
create table farm (code_farm int not null primary key, code_country int);
create table registration (code_reg int not null primary key, code_horse int not null, code_regtype int not null,
  code_farm int not null, bydate date);
create table cover (code_cover int not null primary key, code_horse int not null, bydate date);
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 400) do begin
    insert into farm values (:i, mod(:i, 30));
    i = i + 1;
  end
  i = 0;
  while (i < 3000) do begin
    insert into horse values (:i, 'horse ' || :i);
    i = i + 1;
  end
  i = 0;
  while (i < 12000) do begin
    insert into registration values (:i, mod(:i * 7, 3000), mod(:i, 4), mod(:i * 13, 400),
      dateadd(mod(:i, 3000) day to date '2015-01-01'));
    i = i + 1;
  end
  i = 0;
  while (i < 8000) do begin
    insert into cover values (:i, mod(:i * 11, 2250), dateadd(mod(:i, 2000) day to date '2016-01-01'));
    i = i + 1;
  end
end^
set term ;^
commit;
alter table registration add constraint fk_registration_horse foreign key (code_horse) references horse (code_horse);
alter table registration add constraint fk_registration_farm foreign key (code_farm) references farm (code_farm);
alter table cover add constraint fk_cover_horse foreign key (code_horse) references horse (code_horse);
create index registration_idx_horse_regtype on registration (code_horse, code_regtype);
commit;

-- the reference: one row per horse times the covers of the horse
create view ref (n) as
  select sum(iif(c = 0, 1, c)) from (select (select count(*) from cover c where c.code_horse = h.code_horse) c
                                      from horse h);
commit;

set explain on;
-- L1: the query of the report - a window function in the lateral, then COVER
select 'L1 diff' as t, (select n from ref) - count(*) from horse h
  left join lateral (
    select regs.bydate, regs.prev_code_country as code_import_country
    from (
      select r.bydate, r.code_farm, farm.code_country,
             lag(farm.code_country) over (order by r.bydate) as prev_code_country
      from registration r join farm on farm.code_farm = r.code_farm
      where r.code_horse = h.code_horse and r.code_regtype = 2 and farm.code_country > 0
    ) regs
    where regs.code_country is distinct from regs.prev_code_country
    order by regs.bydate
    fetch first row only
  ) import_info on true
  left join cover on cover.code_horse = h.code_horse;

-- L2: an aggregate in the lateral, then COVER
select 'L2 diff' as t, (select n from ref) - count(*) from horse h
  left join lateral (
    select min(r.bydate) as bydate, count(*) as regs from registration r
    where r.code_horse = h.code_horse and r.code_regtype = 2
  ) import_info on true
  left join cover on cover.code_horse = h.code_horse;

-- L3: a window function with a partition in the lateral, COVER by an inner join
select 'L3 diff' as t,
  (select count(*) from horse h join cover c on c.code_horse = h.code_horse) - count(*) from horse h
  left join lateral (
    select r.bydate, row_number() over (partition by r.code_regtype order by r.bydate) as rn
    from registration r
    where r.code_horse = h.code_horse
    order by r.bydate
    fetch first row only
  ) import_info on true
  join cover on cover.code_horse = h.code_horse;
set explain off;

-- the values of the lateral do not depend on the join above it
select 'L4 diff' as t, count(*) from (
  select h.code_horse, import_info.bydate from horse h
    left join lateral (
      select min(r.bydate) as bydate from registration r
      where r.code_horse = h.code_horse and r.code_regtype = 2
    ) import_info on true
    left join cover on cover.code_horse = h.code_horse
) a
where a.bydate is distinct from (select min(r.bydate) from registration r
                                  where r.code_horse = a.code_horse and r.code_regtype = 2);
