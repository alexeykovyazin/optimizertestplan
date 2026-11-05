connect 'tst2' user SYSDBA;
set planonly on;
set explain on;
select count(*) from t where n = 12.34;
select count(*) from t where n between 10 and 20;
select count(*) from t where s = 'v7';
select count(*) from t where g = 3;
