-- 65_star_fusion.sql - the fused multi-river hash join of 3eba645881 ("the star river fusion"). Alias tst13star
-- (ShowExplainCardinality = true).
-- t1, t2, t3, t4: 60 000 rows each, x = mod(i, 2000), y = mod(i, 3), z = mod(i, 7); every 500th row has x NULL,
-- every 700th row has y NULL. Indexes on x, y, z of every table, so the tables stay in one river and the hash join is
-- chosen by the cost.
-- Every query is run twice: by the plan of the optimizer and by the nested loops (section N). The numbers must be equal.
set bail off;
create database 'tst13star' user SYSDBA;
create table t1 (id int not null, x int, y int, z int);
create table t2 (id int not null, x int, y int, z int);
create table t3 (id int not null, x int, y int, z int);
create table t4 (id int not null, x int, y int, z int);
commit;
set term ^;
execute block as declare i int = 0; declare vx int; declare vy int; begin
  while (i < 60000) do begin
    vx = iif(mod(i, 500) = 499, null, mod(i, 2000));
    vy = iif(mod(i, 700) = 699, null, mod(i, 3));
    insert into t1 values (:i, :vx, :vy, mod(:i, 7));
    insert into t2 values (:i, :vx, :vy, mod(:i, 7));
    insert into t3 values (:i, :vx, :vy, mod(:i, 7));
    insert into t4 values (:i, :vx, :vy, mod(:i, 7));
    i = i + 1;
  end
end^
set term ;^
commit;
create index t1_x on t1 (x); create index t1_y on t1 (y); create index t1_z on t1 (z);
create index t2_x on t2 (x); create index t2_y on t2 (y); create index t2_z on t2 (z);
create index t3_x on t3 (x); create index t3_y on t3 (y); create index t3_z on t3 (z);
create index t4_x on t4 (x); create index t4_y on t4 (y); create index t4_z on t4 (z);
commit;

select 'S: plans' as tag from rdb$database;
set explain on; set planonly on;
-- S1: one key
select count(*) from t1, t2, t3 where t1.x = t2.x and t1.x = t3.x and t1.id < 3000;
-- S2: the seed join has two keys, the third table one key
select count(*) from t1, t2, t3 where t1.x = t2.x and t1.y = t2.y and t1.x = t3.x and t1.id < 3000;
-- S3: the seed join has one key, the third table two keys
select count(*) from t1, t2, t3 where t1.x = t2.x and t1.x = t3.x and t2.y = t3.y and t1.id < 3000;
-- S4: two keys, the conditions of the third table in the other order
select count(*) from t1, t2, t3 where t1.x = t2.x and t1.y = t2.y and t3.y = t1.y and t3.x = t1.x and t1.id < 3000;
-- S5: one class, plain equality and IS NOT DISTINCT FROM on the same key
select count(*) from t1, t2, t3 where t1.x = t2.x and t1.x = t3.x and t3.x is not distinct from t2.x and t1.id < 3000;
-- S6: IS NOT DISTINCT FROM only (NULL keys match)
select count(*) from t1, t2, t3 where t1.x is not distinct from t2.x and t1.x is not distinct from t3.x and t1.id < 600 and t2.id < 6000 and t3.id < 6000;
-- S7: four tables, one key
select count(*) from t1, t2, t3, t4 where t1.x = t2.x and t1.x = t3.x and t1.x = t4.x and t1.id < 300;
-- S8: four tables, the fourth one by another key
select count(*) from t1, t2, t3, t4 where t1.x = t2.x and t1.x = t3.x and t1.z = t4.z and t1.id < 30 and t4.id < 3000;
set planonly off; set explain off;

select 'S: results' as tag from rdb$database;
select 'S1', count(*), sum(cast(t3.id as bigint)) from t1, t2, t3 where t1.x = t2.x and t1.x = t3.x and t1.id < 3000;
select 'S2', count(*), sum(cast(t3.id as bigint)) from t1, t2, t3 where t1.x = t2.x and t1.y = t2.y and t1.x = t3.x and t1.id < 3000;
select 'S3', count(*), sum(cast(t3.id as bigint)) from t1, t2, t3 where t1.x = t2.x and t1.x = t3.x and t2.y = t3.y and t1.id < 3000;
select 'S4', count(*), sum(cast(t3.id as bigint)) from t1, t2, t3 where t1.x = t2.x and t1.y = t2.y and t3.y = t1.y and t3.x = t1.x and t1.id < 3000;
select 'S5', count(*), sum(cast(t3.id as bigint)) from t1, t2, t3 where t1.x = t2.x and t1.x = t3.x and t3.x is not distinct from t2.x and t1.id < 3000;
select 'S6', count(*), sum(cast(t3.id as bigint)) from t1, t2, t3 where t1.x is not distinct from t2.x and t1.x is not distinct from t3.x and t1.id < 600 and t2.id < 6000 and t3.id < 6000;
select 'S7', count(*), sum(cast(t4.id as bigint)) from t1, t2, t3, t4 where t1.x = t2.x and t1.x = t3.x and t1.x = t4.x and t1.id < 300;
select 'S8', count(*), sum(cast(t4.id as bigint)) from t1, t2, t3, t4 where t1.x = t2.x and t1.x = t3.x and t1.z = t4.z and t1.id < 30 and t4.id < 3000;

select 'N: the same queries by the nested loops' as tag from rdb$database;
select 'S1', count(*), sum(cast(t3.id as bigint)) from t1, t2, t3 where t1.x = t2.x and t1.x = t3.x and t1.id < 3000
  plan join (t1 natural, t2 index (t2_x), t3 index (t3_x));
select 'S2', count(*), sum(cast(t3.id as bigint)) from t1, t2, t3 where t1.x = t2.x and t1.y = t2.y and t1.x = t3.x and t1.id < 3000
  plan join (t1 natural, t2 index (t2_x), t3 index (t3_x));
select 'S3', count(*), sum(cast(t3.id as bigint)) from t1, t2, t3 where t1.x = t2.x and t1.x = t3.x and t2.y = t3.y and t1.id < 3000
  plan join (t1 natural, t2 index (t2_x), t3 index (t3_x));
select 'S4', count(*), sum(cast(t3.id as bigint)) from t1, t2, t3 where t1.x = t2.x and t1.y = t2.y and t3.y = t1.y and t3.x = t1.x and t1.id < 3000
  plan join (t1 natural, t2 index (t2_x), t3 index (t3_x));
select 'S5', count(*), sum(cast(t3.id as bigint)) from t1, t2, t3 where t1.x = t2.x and t1.x = t3.x and t3.x is not distinct from t2.x and t1.id < 3000
  plan join (t1 natural, t2 index (t2_x), t3 index (t3_x));
select 'S6', count(*), sum(cast(t3.id as bigint)) from t1, t2, t3 where t1.x is not distinct from t2.x and t1.x is not distinct from t3.x and t1.id < 600 and t2.id < 6000 and t3.id < 6000
  plan join (t1 natural, t2 natural, t3 natural);
select 'S7', count(*), sum(cast(t4.id as bigint)) from t1, t2, t3, t4 where t1.x = t2.x and t1.x = t3.x and t1.x = t4.x and t1.id < 300
  plan join (t1 natural, t2 index (t2_x), t3 index (t3_x), t4 index (t4_x));
select 'S8', count(*), sum(cast(t4.id as bigint)) from t1, t2, t3, t4 where t1.x = t2.x and t1.x = t3.x and t1.z = t4.z and t1.id < 30 and t4.id < 3000
  plan join (t1 natural, t2 index (t2_x), t3 index (t3_x), t4 index (t4_z));
commit;
drop database;
