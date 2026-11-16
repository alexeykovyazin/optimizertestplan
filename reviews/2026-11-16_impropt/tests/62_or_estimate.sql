-- 62_or_estimate.sql - OR estimate after 283ef14eaf (s1 + s2 - s1*s2). Aliases tst11ordef (default config), tst11or (PredicateCorrelation = true, extended statistics).
-- t: 100 000 rows, a = mod(i,2), b = mod(i/2,2), x = i. Real: a=1 or b=1 -> 75 000; a=0 or a=1 -> 100 000; chain of 10 ranges x<10000 .. x<19000 -> 19 000.
-- O1 (default config): the estimates must be the same as before the commit ("false does not change a single estimate").
-- O2 (correlation on): the chain of overlapping ranges.
set bail off;
create database 'tst11ordef' user SYSDBA;
create table t (a int, b int, x int); create index t_a on t(a); create index t_b on t(b); create index t_x on t(x);
commit;
set term ^;
execute block as declare i int = 0; begin while (i < 100000) do begin insert into t values (mod(:i,2), mod(:i/2,2), :i); i = i + 1; end end^
set term ;^
commit;
set statistics index t_a; set statistics index t_b; set statistics index t_x; commit;
select 'O1: default config' as tag from rdb$database;
set explain on; set planonly on;
select count(*) from t where a = 1 or b = 1;
select count(*) from t where a = 0 or a = 1;
select count(*) from t where a = 1 or b = 1 or x = 5;
set planonly off; set explain off;
commit;
create database 'tst11or' user SYSDBA;
create table t (a int, b int, x int); create index t_a on t(a); create index t_b on t(b); create index t_x on t(x);
commit;
set term ^;
execute block as declare i int = 0; begin while (i < 100000) do begin insert into t values (mod(:i,2), mod(:i/2,2), :i); i = i + 1; end end^
set term ;^
commit;
alter database add extended statistics; commit;
alter database refresh statistics full; commit;
connect 'tst11or' user SYSDBA;
select 'O2: correlation on' as tag from rdb$database;
set explain on; set planonly on;
select count(*) from t where a = 1 or b = 1;
select count(*) from t where a = 0 or a = 1;
select count(*) from t where x < 10000 or x < 11000 or x < 12000 or x < 13000 or x < 14000 or x < 15000 or x < 16000 or x < 17000 or x < 18000 or x < 19000;
select count(*) from t where x < 10000 or x < 19000;
select count(*) from t where x between 0 and 999 or x between 500 and 1499 or x between 1000 and 1999;
select count(*) from t where x < 10000 or x > 90000;
select count(*) from t where x > 10000 or x < 90000;
select count(*) from t where 10000 > x or x < 19000;
select count(*) from t where a = 1 or a = 0 or a = 1 or b = 1;
