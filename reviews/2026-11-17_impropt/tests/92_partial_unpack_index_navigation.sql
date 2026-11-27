-- Test 92: the partial unpack of a record and the index navigation.
-- A read-only stream unpacks only the head of the record: the fields up to the last one the query refers to.
-- The index navigation composes the index key of every record it reads and compares it with the key of the
-- index node. So it needs the fields of all the index segments, also the ones the query does not refer to.
-- The defect (hqbird commit 2a6a824a7d): "select a from p order by a" over the primary key (a, b) returned
-- 40 rows of 4 000 - one row for every value of a.
-- Expected results (the same on every build without the defect):
--   N1: 4000, 78000      N2: 40, 4000        N3: 4000, 198000    N4: 4000, 78000    N5: 1000, 14500
--   N6: 0, 39            N7: 40, 40000       N8: 1000, 4500      N9: 1000, 4500     N10: 4000, 474000
--   N11: 3900, 76250     N12: 4000, 78000
-- Expected plans: N1, N4, N5, N8, N9, N11, N12 - ORDER by the index named in the PLAN clause; N3 - ORDER P_B_D;
--   N10 - ORDER P_EXPR. The plans of N2, N6 and N7 are not fixed by the test.
set bail off;
set names utf8;
create database 'tst2def' user SYSDBA default character set utf8;
create table p (a int not null, b int not null, w int, constraint p_pk primary key (a, b));
create table t (id int not null primary key, k int not null, v int);
create table q (a int not null, b int, c varchar(100));
create table r (a int not null, s varchar(200), b int not null, z int);
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 4000) do begin
    insert into p values (mod(:i, 40), :i / 40, :i);
    i = i + 1;
  end
  i = 0;
  while (i < 400) do begin
    insert into t values (:i, mod(:i, 40), :i);
    i = i + 1;
  end
  i = 0;
  while (i < 1000) do begin
    insert into q values (mod(:i, 10), iif(mod(:i, 3) = 0, null, :i / 10), 'c' || :i);
    insert into r values (mod(:i, 10), rpad('s', mod(:i, 150) + 1, 'x'), :i / 10, :i);
    i = i + 1;
  end
end^
set term ;^
commit;
create descending index p_b_d on p (b, a);
create index p_awb on p (a, w, b);
create index p_expr on p computed by (b * 2 + a);
create index p_part on p (a, b) where w >= 100;
create index t_k on t (k);
create index q_ab on q (a, b);
create index r_ab on r (a, b);
commit;

set plan on;
-- N1: the first column of the two-column primary key
select 'N1' q, count(*) c, sum(a) s from (select a from p plan (p order p_pk) order by a rows 100000);
-- N2: a GROUP BY the first column
select 'N2' q, count(*) c, sum(n) s from (select a, count(*) n from p group by a);
-- N3: a descending index (b, a), the query refers to b only (b is the second field, a is the first one)
select 'N3' q, count(*) c, sum(b) s from (select b from p order by b desc rows 100000);
-- N4: a three-column index (a, w, b), the query refers to a only
select 'N4' q, count(*) c, sum(a) s from (select a from p plan (p order p_awb) order by a rows 100000);
-- N5: a range of the first column
select 'N5' q, count(*) c, sum(a) s from (select a from p where a between 10 and 19 plan (p order p_pk) order by a rows 100000);
-- N6: MIN and MAX of the first column
select 'N6' q, min(a) c, max(a) s from p;
-- N7: the shape of the case U4 of the test 91: a join by the first column under a GROUP BY
select 'N7' q, count(*) c, sum(n) s from (select x.k, count(*) n from t x join p on p.a = x.k group by x.k);
-- N8: NULLs in the second column of the index
select 'N8' q, count(*) c, sum(a) s from (select a from q plan (q order q_ab) order by a rows 100000);
-- N9: a wide text field between the two columns of the index
select 'N9' q, count(*) c, sum(a) s from (select a from r plan (r order r_ab) order by a rows 100000);
-- N10: an expression index
select 'N10' q, count(*) c, sum(e) s from (select b * 2 + a e from p order by b * 2 + a rows 100000);
-- N11: a partial index
select 'N11' q, count(*) c, sum(a) s from (select a from p where w >= 100 plan (p order p_part) order by a rows 100000);
-- N12: the same query as N1 after a change of the record format (the old records have no field x)
alter table p add x int;
commit;
update p set x = 1 where a = 0 and b < 50;
commit;
select 'N12' q, count(*) c, sum(a) s from (select a from p plan (p order p_pk) order by a rows 100000);
set plan off;
drop database;
