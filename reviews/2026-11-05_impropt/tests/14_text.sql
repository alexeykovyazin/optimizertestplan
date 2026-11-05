connect 'tst2' user SYSDBA;
create table tu(s varchar(30) character set utf8, sn varchar(30));
set term ^;
execute block as declare i int = 0; begin while (i < 100000) do begin insert into tu values('v' || mod(:i, 500), 'v' || mod(:i, 500)); i = i + 1; end end^
set term ;^
commit;
alter database refresh statistics for table tu;
commit;
set planonly on;
set explain on;
select count(*) from tu where s >= 'v5';
select count(*) from tu where s < 'v5';
select count(*) from tu where s between 'v2' and 'v3';
select count(*) from tu where sn >= 'v5';
select count(*) from tu where sn < 'v5';
select count(*) from tu where sn = 'v5';
select count(*) from t where s >= 'v5';
select count(*) from t where s < 'v5';
set planonly off;
select count(*) from tu where s >= 'v5';
select count(*) from tu where s between 'v2' and 'v3';
