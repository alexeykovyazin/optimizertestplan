-- Test 89: the condition every arm of an OR holds is taken out of the OR (the optimizer note 4.65).
--   (A AND X) OR (A AND Y) = A AND (X OR Y)
-- The results are the same before and after the change; the plans differ.
-- Expected results:
--   Q1: 14, 1535      the shape of TPC-H Q19: the join equality and two conditions in each of the three arms
--   I1..I4: 13, 4441  one conditional index condition written in four ways
--   A1: 66, 20476     an arm that holds only the common condition absorbs the OR:  i = 1 OR (i = 1 AND k = 3)
--   A2: 13, 3916      two equal arms
--   L1: 600, 20, 558  the three-valued logic: the rows, the rows where the OR is true, the rows where NOT (OR) is true
--   L2: the same numbers for the factored form written by hand
--   V1: 13, 3916      RAND() in every arm is not taken out, the result is the same
--   D1: 258, 74220    no common condition but the join equality outside the OR: the restriction of every table is
--                     derived from two conditions of an arm
-- Expected plans (before the change -> after it):
--   Q1: B INDEX (RDB$PRIMARY2, RDB$PRIMARY2, RDB$PRIMARY2) -> B INDEX (RDB$PRIMARY2)
--   I1, I4: A INDEX (A_IJ, A_IJ) -> A INDEX (A_P1);  I2, I3: A INDEX (A_IJ) -> A INDEX (A_P1)
--   A1: A INDEX (A_I, A_I) -> A INDEX (A_I);  A2: A INDEX (A_IJ, A_IJ) -> A INDEX (A_IJ)
--   D1 (explained): a Filter over A and a Filter over B below the hash join, each table is read by one Bitmap Or
--      of its index; before the change the only Filter stood above the join
set bail off;
set names utf8;
create database 'tst2def' user SYSDBA default character set utf8;
create table a (
  id int not null primary key,
  i int,
  j int,
  k int,
  n numeric(10,2),
  s varchar(20));
create table b (id int not null primary key, i int, k int, s varchar(5));
commit;
set term ^;
execute block as
  declare x int = 1;
  declare h int;
begin
  while (x <= 600) do
  begin
    h = mod(x * 7919 + 13, 100003);
    insert into a (id, i, j, k, n, s) values (:x,
      iif(mod(:x, 7) = 0, null, mod(:h, 8)),
      iif(mod(:x, 11) = 0, null, mod(:h, 5)),
      iif(mod(:x, 5) = 0, null, mod(:h, 4)),
      iif(mod(:x, 13) = 0, null, mod(:h, 11) / 100.00),
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
end^
set term ;^
commit;
create index a_i on a (i);
create index a_ij on a (i, j);
create index a_s on a (s);
create index b_k on b (k);
create index a_p1 on a (n) where (i = 1 and j = 2) or (i = 1 and j = 3);
commit;

set plan on;
select 'Q1' q, count(*) c, sum(a.id) sa from a, b
where (a.id = b.id and a.s = 'a' and a.j in (1, 2) and b.k >= 1 and b.k <= 1 + 1 and a.i between 1 and 5 and b.s in ('x', 'y'))
   or (a.id = b.id and a.s = 'b ' and a.j in (0, 3) and b.k >= 2 and b.k <= 2 + 1 and a.i between 1 and 6 and b.s in ('x', 'y'))
   or (a.id = b.id and a.s = 'A' and a.j in (2, 4) and b.k >= 0 and b.k <= 0 + 1 and a.i between 1 and 7 and b.s in ('x', 'y'));

select 'I1' q, count(*) c, sum(a.id) sa from a where ((i = 1 and j = 2) or (i = 1 and j = 3)) and n < 0.05;
select 'I2' q, count(*) c, sum(a.id) sa from a where i = 1 and (j = 2 or j = 3) and n < 0.05;
select 'I3' q, count(*) c, sum(a.id) sa from a where i = 1 and j in (2, 3) and n < 0.05;
select 'I4' q, count(*) c, sum(a.id) sa from a where ((j = 3 and i = 1) or (j = 2 and i = 1)) and n < 0.05;

select 'A1' q, count(*) c, sum(a.id) sa from a where (i = 1) or (i = 1 and k = 3);
select 'A2' q, count(*) c, sum(a.id) sa from a where (i = 1 and j = 2) or (i = 1 and j = 2);
set plan off;

select 'L1' q, count(*) c,
  sum(iif((i = 1 and j = 2 and k = 1) or (i = 1 and j = 3 and k = 1), 1, 0)) t,
  sum(iif(not ((i = 1 and j = 2 and k = 1) or (i = 1 and j = 3 and k = 1)), 1, 0)) f from a;
select 'L2' q, count(*) c,
  sum(iif(i = 1 and k = 1 and (j = 2 or j = 3), 1, 0)) t,
  sum(iif(not (i = 1 and k = 1 and (j = 2 or j = 3)), 1, 0)) f from a;

select 'V1' q, count(*) c, sum(a.id) sa from a where (i = 1 and rand() >= 0 and j = 2) or (i = 1 and rand() >= 0 and j = 2);

set explain on;
select 'D1' q, count(*) c, sum(a.id) sa from a, b
where a.i = b.i and ((a.s = 'a' and a.j in (1, 2) and b.k >= 1 and b.s = 'x') or (a.s = 'A' and a.j in (0, 3) and b.k <= 2 and b.s = 'y'));
set explain off;
