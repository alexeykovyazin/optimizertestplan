-- Test 93: the anti-join of NOT EXISTS and a condition of the sub-query over the outer tables only.
-- With SubQueryConversion = true a correlated NOT EXISTS becomes an anti-join (the optimizer note 4.66).
-- Every equality of the sub-query that refers to the outer query is taken into the join. Such an equality
-- can refer to the outer tables only: "NOT EXISTS (SELECT ... FROM D WHERE D.K = P.K AND P.X = 3)".
-- It is a part of the match: a row of P with X <> 3 has no match and the query returns it.
-- The defect (hqbird commit 465481071d): the condition filtered the outer table, the rows with X <> 3 were lost.
-- The same happened to an equality the optimizer derives: D.K = P.K AND D.K = P.J gives P.K = P.J.
-- The alias "tstsqc" must have SubQueryConversion = true in databases.conf.
-- Expected results (the same with SubQueryConversion = false and on every build without the defect):
--   A01: 437, 109569     A02: 462, 115428     A03: 375, 93875      A04: 500, 125250     A05: 482, 120544
--   A06: 21, 1785        A07: 29, 2465        A08: 500, 125250     A09: 462, 116027     A10: 63, 15681
--   A11: 63, 15681       A12: 459, 115024     A13: 12, 2780        A14: 275, 68425      A15: 275, 68425
--   A16: 437, 109569     A17: 125 / 125 / 125 / 62                 A18: 63, 15681
-- The build with the defect gives other results in A01 - A09, A12, A17 and A18.
-- Expected plans: A01, A02, A05, A08, A09 - HASH (P NATURAL, D NATURAL); A03 - JOIN (P NATURAL, D NATURAL);
--   A04 - JOIN (P NATURAL, E NATURAL); A06, A07 - JOIN (P INDEX (RDB$PRIMARY1), C INDEX (RDB$PRIMARY2));
--   A12 - HASH (HASH (C NATURAL, P NATURAL), D NATURAL). Every query has one PLAN line (no sub-query).
set bail off;
set names utf8;
create database 'tstsqc' user SYSDBA default character set utf8;
create table p (id int not null primary key, k int, j int, x int);
create table c (id int not null primary key, k int, j int, x int);
create table d (id int not null primary key, k int, j int, x int);
create table e (id int not null primary key, k int);
commit;
set term ^;
execute block as
  declare i int = 1;
  declare h int;
begin
  while (i <= 500) do
  begin
    h = mod(i * 7919 + 13, 100003);
    insert into p (id, k, j, x) values (:i,
      iif(mod(:i, 10) = 0, null, mod(:h, 60)),
      iif(mod(:i, 7) = 0, null, mod(:h, 5)),
      mod(:i, 4));
    i = i + 1;
  end
  i = 1;
  while (i <= 800) do
  begin
    h = mod(i * 104729 + 7, 100019);
    insert into c (id, k, j, x) values (:i,
      iif(mod(:i, 9) = 0, null, mod(:h, 40) * 2),
      iif(mod(:i, 5) = 0, null, mod(:h, 5)),
      mod(:i, 3));
    i = i + 1;
  end
end^
set term ;^
commit;
insert into d select * from c;
commit;
create index c_k on c (k);
commit;
select rdb$config_value from rdb$config where rdb$config_name = 'SubQueryConversion';
set list on;
set plan on;
-- A01: the join key and an equality of an outer column with a constant
select 'A01' q, count(*) c, sum(p.id) s from p where not exists (select 1 from d where d.k = p.k and p.x = 3);
-- A02: the join key and an equality of two outer columns
select 'A02' q, count(*) c, sum(p.id) s from p where not exists (select 1 from d where d.k = p.k and p.x = p.j);
-- A03: only a condition over the outer table, the inner table is not empty
select 'A03' q, count(*) c, sum(p.id) s from p where not exists (select 1 from d where p.x = 3);
-- A04: the same, the inner table is empty
select 'A04' q, count(*) c, sum(p.id) s from p where not exists (select 1 from e where p.x = 3);
-- A05: two equalities with one inner column; the optimizer derives P.K = P.J
select 'A05' q, count(*) c, sum(p.id) s from p where not exists (select 1 from d where d.k = p.k and d.k = p.j);
-- A06: nested loops through the unique index of the inner table
select 'A06' q, count(*) c, sum(p.id) s from p where p.id between 71 and 99 and not exists (select 1 from c where c.id = p.k and p.x = 3);
-- A07: nested loops and the derived equality
select 'A07' q, count(*) c, sum(p.id) s from p where p.id between 71 and 99 and not exists (select 1 from c where c.id = p.k and c.id = p.j);
-- A08: the join key, a condition of the inner table and a condition of the outer table
select 'A08' q, count(*) c, sum(p.id) s from p where not exists (select 1 from d where d.k = p.k and d.j = 1 and p.j = 1 and p.x = 3);
-- A09: IS NOT DISTINCT FROM over the outer table
select 'A09' q, count(*) c, sum(p.id) s from p where not exists (select 1 from d where d.k = p.k and p.j is not distinct from 1);
-- A10, A11: EXISTS with the same conditions stays as it was (a semi-join filters the outer table)
select 'A10' q, count(*) c, sum(p.id) s from p where exists (select 1 from d where d.k = p.k and p.x = 3);
select 'A11' q, count(*) c, sum(p.id) s from p where exists (select 1 from d where d.k = p.k) and p.x = 3;
-- A12: the outer part is a join; the condition of the sub-query compares its two tables
select 'A12' q, count(*) c, sum(p.id) s from p join c on c.id = p.id where not exists (select 1 from d where d.k = p.k and p.j = c.j);
-- A13: a condition of the outer query stays a filter of the outer table
select 'A13' q, count(*) c, sum(p.id) s from p where p.x = 3 and p.j = 2 and not exists (select 1 from d where d.k = p.k and p.x = 3);
-- A14, A15: NOT EXISTS without such a condition, and the LEFT JOIN form of it
select 'A14' q, count(*) c, sum(p.id) s from p where not exists (select 1 from d where d.k = p.k);
select 'A15' q, count(*) c, sum(p.id) s from p left join d on d.k = p.k where d.k is null;
-- A16: the LEFT JOIN form of A01
select 'A16' q, count(*) c, sum(p.id) s from p left join d on d.k = p.k and p.x = 3 where d.k is null;
-- A17: GROUP BY above the anti-join of A01 (four rows: x = 0, 1, 2, 3)
select 'A17' q, p.x, count(*) c from p where not exists (select 1 from d where d.k = p.k and p.x = 3) group by p.x order by p.x;
set plan off;
-- A18: DELETE by the NOT EXISTS of A01: 63 rows stay, the sum of id is 15731
delete from p where not exists (select 1 from d where d.k = p.k and p.x = 3);
select 'A18' q, count(*) c, sum(p.id) s from p;
rollback;
drop database;
