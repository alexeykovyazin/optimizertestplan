-- 51_not_in_estimate.sql - NOT IN with a list of 2+ values is estimated as IN (no complement). Alias tst10like.
-- Cause: src/jrd/optimizer/Optimizer.cpp:1472-1476 (commit 24da50c73f): the branch NOT -> InListBoolNode
-- sets distListNode but not "negated = true" (the branch NOT -> ComparativeBoolNode at 1477-1493 sets it).
-- So 1628-1631 return the IN share instead of 1 - nullFraction - share, and 1615 (NOT IN with NULL) is dead.
-- One element "k not in (1)" is parsed as "k <> 1" and is correct. Needs ExtendedStatistics (column distribution).
-- Data: t 10 000 rows: k = mod(i, 50), kn = mod(i, 40) with 10% NULL, ki = k with index, d = 30 dates, s = 25 names;
-- big 500 000 rows: tk = mod(i, 10000) (index big_tk), pad = 'r' in 2 000 rows (index big_pad).
-- Expected rows= (real count) are in the comments; the J* joins must have the same count/sum.
set bail off;
create database 'tst10like' user SYSDBA page_size 8192;
create table t (id int not null primary key, k int, kn int, ki int, d date, s varchar(20));
create table big (id int not null primary key, tk int, pad varchar(20));
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 10000) do begin
    insert into t values (:i, mod(:i, 50), iif(mod(:i, 10) = 0, null, mod(:i, 40)), mod(:i, 50),
      dateadd(mod(:i, 30) day to date '2024-01-01'), 'name' || mod(:i, 25));
    i = i + 1; end
  i = 0;
  while (i < 500000) do begin
    insert into big values (:i, mod(:i, 10000), iif(mod(:i, 250) = 7, 'r', 'x' || mod(:i, 1000)));
    i = i + 1; end
end^
set term ;^
commit;
create index t_ki on t (ki);
create index big_tk on big (tk);
create index big_pad on big (pad);
commit;
alter database add extended statistics; commit;
alter database refresh statistics; commit;
connect 'tst10like' user SYSDBA;

set list on;
select 'R1 k not in (1, 2): 9600' as tag, count(*) as cnt from t where k not in (1, 2);
select 'R2 k not in (-5, -7): 10000' as tag, count(*) as cnt from t where k not in (-5, -7);
select 'R3 kn not in (1, 2): 8500' as tag, count(*) as cnt from t where kn not in (1, 2);
select 'R4 not (k in (1, 2, 3)): 9400' as tag, count(*) as cnt from t where not (k in (1, 2, 3));
select 'R5 d not in (2 dates): 9332' as tag, count(*) as cnt from t where d not in (date '2024-01-01', date '2024-01-02');
select 'R6 s not in (3 names): 9200' as tag, count(*) as cnt from t where s not in ('name1', 'name2', 'zzz');
select 'R7 k not in (10 values): 8000' as tag, count(*) as cnt from t where k not in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9);
select 'R8 k not in (1, null): 0' as tag, count(*) as cnt from t where k not in (1, null);
set list off;

set planonly on;
set explain on;
-- E1 real 9600 (bug: 400 = the IN share)
select count(*) from t where k not in (1, 2);
-- C1 control "<> and <>", real 9600
select count(*) from t where k <> 1 and k <> 2;
-- C2 control one element (parsed as <>), real 9800
select count(*) from t where k not in (1);
-- E2 values not in MCV, real 10000 (bug: 1)
select count(*) from t where k not in (-5, -7);
-- E3 nullable column, real 8500
select count(*) from t where kn not in (1, 2);
-- E4 NOT (x IN (...)), real 9400
select count(*) from t where not (k in (1, 2, 3));
-- E5 date, real 9332
select count(*) from t where d not in (date '2024-01-01', date '2024-01-02');
-- E6 text, real 9200
select count(*) from t where s not in ('name1', 'name2', 'zzz');
-- E7 ten values, real 8000
select count(*) from t where k not in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9);
-- E8 indexed column, real 9600
select count(*) from t where ki not in (1, 2);
-- E9 NULL in the list, real 0 (expected 1 row)
select count(*) from t where k not in (1, null);
set explain off;
set planonly off;

-- the bad plan: t is estimated 400 / 1 rows and drives a nested loop into big (BIG_TK + BIG_PAD bitmap per row);
-- the right plan reads 2 000 big rows by BIG_PAD and looks up t by its PK. Expected: 2000 / 499764000.
select count(*) from big where pad = 'r';
set list on;
set stats on;
select 'J1 not in (1, 2)' as tag, count(*) as cnt, sum(big.id) as sum_id
  from t join big on big.tk = t.id where t.k not in (1, 2) and big.pad = 'r';
select 'J2 <> and <> (control)' as tag, count(*) as cnt, sum(big.id) as sum_id
  from t join big on big.tk = t.id where t.k <> 1 and t.k <> 2 and big.pad = 'r';
select 'J3 not in (-5, -7)' as tag, count(*) as cnt, sum(big.id) as sum_id
  from t join big on big.tk = t.id where t.k not in (-5, -7) and big.pad = 'r';
set stats off;
set list off;
set planonly on;
select count(*) from t join big on big.tk = t.id where t.k not in (1, 2) and big.pad = 'r';
select count(*) from t join big on big.tk = t.id where t.k <> 1 and t.k <> 2 and big.pad = 'r';
set planonly off;
