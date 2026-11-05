connect 'tst2' user SYSDBA;
create table tz(x int, y int, p varchar(100));
set term ^;
execute block as declare i int = 0; begin while (i < 100000) do begin insert into tz values(:i, mod(:i, 20000), lpad(:i, 100, 'abcdefghij')); i = i + 1; end end^
set term ;^
commit;
alter database refresh statistics sample for table tz;
commit;
select STAT$FIELD_NAME, STAT$NDISTINCT, STAT$SAMPLE_SIZE, STAT$SAMPLE_FRACTION, STAT$ND_EXACT from STAT$COLUMNS where STAT$RELATION_NAME = 'TZ';
alter database refresh statistics scan for table tz;
commit;
select STAT$FIELD_NAME, STAT$NDISTINCT, STAT$SAMPLE_SIZE, STAT$SAMPLE_FRACTION, STAT$ND_EXACT from STAT$COLUMNS where STAT$RELATION_NAME = 'TZ';
set planonly on;
set explain on;
select count(*) from tz where x between 1000 and 1999;
select count(*) from tz where x < 50000;
select count(*) from t where n between 10 and 20;
select count(*) from t where n < 50;
select count(*) from t where n > 90;
