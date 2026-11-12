-- 36_bhj_slot_crash.sql - W2 (f8bd5b4cf0): BHJ slot cache memcpy overflow, river record > 64 KB. STOPS THE SERVER on 06041718cc.
-- Works on the default config too. Alias tst9bhj.
-- vB / T1: BatchHashJoin slot mode, hashed record > 64 KB (SlotCache::add overflow).
-- Hashed side D: derived table with FIRST over a join of two tables (2 streams).
-- Buffered record of D: a2.k + a2.w1 + a2.w2 + b2.k + b2.w1 + overhead = ~72 KB.
-- Estimate of the inner join: A x B x (index selectivity of B.K):
--   FIRST 5000000 caps D to 5M > HashJoin::maxCapacity (~4M)
--   -> Batch Hash Join, 8 batches. Leader L: narrow derived river (FIRST 6000000).
-- Real rows: only 1 keys of B are not NULL (x 15 duplicates) -> the hashed
--   side holds 1 x 15 records of ~72 KB, the BHJ batches stay in RAM.
set bail on;
create database 'tst9bhj' user SYSDBA page_size 8192;
create table a (k int, w1 varchar(32000) character set none, w2 varchar(8000) character set none);
create table b (k int, w1 varchar(32000) character set none);
commit;
set term ^;
execute block as
  declare i int = 1;
  declare j int;
begin
  while (i <= 10000) do
  begin
    insert into a (k, w1, w2) values (:i, 'a' || :i, 'x');
    i = i + 1;
  end
  i = 1;
  while (i <= 1) do
  begin
    j = 1;
    while (j <= 15) do
    begin
      insert into b (k, w1) values (:i, 'b' || :i);
      j = j + 1;
    end
    i = i + 1;
  end
  i = 1;
  while (i <= 2000 - 1 * 15) do
  begin
    insert into b (k, w1) values (null, null);
    i = i + 1;
  end
end^
set term ;^
commit;
-- the index keeps the inner joins of L and D on nested loops (no inner record buffer
-- eats the 64 MB temp cache); its selectivity 1/(distinct keys) ignores the NULL keys,
-- so the join estimate is A x B / 1 while the real join has 1 x 15 rows
create index b_k on b (k);
commit;
set bail off;
select (select count(*) from a) a_rows, (select count(*) from b) b_rows,
  (select count(*) from a join b on b.k = a.k) inner_rows from rdb$database;
set explain on;
set planonly on;
select count(*) cnt, sum(char_length(d.aw1)) l1, sum(char_length(d.aw2)) l2, sum(char_length(d.bw1)) l3
from (select first 6000000 a.k from a join b on b.k = a.k) l
join (select first 5000000 a2.k, a2.w1 aw1, a2.w2 aw2, b2.w1 bw1
      from a a2 join b b2 on b2.k = a2.k) d on d.k = l.k;
set planonly off;
set explain off;
select current_timestamp ts_before from rdb$database;
select count(*) cnt, sum(char_length(d.aw1)) l1, sum(char_length(d.aw2)) l2, sum(char_length(d.bw1)) l3
from (select first 6000000 a.k from a join b on b.k = a.k) l
join (select first 5000000 a2.k, a2.w1 aw1, a2.w2 aw2, b2.w1 bw1
      from a a2 join b b2 on b2.k = a2.k) d on d.k = l.k;
select current_timestamp ts_after from rdb$database;
-- reference without the batched hash join: nested loops via PLAN JOIN is not allowed for
-- derived tables, so count it directly
select sum(c * c) expected_cnt from (select b.k, count(*) c from a join b on b.k = a.k group by b.k);
