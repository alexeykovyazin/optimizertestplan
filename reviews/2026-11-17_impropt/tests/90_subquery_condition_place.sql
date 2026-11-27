-- Test 90: the place of a condition that runs a subquery for every row (the optimizer note 4.66).
-- Such a condition of a stream waits for the end of the inner join when the join leaves fewer rows than the
-- stream delivers. The results are the same before and after the change; the explained plans differ.
-- Expected results: P1: 99, 10000;  P2: 18, 1791;  P3: 834, 184867;  P4: 29, 2841;  P5: 97, 22256;  P6: 600, 180300
-- Expected plans:
--   P1 (the shape of TPC-H Q21): A is read whole and joined with B by a hash join; the filter with the two
--      subqueries stands above the join (Filter rows=63.81 over Hash Join rows=255.25). Before the change the
--      filter stood over the scan of A (rows=680.67), below the join.
--   P2: B is read first, A is read by its primary key for every row of B: the subqueries are evaluated after the
--      join already, the plan does not change.
--   P3: the join with C gives more rows than A has: the subquery stays in the filter over the scan of A.
--   P4: the subquery is invariant (computed once): it stays in the filter of its stream.
--   P5: one table: the plan does not change; the cheap condition a.s = 'a' is evaluated before the subquery.
--   P6: an outer join: the conditions of the outer stream stay where they were.
set bail off;
set names utf8;
create database 'tst2def' user SYSDBA default character set utf8;
create table a (
  id int not null primary key,
  i int,
  j int,
  k int,
  s varchar(20));
create table b (id int not null primary key, i int, k int, s varchar(5));
create table c (id int not null primary key, ai int, v int);
commit;
set term ^;
execute block as
  declare x int = 1;
  declare h int;
begin
  while (x <= 600) do
  begin
    h = mod(x * 7919 + 13, 100003);
    insert into a (id, i, j, k, s) values (:x,
      iif(mod(:x, 7) = 0, null, mod(:h, 8)),
      iif(mod(:x, 11) = 0, null, mod(:h, 5)),
      iif(mod(:x, 5) = 0, null, mod(:h, 4)),
      iif(mod(:x, 9) = 0, null, iif(mod(:h, 4) = 0, 'a', iif(mod(:h, 4) = 1, 'b ', iif(mod(:h, 4) = 2, 'A', 'ab12')))));
    x = x + 1;
  end
  x = 1;
  while (x <= 200) do
  begin
    insert into b (id, i, k, s) values (:x, iif(mod(:x, 6) = 0, null, mod(:x, 8)), iif(mod(:x, 10) = 0, null, mod(:x, 4)),
      iif(mod(:x, 3) = 0, 'x', iif(mod(:x, 3) = 1, 'y', null)));
    x = x + 1;
  end
  x = 1;
  while (x <= 1000) do
  begin
    insert into c (id, ai, v) values (:x, iif(mod(:x, 23) = 0, null, mod(:x * 7, 450) + 1), iif(mod(:x, 9) = 0, null, mod(:x, 10)));
    x = x + 1;
  end
end^
set term ;^
commit;
create index a_i on a (i);
create index a_s on a (s);
create index b_i on b (i);
create index c_ai on c (ai);
commit;

set explain on;
select 'P1' q, count(*) c, sum(a.id) sa from a join b on b.id = a.id
where exists (select 1 from c l2 where l2.ai = a.id and l2.v <> a.j)
  and not exists (select 1 from c l3 where l3.ai = a.id and l3.v <> a.j and l3.v > 6);

select 'P2' q, count(*) c, sum(a.id) sa from a join b on b.id = a.id
where b.s = 'x' and a.i > a.j
  and exists (select 1 from c l2 where l2.ai = a.id and l2.v <> a.j)
  and not exists (select 1 from c l3 where l3.ai = a.id and l3.v <> a.j and l3.v > 6);

select 'P3' q, count(*) c, sum(a.id) sa from a join c on c.ai = a.id
where exists (select 1 from b b2 where b2.i = a.i and b2.id <> a.id);

select 'P4' q, count(*) c, sum(a.id) sa from a join b on b.id = a.id
where b.s = 'x' and a.i > (select avg(i) from b);

select 'P5' q, count(*) c, sum(a.id) sa from a
where exists (select 1 from c l2 where l2.ai = a.id) and a.s = 'a';

select 'P6' q, count(*) c, sum(a.id) sa from a left join b on b.id = a.id
where exists (select 1 from c l2 where l2.ai = a.id) or a.id > 0;
set explain off;
