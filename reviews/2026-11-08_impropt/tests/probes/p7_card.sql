create database 'probe7' user SYSDBA page_size 16384;
create table t (id int, g int);
commit;
set term ^;
execute block as declare i int = 1; begin while (i <= 400000) do begin insert into t values(:i, mod(:i, 50)); i = i + 1; end end^
set term ;^
commit;
alter database add extended statistics;
commit;
connect 'probe7' user SYSDBA;
alter database refresh statistics;
commit;
connect 'probe7' user SYSDBA;
set explain on; set planonly on;
select count(*) from t;
set planonly off; set explain off;
set term ^;
execute block as declare i int = 400001; begin while (i <= 500000) do begin insert into t values(:i, mod(:i, 50)); i = i + 1; end end^
set term ;^
commit;
connect 'probe7' user SYSDBA;
set explain on; set planonly on;
select count(*) from t;
set planonly off; set explain off;
alter database refresh statistics;
commit;
select STAT$RELATION_NAME, STAT$CARDINALITY, STAT$CARD_EXACT from STAT$TABLES;
connect 'probe7' user SYSDBA;
set explain on; set planonly on;
select count(*) from t;
