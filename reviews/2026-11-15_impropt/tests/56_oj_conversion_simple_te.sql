-- 56_oj_conversion_simple_te.sql - LEFT JOIN -> INNER JOIN conversion for a simple table expression
-- over one table (view / derived table / CTE / nested view). Alias tst10oj (delete its file first, as for test 47).
-- Data: s 2000 rows (col = 'x' for id = 200, 400, ..., 2000; kid = mod(id, 100) + 1), index s_col;
--       big 40000 rows (ref = mod(id, 2000) + 1, index big_ref) + 100 rows with ref = 0 (no match in s);
--       k 100 rows.
-- Expected results (arithmetic): see NOTE.md. Fetches: good plan (S_COL -> BIG_REF) < 1000,
-- bad plan (BIG full scan, nested loop outer) > 40000.
set bail off;
create database 'tst10oj' user SYSDBA page_size 8192;
create table k (id int primary key, name varchar(20));
create table s (id int primary key, kid int, col varchar(10), pad varchar(50));
create table big (id int primary key, ref int, pad varchar(50));
commit;
set term ^;
execute block as declare i int = 1; begin
  while (i <= 100) do begin insert into k values (:i, 'k' || :i); i = i + 1; end
  i = 1;
  while (i <= 2000) do begin
    insert into s values (:i, mod(:i, 100) + 1, iif(mod(:i, 200) = 0, 'x', 'v' || mod(:i, 50)), rpad('s', 50, '.'));
    i = i + 1; end
  i = 1;
  while (i <= 40000) do begin
    insert into big values (:i, mod(:i, 2000) + 1, rpad('b', 50, '.'));
    i = i + 1; end
  while (i <= 40100) do begin
    insert into big values (:i, 0, rpad('b', 50, '.'));
    i = i + 1; end
end^
set term ;^
commit;
create index s_col on s (col);
create index big_ref on big (ref);
create view v1 as select * from s;
create view v1w as select * from s where kid = 1;
create view v1n as select * from v1;
create view v2 as select s.id, s.col, k.name from s join k on k.id = s.kid;
create view va as select col, max(id) as id, count(*) as cnt from s group by col;
create view vx as select id, coalesce(col, 'x') as col from s;
commit;
alter database add extended statistics; commit;
alter database refresh statistics; commit;
connect 'tst10oj' user SYSDBA;

select count(*) from big;
select count(*) from s;

set explain on;
set stats on;
-- converted to inner join (Q1 already before the fix; Q2-Q6 after the fix)
select 'Q1 plain table' as tag, count(*) as cnt, sum(b.id) as sum_id from big b left join s on s.id = b.ref where s.col = 'x';
select 'Q2 simple view' as tag, count(*) as cnt, sum(b.id) as sum_id from big b left join v1 on v1.id = b.ref where v1.col = 'x';
select 'Q3 view with WHERE' as tag, count(*) as cnt, sum(b.id) as sum_id from big b left join v1w on v1w.id = b.ref where v1w.col = 'x';
select 'Q4 derived table' as tag, count(*) as cnt, sum(b.id) as sum_id from big b left join (select id, col from s) d on d.id = b.ref where d.col = 'x';
with c as (select id, col from s where id > 1000)
select 'Q5 CTE with WHERE' as tag, count(*) as cnt, sum(b.id) as sum_id from big b left join c on c.id = b.ref where c.col = 'x';
select 'Q6 nested simple view' as tag, count(*) as cnt, sum(b.id) as sum_id from big b left join v1n on v1n.id = b.ref where v1n.col = 'x';
-- stays outer join, nested loop (no change by the fix)
select 'Q7 view with join' as tag, count(*) as cnt, sum(b.id) as sum_id from big b left join v2 on v2.id = b.ref where v2.col = 'x';
select 'Q8 view with aggregate' as tag, count(*) as cnt, sum(b.id) as sum_id from big b left join va on va.id = b.ref where va.col = 'x';
select 'Q9 view with computed column' as tag, count(*) as cnt, sum(b.id) as sum_id from big b left join vx on vx.id = b.ref where vx.col = 'x';
