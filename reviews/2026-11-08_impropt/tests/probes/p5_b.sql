connect 'probe5' user SYSDBA;
create table tu5(d double precision, nm numeric(9,4), ts timestamp, c varchar(10) character set utf8, cn varchar(10));
set term ^;
execute block as declare i int = 0; begin while (i < 100000) do begin
 insert into tu5 values((:i - 50000) / 1000000e0, :i / 10000e0,
   timestamp '2020-01-01 00:00:00' + :i / 86400e0,
   'k' || lpad(:i, 6, '0'), 'k' || lpad(:i, 6, '0'));
 i = i + 1; end end^
set term ;^
commit;
alter database refresh statistics for table tu5;
commit;
set echo on;
select STAT$FIELD_NAME, STAT$NDISTINCT, STAT$SAMPLE_SIZE, STAT$SAMPLE_FRACTION, STAT$ND_EXACT from STAT$COLUMNS where STAT$RELATION_NAME = 'TU5';
select STAT$FIELD_NAME, STAT$NDISTINCT, STAT$SAMPLE_SIZE, STAT$SAMPLE_FRACTION, STAT$ND_EXACT from STAT$COLUMNS where STAT$RELATION_NAME = 'TZI';
set planonly on; set explain on;
-- DOUBLE -0.05..0.05: real 50000, 1001, 50000
select count(*) from tu5 where d >= 0;
select count(*) from tu5 where d between -0.01 and -0.009;
select count(*) from tu5 where d < 0;
-- NUMERIC(9,4) 0..9.9999: real 10001, 50000
select count(*) from tu5 where nm between 1 and 2;
select count(*) from tu5 where nm >= 5;
-- TIMESTAMP 1 row per second, 100000 s: real 56800, 3601
select count(*) from tu5 where ts >= timestamp '2020-01-01 12:00:00';
select count(*) from tu5 where ts between timestamp '2020-01-01 01:00:00' and timestamp '2020-01-01 02:00:00';
-- R1 text unique UTF8: real 50000, 1000
select count(*) from tu5 where c >= 'k050000';
select count(*) from tu5 where c between 'k050000' and 'k050999';
select count(*) from tu5 where c < 'k050000';
-- R1 text unique NONE: real 50000, 1000
select count(*) from tu5 where cn >= 'k050000';
select count(*) from tu5 where cn between 'k050000' and 'k050999';
-- tzi: same stats, natural vs index
select count(*) from tzi where y between 10000 and 10199 plan (tzi natural);
select count(*) from tzi where y between 10000 and 10199;
select count(*) from tzi where x between 50000 and 50999 plan (tzi natural);
select count(*) from tzi where x between 50000 and 50999;
set planonly off; set explain off;
select count(*) from tu5 where ts >= timestamp '2020-01-01 12:00:00';
select count(*) from tu5 where ts between timestamp '2020-01-01 01:00:00' and timestamp '2020-01-01 02:00:00';
select count(*) from tu5 where nm between 1 and 2;
-- growth: add 10000 rows above max, no refresh. real 10000, 1000
insert into tz select x + 100000, y, p from tz where x < 10000;
commit;
set planonly on; set explain on;
select count(*) from tz where x >= 100000;
select count(*) from tz where x between 105000 and 105999;
select count(*) from tz where x between 50000 and 50999;
set planonly off; set explain off;
