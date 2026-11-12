-- 35_oj_on_subq.sql - W1 (41d70f3868): Hash Join (outer) drops an ON conjunct with a subquery or an outer reference.
-- Correct counts: see RESULTS.md. Alias tst9oj.
-- vA: Hash Join (outer) and ON conjuncts with a subquery / a parent-query reference.
-- Data: oa.x = ob.x = id (1:1, 10000 rows), oa.z = id mod 10, ob.y = id mod 100,
-- ot(k, v) = (0..9, k*10). ob has NO index on x (hash join is cheap),
-- obi = copy of ob WITH index on x (reference nested loop by PLAN).
set bail off;
create database 'tst9oj' user SYSDBA;
create table oa (id int not null, x int, z int);
create table ob (id int not null, x int, y int);
create table obi (id int not null, x int, y int);
create table ot (k int, v int);
commit;
set term ^;
execute block as
declare i int = 1;
begin
  while (i <= 10000) do
  begin
    insert into oa values (:i, :i, mod(:i, 10));
    insert into ob values (:i, :i, mod(:i, 100));
    insert into obi values (:i, :i, mod(:i, 100));
    i = i + 1;
  end
  i = 0;
  while (i < 10) do
  begin
    insert into ot values (:i, :i * 10);
    i = i + 1;
  end
end^
set term ;^
commit;
create index obi_x on obi(x);
commit;
alter database add extended statistics; commit; alter database refresh statistics; commit;
connect 'tst9oj' user SYSDBA;

-- ===== R: independent reference counts (no outer join) =====
select 'R1 scalar/exists/notexists/any expected' as tag, count(*) as expected_match
  from oa where mod(oa.x, 100) > (select min(v) from ot where ot.k = oa.z);
select 'R5 parent-ref expected (p.v=50)' as tag, count(*) as expected_match
  from oa where mod(oa.x, 100) - oa.z > 50;
select 'R7 uncorrelated expected' as tag, count(*) as expected_match
  from ob where ob.y > 50;

set explain on;

-- ===== N: reference nested loop (forced by PLAN with index) =====
select 'N1 NL scalar' as tag, count(*) as cnt_all, count(obi.id) as cnt_match
  from oa left join obi on oa.x = obi.x and obi.y > (select min(v) from ot where ot.k = oa.z)
  PLAN JOIN (OA NATURAL, OBI INDEX (OBI_X));

-- ===== Q: outer join over ob (no index) - the optimizer is free =====
select 'Q1 scalar subquery' as tag, count(*) as cnt_all, count(ob.id) as cnt_match
  from oa left join ob on oa.x = ob.x and ob.y > (select min(v) from ot where ot.k = oa.z);

select 'Q1b anti (ob.id is null), expect 10000-R1' as tag, count(*) as cnt
  from oa left join ob on oa.x = ob.x and ob.y > (select min(v) from ot where ot.k = oa.z)
  where ob.id is null;

select 'Q2 exists' as tag, count(*) as cnt_all, count(ob.id) as cnt_match
  from oa left join ob on oa.x = ob.x and exists (select 1 from ot where ot.k = oa.z and ot.v < ob.y);

select 'Q3 not exists' as tag, count(*) as cnt_all, count(ob.id) as cnt_match
  from oa left join ob on oa.x = ob.x and not exists (select 1 from ot where ot.k = oa.z and ot.v >= ob.y);

select 'Q4 or exists' as tag, count(*) as cnt_all, count(ob.id) as cnt_match
  from oa left join ob on oa.x = ob.x and (ob.y < 0 or exists (select 1 from ot where ot.k = oa.z and ot.v < ob.y));

select 'Q5 parent-query ref' as tag, p.k,
  (select count(ob.id) from oa left join ob on oa.x = ob.x and ob.y - oa.z > p.v) as cnt_match
  from ot p where p.k = 5;

select 'Q6 > any' as tag, count(*) as cnt_all, count(ob.id) as cnt_match
  from oa left join ob on oa.x = ob.x and ob.y > any (select v from ot where ot.k = oa.z);

select 'Q7 control uncorrelated subq' as tag, count(*) as cnt_all, count(ob.id) as cnt_match
  from oa left join ob on oa.x = ob.x and ob.y > (select min(v) from ot where ot.k = 5);

select 'Q8 control plain non-equi' as tag, count(*) as cnt_all, count(ob.id) as cnt_match
  from oa left join ob on oa.x = ob.x and ob.y > oa.z * 10;

-- ===== I: same as Q1 over obi (index on x), optimizer is free =====
select 'I1 scalar, index on x' as tag, count(*) as cnt_all, count(obi.id) as cnt_match
  from oa left join obi on oa.x = obi.x and obi.y > (select min(v) from ot where ot.k = oa.z);

-- ===== RJ: right join form =====
select 'RJ1 right join scalar' as tag, count(*) as cnt_all, count(ob.id) as cnt_match
  from ob right join oa on oa.x = ob.x and ob.y > (select min(v) from ot where ot.k = oa.z);

set explain off;
exit;
