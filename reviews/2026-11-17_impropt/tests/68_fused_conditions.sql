-- 68_fused_conditions.sql - the fused multi-river hash join verifies the matches of every hashed river by the
-- condition of this river (no filter above the river). Alias tst18fused (ShowExplainCardinality = true).
-- t1, t2, t3: 60 000 rows each, x = mod(i, 2000), every 500th row has x NULL. b: 4 200 000 rows, x = mod(i, 2000)
-- (above the capacity of the hash table: the batched hash join). k1, k2, k3: 2 000 000 rows each, the pair (x, y) is
-- unique, x = mod(j, 1500), y = j / 1500; j starts at 0, 1 000 000 and 1 500 000. Indexes on every key column, so
-- the tables stay in one river and the hash join is chosen by the cost.
-- Expected: F1 53 892 000, F2 2 694 600 (= N), F4 18 900 000 (= N), F5 500 000 / 874 999 750 000 (a key of 8 bytes: the hash collisions
-- of different keys must be rejected by the conditions of the rivers).
set bail off;
create database 'tst18fused' user SYSDBA;
create table t1 (id int not null, x int);
create table t2 (id int not null, x int);
create table t3 (id int not null, x int);
create table b (id int not null, x int);
create table k1 (id int not null, x int, y int);
create table k2 (id int not null, x int, y int);
create table k3 (id int not null, x int, y int);
commit;
set term ^;
execute block as declare i int = 0; declare vx int; begin
  while (i < 60000) do begin
    vx = iif(mod(i, 500) = 499, null, mod(i, 2000));
    insert into t1 values (:i, :vx);
    insert into t2 values (:i, :vx);
    insert into t3 values (:i, :vx);
    i = i + 1;
  end
end^
execute block as declare i int = 0; begin
  while (i < 4200000) do begin
    insert into b values (:i, mod(:i, 2000));
    i = i + 1;
  end
end^
execute block as declare i int = 0; declare j int; begin
  while (i < 2000000) do begin
    insert into k1 values (:i, mod(:i, 1500), :i / 1500);
    j = i + 1000000;
    insert into k2 values (:j, mod(:j, 1500), :j / 1500);
    j = i + 1500000;
    insert into k3 values (:j, mod(:j, 1500), :j / 1500);
    i = i + 1;
  end
end^
set term ;^
commit;
create index t1_x on t1 (x); create index t2_x on t2 (x); create index t3_x on t3 (x);
create index b_x on b (x);
create index k1_x on k1 (x); create index k1_y on k1 (y);
create index k2_x on k2 (x); create index k2_y on k2 (y);
create index k3_x on k3 (x); create index k3_y on k3 (y);
commit;

select 'P: plans' as tag from rdb$database;
set explain on; set planonly on;
-- F1: three rivers, one key, the whole tables
select count(*) from t1, t2, t3 where t1.x = t2.x and t1.x = t3.x;
-- F2: the edge of the third table is written against the second one
select count(*) from t1, t2, t3 where t1.x = t2.x and t2.x = t3.x and t1.id < 3000;
-- F4: the batched hash join over the fused river
select count(*) from t1, t2, t3, b where t1.x = t2.x and t1.x = t3.x and t1.x = b.x and t1.id < 10;
-- F5: two keys (8 bytes), the unique pairs
select count(*) from k1, k2, k3 where k1.x = k2.x and k1.y = k2.y and k1.x = k3.x and k1.y = k3.y;
set planonly off; set explain off;

select 'F: results' as tag from rdb$database;
set stat on;
select 'F1', count(*), sum(cast(t3.id as bigint)) from t1, t2, t3 where t1.x = t2.x and t1.x = t3.x;
set stat off;
select 'F2', count(*), sum(cast(t3.id as bigint)) from t1, t2, t3 where t1.x = t2.x and t2.x = t3.x and t1.id < 3000;
select 'F4', count(*), sum(cast(b.id as bigint)) from t1, t2, t3, b
  where t1.x = t2.x and t1.x = t3.x and t1.x = b.x and t1.id < 10;
select 'F5', count(*), sum(cast(k3.id as bigint)) from k1, k2, k3
  where k1.x = k2.x and k1.y = k2.y and k1.x = k3.x and k1.y = k3.y;

select 'N: the same queries by the nested loops' as tag from rdb$database;
select 'F2', count(*), sum(cast(t3.id as bigint)) from t1, t2, t3 where t1.x = t2.x and t2.x = t3.x and t1.id < 3000
  plan join (t1 natural, t2 index (t2_x), t3 index (t3_x));
select 'F4', count(*), sum(cast(b.id as bigint)) from t1, t2, t3, b
  where t1.x = t2.x and t1.x = t3.x and t1.x = b.x and t1.id < 10
  plan join (t1 natural, t2 index (t2_x), t3 index (t3_x), b index (b_x));
commit;
drop database;
