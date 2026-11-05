connect 'tst2' user SYSDBA;
select count(*) from t having count(*) > 0;
select * from (select max(x) m from t) where m > 0;
select * from (select count(*) c, sum(x) sx from t) where c > 0 and sx > 0;
select * from (select count(*) c from t having count(*) > 1) where c > 2;
select 'S1 ok' from rdb$database;
