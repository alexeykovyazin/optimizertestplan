-- 38b_stat_new_open.sql - W4: run on 06041718cc after 38a: every SELECT fails with Column unknown STAT$BLOB_LEVELS.
-- p5 (step 2, NEW engine 06041718cc): the same database, the storage of a3cfa97218.
connect 'tst9mig' user SYSDBA;
select count(*) as new_select from t where x = 1;
alter database refresh statistics; commit;
