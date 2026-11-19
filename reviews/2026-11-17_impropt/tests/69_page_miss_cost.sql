-- 69_page_miss_cost.sql - the join method choice prices the page accesses the page cache cannot hold
-- (OptimizerPageMissCost). Three aliases with the same data:
--   tst19miss    - DefaultDbCachePages = 1024 (the tables are larger than the cache);
--   tst19missbig - DefaultDbCachePages = 20000 (everything fits the cache);
--   tst19missoff - DefaultDbCachePages = 1024, OptimizerPageMissCost = 0 (the miss pricing is off).
-- t_s: 400 000 rows, k = mod(i * 7919, 100000): 4 rows per key, scattered over the table.
-- t_c: 400 000 rows, k = i / 4: 4 rows per key, adjacent (clustered).
-- o6: 6 000 rows, k = id * 16 (the keys are spread over both tables).
-- o20, o20n: 20 000 rows, k = id * 5, stored in the order of k; o20 has an index on k, o20n has none.
-- Expected plans: tst19miss - M1 hash join (the nested loop reads about 5 pages per lookup out of the cache),
-- M2 nested loop (about 2 pages per lookup), M3 nested loop (the lookups come in the key order and share their
-- pages), M4 hash join (the same lookups, their order is not known); tst19missbig and tst19missoff - nested loop
-- in all four.
-- Expected counts: M1, M2 24 000; M3, M4 80 000.
set bail off;
create database 'tst19miss' user SYSDBA;
create table t_s (id int not null, k int, pad varchar(120));
create table t_c (id int not null, k int, pad varchar(120));
create table o6 (id int not null, k int);
create table o20 (id int not null, k int);
create table o20n (id int not null, k int);
commit;
set term ^;
execute block as declare i int = 0; declare p varchar(120); begin
  while (i < 400000) do begin
    p = uuid_to_char(gen_uuid()) || uuid_to_char(gen_uuid()) || uuid_to_char(gen_uuid());
    insert into t_s values (:i, mod(:i * 7919, 100000), :p);
    insert into t_c values (:i, :i / 4, :p);
    i = i + 1;
  end
end^
execute block as declare i int = 0; begin
  while (i < 6000) do begin
    insert into o6 values (:i, :i * 16);
    i = i + 1;
  end
end^
execute block as declare i int = 0; begin
  while (i < 20000) do begin
    insert into o20 values (:i, :i * 5);
    insert into o20n values (:i, :i * 5);
    i = i + 1;
  end
end^
set term ;^
commit;
create index t_s_k on t_s (k);
create index t_c_k on t_c (k);
create index o20_k on o20 (k);
commit;

select 'small cache' as case_name, mon$page_buffers as page_buffers from mon$database;
set plan on;
-- M1: scattered rows
select count(*) as m1 from o6 o join t_s i on i.k = o.k;
-- M2: clustered rows
select count(*) as m2 from o6 o join t_c i on i.k = o.k;
-- M3: clustered rows, the lookups come in the key order (o20 is stored in the order of k, the index o20_k shows it)
select count(*) as m3 from o20 o join t_c i on i.k = o.k;
-- M4: the same rows, the order of the lookups is not known (no index on o20n.k)
select count(*) as m4 from o20n o join t_c i on i.k = o.k;
set plan off;
commit;
drop database;

create database 'tst19missbig' user SYSDBA;
create table t_s (id int not null, k int, pad varchar(120));
create table t_c (id int not null, k int, pad varchar(120));
create table o6 (id int not null, k int);
create table o20 (id int not null, k int);
create table o20n (id int not null, k int);
commit;
set term ^;
execute block as declare i int = 0; declare p varchar(120); begin
  while (i < 400000) do begin
    p = uuid_to_char(gen_uuid()) || uuid_to_char(gen_uuid()) || uuid_to_char(gen_uuid());
    insert into t_s values (:i, mod(:i * 7919, 100000), :p);
    insert into t_c values (:i, :i / 4, :p);
    i = i + 1;
  end
end^
execute block as declare i int = 0; begin
  while (i < 6000) do begin
    insert into o6 values (:i, :i * 16);
    i = i + 1;
  end
end^
execute block as declare i int = 0; begin
  while (i < 20000) do begin
    insert into o20 values (:i, :i * 5);
    insert into o20n values (:i, :i * 5);
    i = i + 1;
  end
end^
set term ;^
commit;
create index t_s_k on t_s (k);
create index t_c_k on t_c (k);
create index o20_k on o20 (k);
commit;

select 'large cache' as case_name, mon$page_buffers as page_buffers from mon$database;
set plan on;
-- M1: scattered rows
select count(*) as m1 from o6 o join t_s i on i.k = o.k;
-- M2: clustered rows
select count(*) as m2 from o6 o join t_c i on i.k = o.k;
-- M3: clustered rows, the lookups come in the key order (o20 is stored in the order of k, the index o20_k shows it)
select count(*) as m3 from o20 o join t_c i on i.k = o.k;
-- M4: the same rows, the order of the lookups is not known (no index on o20n.k)
select count(*) as m4 from o20n o join t_c i on i.k = o.k;
set plan off;
commit;
drop database;

create database 'tst19missoff' user SYSDBA;
create table t_s (id int not null, k int, pad varchar(120));
create table t_c (id int not null, k int, pad varchar(120));
create table o6 (id int not null, k int);
create table o20 (id int not null, k int);
create table o20n (id int not null, k int);
commit;
set term ^;
execute block as declare i int = 0; declare p varchar(120); begin
  while (i < 400000) do begin
    p = uuid_to_char(gen_uuid()) || uuid_to_char(gen_uuid()) || uuid_to_char(gen_uuid());
    insert into t_s values (:i, mod(:i * 7919, 100000), :p);
    insert into t_c values (:i, :i / 4, :p);
    i = i + 1;
  end
end^
execute block as declare i int = 0; begin
  while (i < 6000) do begin
    insert into o6 values (:i, :i * 16);
    i = i + 1;
  end
end^
execute block as declare i int = 0; begin
  while (i < 20000) do begin
    insert into o20 values (:i, :i * 5);
    insert into o20n values (:i, :i * 5);
    i = i + 1;
  end
end^
set term ;^
commit;
create index t_s_k on t_s (k);
create index t_c_k on t_c (k);
create index o20_k on o20 (k);
commit;

select 'miss cost off' as case_name, mon$page_buffers as page_buffers from mon$database;
set plan on;
-- M1: scattered rows
select count(*) as m1 from o6 o join t_s i on i.k = o.k;
-- M2: clustered rows
select count(*) as m2 from o6 o join t_c i on i.k = o.k;
-- M3: clustered rows, the lookups come in the key order (o20 is stored in the order of k, the index o20_k shows it)
select count(*) as m3 from o20 o join t_c i on i.k = o.k;
-- M4: the same rows, the order of the lookups is not known (no index on o20n.k)
select count(*) as m4 from o20n o join t_c i on i.k = o.k;
set plan off;
commit;
drop database;
