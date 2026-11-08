-- 31_oj_parent.sql - a3cfa97218 (7426e92a7a): the outer hash join takes
-- conjuncts that do not belong to it into its ON condition.
-- f2888abf7c gives the expected counts. a3cfa97218 gives errors and wrong counts.
-- Alias tst8oj: ExtendedStatistics = true, ShowExplainCardinality = true.
-- No extended statistics are collected: the bug does not need them.
create database 'tst8oj' user SYSDBA;
create table oa(x int, z int);
create table ob(x int, y int);
create table oc(k int, w int);
set term ^;
execute block as declare i int = 0; begin
  while (i < 20000) do begin
    insert into oa values(:i, 10);
    insert into ob values(:i, mod(:i, 20));
    insert into oc values(:i, 10);
    i = i + 1;
  end
end^
set term ;^
commit;

set explain on;
-- A1: LEFT JOIN, then INNER JOIN on an outer-stream column. Expected 20000 / 20000.
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x join oc on oc.k = oa.x;
-- A2: the same with a non-equi ON condition. Expected 20000 / 9000.
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and ob.y > oa.z join oc on oc.k = oa.x;
-- A3: INNER JOIN first. Expected 20000 / 20000.
select count(*), count(ob.x) from oc join oa on oc.k = oa.x left join ob on oa.x = ob.x;
set explain off;

-- B: ANY/ALL over a LEFT JOIN. oa.z = 10 in every row.
-- B1: 5 > ALL (10, ...) is FALSE. Expected 0.
select count(*) as b1_expect_0 from rdb$database where 5 > all (select oa.z from oa left join ob on oa.x = ob.x);
-- B2: NOT (B1) is TRUE. Expected 1.
select count(*) as b2_expect_1 from rdb$database where not (5 > all (select oa.z from oa left join ob on oa.x = ob.x));
-- B3: 15 > ALL (10, ...) is TRUE. Expected 1.
select count(*) as b3_expect_1 from rdb$database where 15 > all (select oa.z from oa left join ob on oa.x = ob.x);
-- B4: 5 = ANY (10, ...) is FALSE. Expected 0.
select count(*) as b4_expect_0 from rdb$database where 5 = any (select oa.z from oa left join ob on oa.x = ob.x);
