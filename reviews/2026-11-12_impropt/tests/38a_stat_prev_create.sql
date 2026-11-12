-- 38a_stat_prev_create.sql - W4: run on a3cfa97218 (STAT$ storage in the old format). Alias tst9mig.
-- p5 (step 1, PREV engine a3cfa97218): a storage of the 08.11 format (with STAT$LEN_*).
create database 'tst9mig' user SYSDBA;
alter database add extended statistics; commit;
create table t(x int, s varchar(20), b blob sub_type text);
insert into t values(1, 'a', 'blob'); insert into t values(2, 'b', null); commit;
alter database refresh statistics; commit;
select count(*) as prev_ok from t where x = 1;
