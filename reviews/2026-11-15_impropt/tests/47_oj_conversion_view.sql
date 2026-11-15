-- 47_oj_conversion_view.sql - Y5 (73ff47d23e): LEFT JOIN to a view / derived table / CTE with WHERE on the inner side is no longer converted to INNER JOIN -> full scan of big. Alias tst10oj.
-- Data: big 400 000 rows (ref = mod(i, 20000) + 1, index big_ref), s 20 000 rows (col = 'x' in 10 rows, index s_col),
-- k 100 rows; v1 = select * from s; v2 = s join k.
-- Expected for every query: 200 rows, sum(b.id) = 40199800 (10 s rows x 20 big rows; arithmetic).
-- Look at Fetches: good plan (S_COL range -> BIG_REF) ~500, bad plan (BIG full scan) ~2 000 000.
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
  while (i <= 20000) do begin
    insert into s values (:i, mod(:i, 100) + 1, iif(mod(:i, 2000) = 0, 'x', 'v' || mod(:i, 500)), rpad('s', 50, '.'));
    i = i + 1; end
  i = 1;
  while (i <= 400000) do begin
    insert into big values (:i, mod(:i, 20000) + 1, rpad('b', 50, '.'));
    i = i + 1; end
end^
set term ;^
commit;
create index s_col on s (col);
create index big_ref on big (ref);
create view v1 as select * from s;
create view v2 as select s.id, s.col, k.name from s join k on k.id = s.kid;
commit;
alter database add extended statistics; commit;
alter database refresh statistics; commit;
connect 'tst10oj' user SYSDBA;

select 'R1 rows with col = x in s (expected 10)' as tag, count(*) as cnt from s where col = 'x';
-- warm up the cache
select count(*) from big;
select count(*) from s;

set explain on;
set stats on;
-- control: plain table (converted to inner join)
select 'C1 plain table' as tag, count(*) as cnt, sum(b.id) as sum_id from big b left join s on s.id = b.ref where s.col = 'x';
-- the bug: view, derived table, CTE, view with join
select 'Q1 view v1' as tag, count(*) as cnt, sum(b.id) as sum_id from big b left join v1 on v1.id = b.ref where v1.col = 'x';
select 'Q2 derived table' as tag, count(*) as cnt, sum(b.id) as sum_id from big b left join (select * from s) d on d.id = b.ref where d.col = 'x';
with c as (select * from s)
select 'Q3 CTE' as tag, count(*) as cnt, sum(b.id) as sum_id from big b left join c on c.id = b.ref where c.col = 'x';
select 'Q4 view v2 (join inside)' as tag, count(*) as cnt, sum(b.id) as sum_id from big b left join v2 on v2.id = b.ref where v2.col = 'x';
-- workaround: INNER JOIN by hand
select 'W1 view v1, inner join' as tag, count(*) as cnt, sum(b.id) as sum_id from big b join v1 on v1.id = b.ref where v1.col = 'x';
select 'W2 derived, inner join' as tag, count(*) as cnt, sum(b.id) as sum_id from big b join (select * from s) d on d.id = b.ref where d.col = 'x';
