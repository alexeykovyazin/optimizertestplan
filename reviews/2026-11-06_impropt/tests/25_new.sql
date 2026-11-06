connect 'tst2' user SYSDBA;
-- copy of tz with indexes on x (unique values) and y (20000 values x 5 rows)
create table tzi(x int, y int);
insert into tzi select x, y from tz;
commit;
create index tzi_x on tzi(x);
create index tzi_y on tzi(y);
commit;
alter database refresh statistics for table tzi;
commit;
set planonly on;
set explain on;
-- R4 with an index on the column: expected 1000
select count(*) from tzi where y between 10000 and 10199;
-- R1 with an index on the unique column: expected 1000
select count(*) from tzi where x between 50000 and 50999;
-- same direction pair: expected 25000
select count(*) from tz where y >= 10000 and y >= 15000;
-- three bounds: expected 505
select count(*) from tz where y >= 10000 and y <= 10199 and y <= 10100;
-- empty range: expected 0
select count(*) from tz where y between 10199 and 10000;
-- field on the right side: expected 1000
select count(*) from tz where 10199 >= y and 10000 <= y;
-- reversed STARTING: prefixes v1, v12, v123 -> expected 600
select count(*) from t where 'v123' starting with s;
-- reversed CONTAINING: substrings v1, v12 -> expected 400
select count(*) from t where 'xv12y' containing s;
-- reversed LIKE: legacy estimate, expected 200
select count(*) from t where 'v123' like s;
-- unique column, values outside [min, max]: expected 0 and 100000
select count(*) from tz where x > 200000;
select count(*) from tz where x >= -5;
set planonly off;
select count(*) from tzi where y between 10000 and 10199;
select count(*) from tz where y >= 10000 and y >= 15000;
select count(*) from tz where y >= 10000 and y <= 10199 and y <= 10100;
select count(*) from t where 'v123' starting with s;
select count(*) from t where 'xv12y' containing s;
select count(*) from t where 'v123' like s;
