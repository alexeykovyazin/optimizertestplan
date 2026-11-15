-- 54_old_stat_storage.sql - W4 / N1: a statistics storage of an older format (STAT$COLUMNS without the blob profile columns) must not break the queries. Alias tst10blob.
-- Before the fix: every SELECT / PREPARE over a user table and REFRESH fail with "Column unknown STAT$BLOB_LEVELS".
-- After the fix: the queries work with the estimates of the storage-less path (the same rows= as in section A),
-- firebird.log of the root gets exactly ONE new entry "The extended statistics storage (the STAT$ tables) has an old format",
-- REFRESH still fails, but its error ends with "The extended statistics storage has an old format: add the missing columns ...".
-- Section D adds the columns back: REFRESH works and the estimate comes from the statistics (x = 5: rows=100).
-- Data: t 10 000 rows, x = mod(id, 100) (real count of x = 5 is 100), b a short text blob.
set bail off;
create database 'tst10blob' user SYSDBA;
create table t (id int not null, x int, b blob sub_type text);
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 10000) do begin
    insert into t values (:i, mod(:i, 100), 'abc' || :i);
    i = i + 1; end
end^
set term ;^
commit;

select 'A: no storage (baseline estimate)' as tag from rdb$database;
set explain on;
set planonly on;
select count(*) from t where x = 5;
set planonly off;
set explain off;

alter database add extended statistics; commit;
alter database refresh statistics; commit;
alter table STAT$COLUMNS drop STAT$BLOB_LEVELS, drop STAT$BLOB_LEVELS_TEXT, drop STAT$BLOB_AVG_PAGES,
  drop STAT$BLOB_MAX_PAGES, drop STAT$BLOB_AVG_LEN, drop STAT$BLOB_MAX_LEN, drop STAT$SUB_TYPE;
commit;
connect 'tst10blob' user SYSDBA;

select 'B: old storage, expected count 100 and the estimate of section A' as tag from rdb$database;
select count(*) from t where x = 5;
select count(*) from t;
set explain on;
set planonly on;
select count(*) from t where x = 5;
set planonly off;
set explain off;

select 'C: REFRESH on old storage, expected error with the old format hint' as tag from rdb$database;
alter database refresh statistics; commit;
select count(*) from t where x = 5;

select 'D: columns added back, expected rows=100 from the statistics' as tag from rdb$database;
alter table STAT$COLUMNS
  add STAT$BLOB_LEVELS BLOB SUB_TYPE BINARY,
  add STAT$BLOB_LEVELS_TEXT BLOB SUB_TYPE TEXT CHARACTER SET UTF8,
  add STAT$BLOB_AVG_PAGES DOUBLE PRECISION,
  add STAT$BLOB_MAX_PAGES INTEGER,
  add STAT$BLOB_AVG_LEN DOUBLE PRECISION,
  add STAT$BLOB_MAX_LEN BIGINT,
  add STAT$SUB_TYPE SMALLINT;
commit;
alter database refresh statistics; commit;
connect 'tst10blob' user SYSDBA;
select count(*) from t where x = 5;
set explain on;
set planonly on;
select count(*) from t where x = 5;
set planonly off;
set explain off;
