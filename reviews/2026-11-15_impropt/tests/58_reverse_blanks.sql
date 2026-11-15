-- 58_reverse_blanks.sql - reverse STARTING WITH / CONTAINING with trailing blanks in the literal (fix y12). Alias tst10rev.
-- Each query: tag with the real count, then the estimate (rows=) from set explain under set planonly.
-- r 100 000 rows, no index:
--   tr  VARCHAR(20): 'abc' in 5 000 rows, other 'q' || i (unique)
--   tb  VARCHAR(20): 'abc  ' (stored with 2 blanks) in 5 000 rows, other 'q' || i
--   bs  VARCHAR(20): 'Bob' in 5 000 rows, other 'q' || i
--   nm2 VARCHAR(60): 'Anna Kowalski' in 1 400 rows, other 'Bob Smith' || nnnn
--   chu CHAR(10):    'abc' in 50 000 rows, other 'w' || i
set bail off;
create database 'tst10rev' user SYSDBA;
create table r (id int not null, tr varchar(20), tb varchar(20), bs varchar(20), nm2 varchar(60), chu char(10));
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 100000) do begin
    insert into r values (:i,
      iif(mod(:i, 20) = 0, 'abc', 'q' || :i),
      iif(mod(:i, 20) = 1, 'abc  ', 'q' || :i),
      iif(mod(:i, 20) = 2, 'Bob', 'q' || :i),
      iif(mod(:i, 1000) < 14, 'Anna Kowalski', 'Bob Smith' || lpad(mod(:i, 10000), 4, '0')),
      iif(mod(:i, 2) = 0, 'abc', 'w' || :i));
    i = i + 1; end
end^
set term ;^
commit;
alter database add extended statistics; commit;
alter database refresh statistics; commit;
connect 'tst10rev' user SYSDBA;

-- ===== fixed cases =====
select 'A1 ''abc     '' starting with tr (expected 5000)' as tag, count(*) as real_cnt from r where 'abc     ' starting with tr;
set planonly on; set explain on;
select count(*) from r where 'abc     ' starting with tr;
set explain off; set planonly off; set plan off;
select 'A2 ''Kowalski   '' containing nm2 (expected 0)' as tag, count(*) as real_cnt from r where 'Kowalski   ' containing nm2;
set planonly on; set explain on;
select count(*) from r where 'Kowalski   ' containing nm2;
set explain off; set planonly off; set plan off;
select 'A3 ''abc      '' starting with tb (expected 5000)' as tag, count(*) as real_cnt from r where 'abc      ' starting with tb;
set planonly on; set explain on;
select count(*) from r where 'abc      ' starting with tb;
set explain off; set planonly off; set plan off;
select 'A4 ''Bob Smith'' starting with bs (expected 5000)' as tag, count(*) as real_cnt from r where 'Bob Smith' starting with bs;
set planonly on; set explain on;
select count(*) from r where 'Bob Smith' starting with bs;
set explain off; set planonly off; set plan off;
-- ===== controls (estimates must not change) =====
select 'C1 ''abc'' starting with tr (expected 5000)' as tag, count(*) as real_cnt from r where 'abc' starting with tr;
set planonly on; set explain on;
select count(*) from r where 'abc' starting with tr;
set explain off; set planonly off; set plan off;
select 'C2 ''Kowalski'' containing nm2 (expected 0)' as tag, count(*) as real_cnt from r where 'Kowalski' containing nm2;
set planonly on; set explain on;
select count(*) from r where 'Kowalski' containing nm2;
set explain off; set planonly off; set plan off;
select 'C3 W14 ''abc       '' starting with chu (expected 50000)' as tag, count(*) as real_cnt from r where 'abc       ' starting with chu;
set planonly on; set explain on;
select count(*) from r where 'abc       ' starting with chu;
set explain off; set planonly off; set plan off;
select 'C4 ''xxabc       yy'' containing chu (expected 50000)' as tag, count(*) as real_cnt from r where 'xxabc       yy' containing chu;
set planonly on; set explain on;
select count(*) from r where 'xxabc       yy' containing chu;
set explain off; set planonly off; set plan off;
select 'C5 tr starting with ''abc'' (expected 5000)' as tag, count(*) as real_cnt from r where tr starting with 'abc';
set planonly on; set explain on;
select count(*) from r where tr starting with 'abc';
set explain off; set planonly off; set plan off;
