connect 'tst2' user SYSDBA;
alter table t add y int; commit;
update t set y = x; commit;
set planonly on;
set explain on;
select count(*) from t where y between 10 and 20;
select count(*) from t where y > 5;
set planonly off;
select 'S2 ok' from rdb$database;
