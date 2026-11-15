-- 49_desc_range_reverse.sql - Y9 (b44d87f9be): strict bounds on a heavy value with a DESCENDING index; W9 parameter + literal on an indexed column; Y12 (dc2e6c19b1): reverse STARTING WITH / CONTAINING with trailing blanks. Alias tst10desc.
-- Each query: tag with the real count, then the estimate (rows=) from set explain under set planonly.
-- t 100 000 rows: xi = xd = 1 (40%), 1000 (20%), unique 50007..150000 (30%), NULL (10%). ixi ASC on xi, ixd DESC on xd.
-- r 100 000 rows: tr = 'abc' in 5 000 rows; nm2 = 'Anna Kowalski' in 1 400 rows, other 'Bob Smith' || nnnn. No index on r.
set bail off;
create database 'tst10desc' user SYSDBA;
create table t (id int not null primary key, xi int, xd int, g int, pad varchar(40));
create table r (id int not null, tr varchar(20), nm2 varchar(60));
commit;
set term ^;
execute block as declare i int = 1; declare v int; begin
  while (i <= 100000) do begin
    v = case when mod(i, 10) = 0 then null
             when mod(i, 10) between 1 and 4 then 1
             when mod(i, 10) between 5 and 6 then 1000
             else 50000 + i end;
    insert into t values (:i, :v, :v, mod(:i, 50), 'x');
    i = i + 1; end
  i = 0;
  while (i < 100000) do begin
    insert into r values (:i, iif(mod(:i, 20) = 0, 'abc', 'q' || :i),
      iif(mod(:i, 1000) < 14, 'Anna Kowalski', 'Bob Smith' || lpad(mod(:i, 10000), 4, '0')));
    i = i + 1; end
end^
set term ;^
commit;
create index ixi on t (xi);
create descending index ixd on t (xd);
commit;
alter database add extended statistics; commit;
alter database refresh statistics; commit;
connect 'tst10desc' user SYSDBA;

-- ===== Y9: DESC index (xd) against ASC index (xi), the same data =====
select 'Y9a-asc xi < 1 (expected 0)' as tag, count(*) as real_cnt from t where xi < 1;
set planonly on; set explain on;
select count(*) from t where xi < 1;
set explain off; set planonly off; set plan off;
select 'Y9a-desc xd < 1 (expected 0)' as tag, count(*) as real_cnt from t where xd < 1;
set planonly on; set explain on;
select count(*) from t where xd < 1;
set explain off; set planonly off; set plan off;
select 'Y9b-asc xi > 1 (expected 50000)' as tag, count(*) as real_cnt from t where xi > 1;
set planonly on; set explain on;
select count(*) from t where xi > 1;
set explain off; set planonly off; set plan off;
select 'Y9b-desc xd > 1 (expected 50000)' as tag, count(*) as real_cnt from t where xd > 1;
set planonly on; set explain on;
select count(*) from t where xd > 1;
set explain off; set planonly off; set plan off;
select 'Y9c-asc xi >= 1 and xi < 1000 (expected 40000)' as tag, count(*) as real_cnt from t where xi >= 1 and xi < 1000;
set planonly on; set explain on;
select count(*) from t where xi >= 1 and xi < 1000;
set explain off; set planonly off; set plan off;
select 'Y9c-desc xd >= 1 and xd < 1000 (expected 40000)' as tag, count(*) as real_cnt from t where xd >= 1 and xd < 1000;
set planonly on; set explain on;
select count(*) from t where xd >= 1 and xd < 1000;
set explain off; set planonly off; set plan off;
select 'Y9d-asc xi > 1 and xi <= 1000 (expected 20000)' as tag, count(*) as real_cnt from t where xi > 1 and xi <= 1000;
set planonly on; set explain on;
select count(*) from t where xi > 1 and xi <= 1000;
set explain off; set planonly off; set plan off;
select 'Y9d-desc xd > 1 and xd <= 1000 (expected 20000)' as tag, count(*) as real_cnt from t where xd > 1 and xd <= 1000;
set planonly on; set explain on;
select count(*) from t where xd > 1 and xd <= 1000;
set explain off; set planonly off; set plan off;
-- control: non-strict bound on the heavy value
select 'Y9e-desc xd <= 1 (expected 40000)' as tag, count(*) as real_cnt from t where xd <= 1;
set planonly on; set explain on;
select count(*) from t where xd <= 1;
set explain off; set planonly off; set plan off;
-- ===== W9: parameter and literal on the same side, indexed column; real count of xi < 60000 = 63000 =====
select 'W9-real xi < 60000 (expected 63000)' as tag, count(*) as real_cnt from t where xi < 60000;
set planonly on; set explain on;
select count(*) from t where xi < 60000;
set explain off; set planonly off; set plan off;
select 'W9a xi < ? and xi < 60000' as tag from rdb$database;
set planonly on; set explain on;
select count(*) from t where xi < ? and xi < 60000;
set explain off; set planonly off; set plan off;
select 'W9b xi < 60000 and xi < ?' as tag from rdb$database;
set planonly on; set explain on;
select count(*) from t where xi < 60000 and xi < ?;
set explain off; set planonly off; set plan off;
select 'W9c xd < ? and xd < 60000' as tag from rdb$database;
set planonly on; set explain on;
select count(*) from t where xd < ? and xd < 60000;
set explain off; set planonly off; set plan off;
select 'W9d xd < 60000 and xd < ?' as tag from rdb$database;
set planonly on; set explain on;
select count(*) from t where xd < 60000 and xd < ?;
set explain off; set planonly off; set plan off;
-- ===== Y12: reverse predicates with trailing blanks in the literal =====
select 'Y12a ''abc     '' starting with tr (expected 5000)' as tag, count(*) as real_cnt from r where 'abc     ' starting with tr;
set planonly on; set explain on;
select count(*) from r where 'abc     ' starting with tr;
set explain off; set planonly off; set plan off;
select 'Y12b ''abc'' starting with tr (expected 5000, control)' as tag, count(*) as real_cnt from r where 'abc' starting with tr;
set planonly on; set explain on;
select count(*) from r where 'abc' starting with tr;
set explain off; set planonly off; set plan off;
select 'Y12c ''Kowalski   '' containing nm2 (expected 0)' as tag, count(*) as real_cnt from r where 'Kowalski   ' containing nm2;
set planonly on; set explain on;
select count(*) from r where 'Kowalski   ' containing nm2;
set explain off; set planonly off; set plan off;
select 'Y12d ''Kowalski'' containing nm2 (expected 0, control)' as tag, count(*) as real_cnt from r where 'Kowalski' containing nm2;
set planonly on; set explain on;
select count(*) from r where 'Kowalski' containing nm2;
set explain off; set planonly off; set plan off;
