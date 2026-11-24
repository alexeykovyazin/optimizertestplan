-- Test 86: the bounded sort of the FIRST N rows (optimizer notes 4.58, "Top N Sort").
-- Change under test: a query with ORDER BY and constant FIRST / SKIP / ROWS limits keeps the N smallest records
-- in memory (collect up to 2N records, then a heap of N) instead of sorting its whole input.
-- Data: T86, 20 000 rows; K has 200 values and NULLs (many equal keys), S is a case-insensitive text with NULLs,
-- W is a wide text key (the sort record is wider than a chunk of the record slots).
-- Expected plans (the build with the bounded sort):
--   P1, P2, P3, P4, P10: "Top N Sort (top: N, ...)", N = FIRST + SKIP (10, 15, 20, 15, 25);
--   P5 (the limit is an expression), P6 (an invariant predicate stands between the sort and the limit),
--   P7 (SKIP without FIRST), P9 (the selection does not fit TopNSortMemory): "Sort";
--   P8 (DISTINCT): "Top N Sort" over "Unique Sort".
-- Expected results:
--   V: CASES = 252, MISMATCHES = 0. Every case compares the rows and their order of the bounded sort with the same
--      query whose limit is written as CAST(N AS INTEGER): such a limit is not a constant for the optimizer, the
--      whole input is sorted. The cases cover an input of 0, N-1, N, N+1, 2N-1, 2N, 2N+1, 5N and 20 000 rows.
--   R: the columns HEAP and FULL_SORT are equal. The sub-query has a large limit and a short input and is opened
--      15 000 times. Before the review fix the bounded sort took and zeroed its 2N record numbers and a block of
--      256K at every open: R1 took 5.6 s against 0.11 s of R2 (out_topn_86_topn_sort.txt, build 631465affc).
--      After the fix both take 0.12 s (out_topnfix_86_topn_sort.txt, build aa214e362c).
--   D: the rows changed by UPDATE / DELETE with ORDER BY ... ROWS are the same in both forms (two equal lines).
set bail off;
create database 'tst2def' user SYSDBA default character set utf8;
create table t86 (
  id int not null,
  k int,
  s varchar(30) character set utf8 collate unicode_ci,
  w varchar(1500) character set utf8,
  constraint t86_pk primary key (id));
commit;
set term ^;
execute block as
  declare i int = 1;
  declare h int;
begin
  while (i <= 20000) do
  begin
    h = mod(i * 7919 + 13, 100003);
    insert into t86 (id, k, s, w) values (:i,
      iif(mod(:i, 17) = 0, null, mod(:h, 200) - 100),
      iif(mod(:i, 29) = 0, null, iif(mod(:h, 3) = 0, 'ab', iif(mod(:h, 3) = 1, 'AB', 'Ab')) || mod(:h, 300)),
      iif(mod(:i, 53) = 0, null, lpad(mod(:h, 2000), 20 + mod(:h, 1400), 'xyz')));
    i = i + 1;
  end
end^
set term ;^
commit;
set statistics index t86_pk;
commit;

set planonly on;
set explain on;
-- P1: FIRST
select first 10 id from t86 order by k, id;
-- P2: FIRST and SKIP
select first 10 skip 5 id from t86 order by s desc, id;
-- P3: ROWS m TO n
select id from t86 order by k desc nulls last, id rows 11 to 20;
-- P4: OFFSET and FETCH
select id from t86 order by w, id offset 5 rows fetch first 10 rows only;
-- P5: the limit is not a constant
select first (cast(10 as integer)) id from t86 order by k, id;
-- P6: an invariant predicate
select first 10 id from t86 where current_date > date '2000-01-01' order by k, id;
-- P7: SKIP without FIRST
select skip 5 id from t86 order by k, id;
-- P8: DISTINCT under the ORDER BY of other columns
select first 10 x.k from (select distinct k, s from t86) x order by x.k desc, x.s;
-- P9: the selection does not fit the memory
select first 2000000 id from t86 order by k, id;
-- P10: DML
delete from t86 order by k, id rows 25;
set explain off;
set planonly off;

-- V: the bounded sort against the full sort
set term ^;
execute block returns (cases int, mismatches int, first_mismatch varchar(300)) as
  declare n int;
  declare ni int;
  declare xi int;
  declare ki int;
  declare x int;
  declare sk int;
  declare ord varchar(100);
  declare q varchar(600);
  declare a varchar(100);
  declare b varchar(100);
begin
  cases = 0; mismatches = 0; first_mismatch = null;
  ni = 0;
  while (ni < 4) do
  begin
    n = decode(ni, 0, 1, 1, 2, 2, 17, 300);
    xi = 0;
    while (xi < 9) do
    begin
      x = decode(xi, 0, 0, 1, n - 1, 2, n, 3, n + 1, 4, 2 * n - 1, 5, 2 * n, 6, 2 * n + 1, 7, 5 * n, 20000);
      ki = 0;
      while (ki < 7) do
      begin
        ord = decode(ki, 0, 'k, id', 1, 'k desc nulls last, id desc', 2, 's, id', 3, 's desc nulls first, id',
          4, 'w, id', 5, 'k, s desc, id', 'k');
        sk = iif(ki = 1, 0, mod(n, 3));
        -- the last key (K alone) does not make the rows unique: only the keys are compared there
        q = 'select coalesce(sum(' || iif(ki = 6, 'coalesce(k, -1000)', 'id') || ' * rn), 0) || ''/'' || count(*) from (' ||
          'select id, k, row_number() over () rn from (select first @N skip ' || sk ||
          ' id, k from t86 where id <= ' || x || ' order by ' || ord || '))';
        execute statement replace(q, '@N', n) into :a;
        execute statement replace(q, '@N', '(cast(' || n || ' as integer))') into :b;
        cases = cases + 1;
        if (a is distinct from b) then
        begin
          mismatches = mismatches + 1;
          if (first_mismatch is null) then
            first_mismatch = 'n=' || n || ' rows=' || x || ' order by ' || ord || ': ' || a || ' <> ' || b;
        end
        ki = ki + 1;
      end
      xi = xi + 1;
    end
    ni = ni + 1;
  end
  suspend;
end^
set term ;^

-- R: a sort with a large limit and a short input, opened 15 000 times
set stats on;
-- R1: the bounded sort
select 'R1' as t, sum((select max(x.id) from (select first 30000 skip 2 b.id from t86 b
    where b.id between a.id and a.id + 5 order by b.k, b.id) x)) as heap
  from t86 a where a.id <= 15000;
-- R2: the full sort
select 'R2' as t, sum((select max(x.id) from (select first (cast(30000 as integer)) skip 2 b.id from t86 b
    where b.id between a.id and a.id + 5 order by b.k, b.id) x)) as full_sort
  from t86 a where a.id <= 15000;
set stats off;

-- D: DML with ORDER BY ... ROWS, the changed rows of both forms
update t86 set k = 5000 order by s desc nulls last, id rows 40;
delete from t86 order by k desc nulls last, id rows 11 to 60;
select 'D heap' as t, count(*), sum(id), sum(k) from t86;
rollback;
update t86 set k = 5000 order by s desc nulls last, id rows (cast(40 as integer));
delete from t86 order by k desc nulls last, id rows (cast(11 as integer)) to (cast(60 as integer));
select 'D full' as t, count(*), sum(id), sum(k) from t86;
rollback;
