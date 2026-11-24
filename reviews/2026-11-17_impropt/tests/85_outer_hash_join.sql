-- Test 85: the hash join of an outer join (HQbird 5.0, the port of the optimizer notes 4.11).
-- Change: a LEFT JOIN whose inner table has no index on the join key was executed only by a nested loop with
-- a full scan of the inner table for every outer row (TPC-H Q13: CUSTOMER LEFT JOIN ORDERS, no index on O_CUSTKEY).
-- The optimizer now prices the nested loop against the hash join and takes the cheaper plan.
-- Data: 3000 customers, 60 000 orders; customers 2000..2999 have no orders, every 50th order has no customer (NULL),
-- every 10th order has a comment the ON clause filters out. BIG_ORDERS has 1 200 000 rows: above the capacity of
-- the hash table of the inner joins (1 009 000 rows), so H3 checks the larger capacity of the outer join.
-- Expected plans (the build with the change):
--   H1, H2: "Hash Join (outer)" over "ORDERS" Full Scan (one scan);
--   H3: "Hash Join (outer)" over "BIG_ORDERS" Full Scan;
--   H4 (a chain of four joins of 1 200 000 hashed rows each): three "Hash Join (outer)" and one
--       "Nested Loop Join (outer)" - the outer joins of a statement share one budget of 4 001 000 hashed rows;
--   C1 (control, few outer rows and an index on the inner key): "Nested Loop Join (outer)" with "ORDERS_PK" stays.
-- The build before the change: H1 and H2 scan ORDERS 3000 times (180 000 000 record reads each), H3 scans
-- BIG_ORDERS 200 times (240 000 000 record reads), H4 scans it 80 times.
-- Expected results: H1, H2, H3, H4, C1 return the same rows on both builds (H3: 60100, 60000; H4: five times 20);
-- in V the columns H1, H2
-- and H3 are equal to H1_REF, H2_REF and H3_REF (the same joins written with a BETWEEN, which cannot be hashed).
set bail off;
create database 'tst2def' user SYSDBA default character set utf8;
create table customer (c_custkey int not null, c_flag int not null, constraint customer_pk primary key (c_custkey));
create table orders (o_orderkey int not null, o_custkey int, o_comment varchar(40),
  constraint orders_pk primary key (o_orderkey));
create table big_orders (b_id int not null, b_custkey int);
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 3000) do begin
    insert into customer values (:i, mod(:i, 4));
    i = i + 1;
  end
  i = 0;
  while (i < 60000) do begin
    insert into orders values (:i, iif(mod(:i, 50) = 0, null, mod(:i * 7, 2000)),
      iif(mod(:i, 10) = 0, 'special packed requests', 'regular'));
    i = i + 1;
  end
  i = 0;
  while (i < 1200000) do begin
    insert into big_orders values (:i, mod(:i * 7, 2000));
    i = i + 1;
  end
end^
set term ;^
commit;
set statistics index customer_pk;
set statistics index orders_pk;
commit;

set explain on;
set stats on;
-- H1: the shape of TPC-H Q13 (an ON condition of the inner side)
select 'H1' as t, c_count, count(*) as custdist from (
    select c.c_custkey, count(o.o_orderkey) from customer c
    left join orders o on c.c_custkey = o.o_custkey and o.o_comment not like '%special%requests%'
    group by c.c_custkey
  ) as c_orders (c_custkey, c_count)
group by c_count order by custdist desc, c_count desc;
-- H2: no grouping, an ON condition of the outer side
select 'H2' as t, count(*), count(o.o_orderkey), sum(o.o_orderkey) from customer c
  left join orders o on c.c_custkey = o.o_custkey and c.c_flag = 1;
-- H3: the hashed table is above the capacity of the inner joins
select 'H3' as t, count(*), count(b.b_id) from customer c
  left join big_orders b on c.c_custkey = b.b_custkey
  where c.c_custkey between 1900 and 2099;
-- H4: a chain of outer joins, every hashed table is above the capacity of the inner joins
select 'H4' as t, count(*), count(b1.b_id), count(b2.b_id), count(b3.b_id), count(b4.b_id) from customer c
  left join big_orders b1 on b1.b_id = c.c_custkey
  left join big_orders b2 on b2.b_id = c.c_custkey + 1
  left join big_orders b3 on b3.b_id = c.c_custkey + 2
  left join big_orders b4 on b4.b_id = c.c_custkey + 3
  where c.c_custkey < 20;
-- C1 (control): few outer rows, the inner table is read by its primary key
select 'C1' as t, count(*), count(o.o_orderkey), sum(o.o_orderkey) from customer c
  left join orders o on o.o_orderkey = c.c_custkey
  where c.c_custkey < 10;
set stats off;
set explain off;
-- V: the values of the H1 and H2 joins for 201 customers (with and without orders) and of the H3 join for
-- 20 customers against the forms that cannot be hashed
select 'V' as t,
  (select count(*) || '/' || count(o.o_orderkey) || '/' || coalesce(sum(o.o_orderkey), 0) from customer c
    left join orders o on c.c_custkey = o.o_custkey and o.o_comment not like '%special%requests%'
    where c.c_custkey between 1900 and 2100) as h1,
  (select count(*) || '/' || count(o.o_orderkey) || '/' || coalesce(sum(o.o_orderkey), 0) from customer c
    left join orders o on o.o_custkey between c.c_custkey and c.c_custkey
      and o.o_comment not like '%special%requests%'
    where c.c_custkey between 1900 and 2100) as h1_ref,
  (select count(*) || '/' || count(o.o_orderkey) || '/' || coalesce(sum(o.o_orderkey), 0) from customer c
    left join orders o on c.c_custkey = o.o_custkey and c.c_flag = 1
    where c.c_custkey between 1900 and 2100) as h2,
  (select count(*) || '/' || count(o.o_orderkey) || '/' || coalesce(sum(o.o_orderkey), 0) from customer c
    left join orders o on o.o_custkey between c.c_custkey and c.c_custkey and c.c_flag = 1
    where c.c_custkey between 1900 and 2100) as h2_ref,
  (select count(*) || '/' || count(b.b_id) || '/' || coalesce(sum(b.b_id), 0) from customer c
    left join big_orders b on c.c_custkey = b.b_custkey
    where c.c_custkey between 1990 and 2009) as h3,
  (select count(*) || '/' || count(b.b_id) || '/' || coalesce(sum(b.b_id), 0) from customer c
    left join big_orders b on b.b_custkey between c.c_custkey and c.c_custkey
    where c.c_custkey between 1990 and 2009) as h3_ref
from rdb$database;
