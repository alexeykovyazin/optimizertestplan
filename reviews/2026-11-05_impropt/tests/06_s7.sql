connect 'tst2' user SYSDBA;
create table t7(a int, b int);
set term ^;
execute block as declare i int = 0; begin while (i < 20000) do begin insert into t7 values(mod(:i, 50), :i); i = i + 1; end end^
set term ;^
commit;
alter table t7 alter column a type bigint;
alter table t7 alter column b type varchar(20);
commit;
insert into t7 values(5000000000, 'new');
commit;
alter database refresh statistics for table t7;
commit;
select STAT$FIELD_NAME, STAT$TYPE, STAT$NDISTINCT, STAT$NULL_FRACTION, STAT$SAMPLE_SIZE from STAT$COLUMNS where STAT$RELATION_NAME = 'T7';
set planonly on;
set explain on;
select count(*) from t7 where a = 7;
select count(*) from t7 where b = '123';
