-- 59_eq_miss_lencap.sql - equality that misses the MCV list: no literal-length cap where equal strings differ in length (fix w15). Alias tst10rev.
-- Each query: tag with the real count, then the estimate (rows=) from set explain under set planonly.
-- q2 100 000 rows, 500 values x 200 rows each (n = lpad(mod(i, 500), 4, '0')), no index:
--   nfd VARCHAR(20) UTF8 COLLATE UNICODE       : 'cafe' || U+0301 || n (decomposed accent)
--   ai  VARCHAR(20) UTF8 COLLATE UNICODE_CI_AI : 'straße' || n
--   oc  CHAR(12) OCTETS                        : 'k' || n (zero padded to 12 bytes)
--   bv  VARCHAR(20) UTF8 (binary collation)    : 'b' || n          (control)
--   cn  CHAR(12) NONE                          : 'c' || n          (control)
-- 500 values of equal frequency: the equality is priced by the miss path (MCV miss).
set bail off;
set names utf8;
create database 'tst10rev' user SYSDBA;
create table q2 (nfd varchar(20) character set utf8 collate unicode,
  ai varchar(20) character set utf8 collate unicode_ci_ai,
  oc char(12) character set octets,
  bv varchar(20) character set utf8,
  cn char(12) character set none);
commit;
set term ^;
execute block as declare i int = 0; declare n varchar(4); begin
  while (i < 100000) do begin
    n = lpad(mod(:i, 500), 4, '0');
    insert into q2 values ('cafe' || _utf8 x'CC81' || :n, 'straße' || :n, 'k' || :n, 'b' || :n, 'c' || :n);
    i = i + 1; end
end^
set term ;^
commit;
alter database add extended statistics; commit;
alter database refresh statistics; commit;
connect 'tst10rev' user SYSDBA;

-- ===== fixed cases: MCV miss =====
select 'M1 ai = ''strasse0377'' (expected 200)' as tag, count(*) as real_cnt from q2 where ai = 'strasse0377';
set planonly on; set explain on;
select count(*) from q2 where ai = 'strasse0377';
set explain off; set planonly off; set plan off;
select 'M2 nfd = NFC ''café0377'' (expected 200)' as tag, count(*) as real_cnt from q2 where nfd = 'café0377';
set planonly on; set explain on;
select count(*) from q2 where nfd = 'café0377';
set explain off; set planonly off; set plan off;
select 'M3 oc = ''k0377'' CHAR(12) OCTETS (expected 200)' as tag, count(*) as real_cnt from q2 where oc = 'k0377';
set planonly on; set explain on;
select count(*) from q2 where oc = 'k0377';
set explain off; set planonly off; set plan off;
-- ===== controls (estimates must not change) =====
select 'C1 ai = ''straße0377'' same length as data (expected 200)' as tag, count(*) as real_cnt from q2 where ai = 'straße0377';
set planonly on; set explain on;
select count(*) from q2 where ai = 'straße0377';
set explain off; set planonly off; set plan off;
select 'C2 bv = ''b0377'' binary miss (expected 200)' as tag, count(*) as real_cnt from q2 where bv = 'b0377';
set planonly on; set explain on;
select count(*) from q2 where bv = 'b0377';
set explain off; set planonly off; set plan off;
select 'C3 bv = ''b03777'' binary, length cap (expected 0)' as tag, count(*) as real_cnt from q2 where bv = 'b03777';
set planonly on; set explain on;
select count(*) from q2 where bv = 'b03777';
set explain off; set planonly off; set plan off;
select 'C4 cn = ''c0377'' CHAR NONE miss (expected 200)' as tag, count(*) as real_cnt from q2 where cn = 'c0377';
set planonly on; set explain on;
select count(*) from q2 where cn = 'c0377';
set explain off; set planonly off; set plan off;
-- ===== changes on purpose: a longer literal under UNICODE_CI_AI loses its length cap =====
select 'X1 ai = ''strasse0377x'' (expected 0)' as tag, count(*) as real_cnt from q2 where ai = 'strasse0377x';
set planonly on; set explain on;
select count(*) from q2 where ai = 'strasse0377x';
set explain off; set planonly off; set plan off;
