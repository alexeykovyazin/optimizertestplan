-- 57_in_notin_estimates.sql - IN / NOT IN list estimates: NOT IN must be the complement of IN
-- (selectivity = 1 - nullFraction - IN share, at least one row). Alias tst10like.
-- Each query: tag with the real count, then the estimate (rows=) from set explain under set planonly.
-- t 20 000 rows:
--   k  = mod(i, 50)                     every value in the MCV list, 400 rows each
--   kn = mod(i, 40), NULL when mod(i, 10) = 0 (10% NULL)
--   u  = 0 or 4 when mod(i, 4) = 0 (2 500 rows each), otherwise i (unique, not in the MCV list)
--   d  = 30 dates from 2024-01-01 (666-667 rows each)
--   dd = 1999-12-31 when mod(i, 5) = 0 (4 000 rows), otherwise 2000-01-01 + i days (unique)
set bail off;
create database 'tst10like' user SYSDBA;
create table t (id int not null primary key, k int, kn int, u int, d date, dd date);
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 20000) do begin
    insert into t values (:i, mod(:i, 50), iif(mod(:i, 10) = 0, null, mod(:i, 40)),
      iif(mod(:i, 4) = 0, mod(:i, 8), :i),
      dateadd(mod(:i, 30) day to date '2024-01-01'),
      iif(mod(:i, 5) = 0, date '1999-12-31', dateadd(:i day to date '2000-01-01')));
    i = i + 1; end
end^
set term ;^
commit;
alter database add extended statistics; commit;
alter database refresh statistics; commit;
connect 'tst10like' user SYSDBA;

select 'k in 1 MCV' as tag, count(*) as real_cnt from t where k in (1);
set planonly on; set explain on;
select count(*) from t where k in (1);
set explain off; set planonly off;
select 'k not in 1 MCV' as tag, count(*) as real_cnt from t where k not in (1);
set planonly on; set explain on;
select count(*) from t where k not in (1);
set explain off; set planonly off;
select 'k in 2 MCV' as tag, count(*) as real_cnt from t where k in (1, 2);
set planonly on; set explain on;
select count(*) from t where k in (1, 2);
set explain off; set planonly off;
select 'k not in 2 MCV' as tag, count(*) as real_cnt from t where k not in (1, 2);
set planonly on; set explain on;
select count(*) from t where k not in (1, 2);
set explain off; set planonly off;
select 'k in 10 MCV' as tag, count(*) as real_cnt from t where k in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9);
set planonly on; set explain on;
select count(*) from t where k in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9);
set explain off; set planonly off;
select 'k not in 10 MCV' as tag, count(*) as real_cnt from t where k not in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9);
set planonly on; set explain on;
select count(*) from t where k not in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9);
set explain off; set planonly off;
select 'k in 2 absent' as tag, count(*) as real_cnt from t where k in (-5, -7);
set planonly on; set explain on;
select count(*) from t where k in (-5, -7);
set explain off; set planonly off;
select 'k not in 2 absent' as tag, count(*) as real_cnt from t where k not in (-5, -7);
set planonly on; set explain on;
select count(*) from t where k not in (-5, -7);
set explain off; set planonly off;
select 'not (k in 3 MCV)' as tag, count(*) as real_cnt from t where not (k in (1, 2, 3));
set planonly on; set explain on;
select count(*) from t where not (k in (1, 2, 3));
set explain off; set planonly off;
select 'kn in 2 MCV (10% NULL)' as tag, count(*) as real_cnt from t where kn in (1, 2);
set planonly on; set explain on;
select count(*) from t where kn in (1, 2);
set explain off; set planonly off;
select 'kn not in 2 MCV (10% NULL)' as tag, count(*) as real_cnt from t where kn not in (1, 2);
set planonly on; set explain on;
select count(*) from t where kn not in (1, 2);
set explain off; set planonly off;
select 'k not in (1, null)' as tag, count(*) as real_cnt from t where k not in (1, null);
set planonly on; set explain on;
select count(*) from t where k not in (1, null);
set explain off; set planonly off;
select 'u in 1 MCV' as tag, count(*) as real_cnt from t where u in (0);
set planonly on; set explain on;
select count(*) from t where u in (0);
set explain off; set planonly off;
select 'u not in 1 MCV' as tag, count(*) as real_cnt from t where u not in (0);
set planonly on; set explain on;
select count(*) from t where u not in (0);
set explain off; set planonly off;
select 'u in 2 MCV' as tag, count(*) as real_cnt from t where u in (0, 4);
set planonly on; set explain on;
select count(*) from t where u in (0, 4);
set explain off; set planonly off;
select 'u not in 2 MCV' as tag, count(*) as real_cnt from t where u not in (0, 4);
set planonly on; set explain on;
select count(*) from t where u not in (0, 4);
set explain off; set planonly off;
select 'u in 2 non-MCV' as tag, count(*) as real_cnt from t where u in (1001, 1003);
set planonly on; set explain on;
select count(*) from t where u in (1001, 1003);
set explain off; set planonly off;
select 'u not in 2 non-MCV' as tag, count(*) as real_cnt from t where u not in (1001, 1003);
set planonly on; set explain on;
select count(*) from t where u not in (1001, 1003);
set explain off; set planonly off;
select 'u in 10 non-MCV' as tag, count(*) as real_cnt from t where u in (1001, 1002, 1003, 1005, 1006, 1007, 1009, 1010, 1011, 1013);
set planonly on; set explain on;
select count(*) from t where u in (1001, 1002, 1003, 1005, 1006, 1007, 1009, 1010, 1011, 1013);
set explain off; set planonly off;
select 'u not in 10 non-MCV' as tag, count(*) as real_cnt from t where u not in (1001, 1002, 1003, 1005, 1006, 1007, 1009, 1010, 1011, 1013);
set planonly on; set explain on;
select count(*) from t where u not in (1001, 1002, 1003, 1005, 1006, 1007, 1009, 1010, 1011, 1013);
set explain off; set planonly off;
select 'u not in MCV + non-MCV' as tag, count(*) as real_cnt from t where u not in (0, 1001);
set planonly on; set explain on;
select count(*) from t where u not in (0, 1001);
set explain off; set planonly off;
select 'd in 1 MCV' as tag, count(*) as real_cnt from t where d in (date '2024-01-01');
set planonly on; set explain on;
select count(*) from t where d in (date '2024-01-01');
set explain off; set planonly off;
select 'd not in 1 MCV' as tag, count(*) as real_cnt from t where d not in (date '2024-01-01');
set planonly on; set explain on;
select count(*) from t where d not in (date '2024-01-01');
set explain off; set planonly off;
select 'd in 2 MCV' as tag, count(*) as real_cnt from t where d in (date '2024-01-01', date '2024-01-02');
set planonly on; set explain on;
select count(*) from t where d in (date '2024-01-01', date '2024-01-02');
set explain off; set planonly off;
select 'd not in 2 MCV' as tag, count(*) as real_cnt from t where d not in (date '2024-01-01', date '2024-01-02');
set planonly on; set explain on;
select count(*) from t where d not in (date '2024-01-01', date '2024-01-02');
set explain off; set planonly off;
select 'd in 10 MCV' as tag, count(*) as real_cnt from t where d in (date '2024-01-01', date '2024-01-02', date '2024-01-03', date '2024-01-04', date '2024-01-05', date '2024-01-06', date '2024-01-07', date '2024-01-08', date '2024-01-09', date '2024-01-10');
set planonly on; set explain on;
select count(*) from t where d in (date '2024-01-01', date '2024-01-02', date '2024-01-03', date '2024-01-04', date '2024-01-05', date '2024-01-06', date '2024-01-07', date '2024-01-08', date '2024-01-09', date '2024-01-10');
set explain off; set planonly off;
select 'd not in 10 MCV' as tag, count(*) as real_cnt from t where d not in (date '2024-01-01', date '2024-01-02', date '2024-01-03', date '2024-01-04', date '2024-01-05', date '2024-01-06', date '2024-01-07', date '2024-01-08', date '2024-01-09', date '2024-01-10');
set planonly on; set explain on;
select count(*) from t where d not in (date '2024-01-01', date '2024-01-02', date '2024-01-03', date '2024-01-04', date '2024-01-05', date '2024-01-06', date '2024-01-07', date '2024-01-08', date '2024-01-09', date '2024-01-10');
set explain off; set planonly off;
select 'dd in 2 non-MCV' as tag, count(*) as real_cnt from t where dd in (date '2000-01-03', date '2000-01-05');
set planonly on; set explain on;
select count(*) from t where dd in (date '2000-01-03', date '2000-01-05');
set explain off; set planonly off;
select 'dd not in 2 non-MCV' as tag, count(*) as real_cnt from t where dd not in (date '2000-01-03', date '2000-01-05');
set planonly on; set explain on;
select count(*) from t where dd not in (date '2000-01-03', date '2000-01-05');
set explain off; set planonly off;
select 'dd not in 1 MCV + 1 non-MCV' as tag, count(*) as real_cnt from t where dd not in (date '1999-12-31', date '2000-01-03');
set planonly on; set explain on;
select count(*) from t where dd not in (date '1999-12-31', date '2000-01-03');
set explain off; set planonly off;
