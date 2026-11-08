create database 'probe5' user SYSDBA page_size 4096;
create table tz(x int, y int, p varchar(100));
create table t(x int, s varchar(30));
set term ^;
execute block as declare i int = 0; begin while (i < 100000) do begin
  insert into tz values(:i, mod(:i, 20000), lpad(:i, 100, 'abcdefghij'));
  insert into t values(:i, 'v' || mod(:i, 500));
  i = i + 1; end end^
set term ;^
commit;
set echo on;
-- ===== NOSTAT: no extended statistics store
set planonly on; set explain on;
select count(*) from tz where y > ?;
select count(*) from tz where y between ? and ?;
select count(*) from tz where y > 10000;
select count(*) from tz where y between 10000 and 10199;
select count(*) from tz where x >= 50000;
select count(*) from t where s >= 'v5';
set planonly off; set explain off;
alter database add extended statistics;
commit;
alter database refresh statistics sample for table tz;
commit;
alter database refresh statistics scan for table tz;
commit;
alter database refresh statistics for table t;
commit;
-- ===== WITH STATS run 1
set planonly on; set explain on;
select count(*) from tz where y between 10000 and 10199;
select count(*) from tz where y <= 10199;
select count(*) from tz where y >= 10000;
-- U9 same direction, real 25000
select count(*) from tz where y >= 10000 and y >= 15000;
select count(*) from tz where y >= 15000 and y >= 10000;
-- U9 same direction upper, real 25000
select count(*) from tz where y <= 4999 and y <= 9999;
-- U9 three bounds discriminating, real 55
select count(*) from tz where y >= 10000 and y <= 10199 and y <= 10010;
-- U9 three bounds, real 500
select count(*) from tz where y >= 10000 and y >= 10100 and y <= 10199;
-- R3 constant expression, real 99985
select count(*) from tz where y > 1 + 1;
-- NONE text range, real 11000
select count(*) from t where s >= 'v5';
-- unique grid edges
-- empty, real 0
select count(*) from tz where x between 60000 and 50000;
-- real 0
select count(*) from tz where x > 50000 and x < 50001;
-- real 1
select count(*) from tz where x >= 99999;
-- real 1
select count(*) from tz where x <= 0;
-- real 1000
select count(*) from tz where x between 99000 and 99999;
-- real 1000
select count(*) from tz where x >= 99000;
-- real 1000
select count(*) from tz where x >= 50000 and x < 51000;
-- real 999
select count(*) from tz where x > 50000 and x < 51000;
-- real 0
select count(*) from tz where x > 99999;
set planonly off; set explain off;
-- ===== noise: refresh scan again twice
alter database refresh statistics scan for table tz;
commit;
set planonly on; set explain on;
select count(*) from tz where y between 10000 and 10199;
select count(*) from tz where y >= 10000 and y >= 15000;
select count(*) from tz where x between 50000 and 50999;
set planonly off; set explain off;
alter database refresh statistics scan for table tz;
commit;
set planonly on; set explain on;
select count(*) from tz where y between 10000 and 10199;
select count(*) from tz where y >= 10000 and y >= 15000;
select count(*) from tz where x between 50000 and 50999;
set planonly off; set explain off;
-- ===== tzi index path vs full scan
create table tzi(x int, y int);
insert into tzi select x, y from tz;
commit;
create index tzi_x on tzi(x);
create index tzi_y on tzi(y);
commit;
alter database refresh statistics for table tzi;
commit;
set planonly on; set explain on;
select count(*) from tzi where y between 10000 and 10199;
select count(*) from tzi where y + 0 between 10000 and 10199;
select count(*) from tzi where y >= 10000 and y <= 10199;
select count(*) from tzi where y = 10000;
set planonly off; set explain off;
alter database refresh statistics for table tzi;
commit;
set planonly on; set explain on;
select count(*) from tzi where y between 10000 and 10199;
select count(*) from tzi where y + 0 between 10000 and 10199;
set planonly off; set explain off;
alter database refresh statistics for table tzi;
commit;
set planonly on; set explain on;
select count(*) from tzi where y between 10000 and 10199;
select count(*) from tzi where y + 0 between 10000 and 10199;
set planonly off; set explain off;
select count(*) from tzi where y between 10000 and 10199;
