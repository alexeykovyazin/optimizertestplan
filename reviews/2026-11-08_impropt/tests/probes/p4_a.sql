create database 'probe4' user SYSDBA page_size 8192;
-- U7: non-text types
create table tt(b bigint, d date, ts timestamp, bo boolean, db double precision, nm numeric(9,2), tm time, vn varchar(10), cn char(6), vo varchar(10) character set octets);
set term ^;
execute block as declare i int = 0; begin while (i < 20000) do begin
 insert into tt values(:i * 1000000000, dateadd(mod(:i, 400) day to date '2020-01-01'), dateadd(:i second to timestamp '2021-05-06 10:00:00'),
   iif(mod(:i,3)=0, true, false), :i / 7.0, mod(:i, 50) + 0.25, dateadd(mod(:i, 3600) second to time '08:00:00'),
   'k' || mod(:i, 30), 'c' || mod(:i, 20), 'o' || mod(:i, 25));
 i = i + 1; end end^
set term ;^
commit;
alter database add extended statistics; commit;
alter database refresh statistics for table tt; commit;
set blob all;
set list on;
select STAT$FIELD_NAME, STAT$MCV_ROWS, STAT$HIST_ROWS, substring(STAT$MCV_TEXT from 1 for 260) mcv, substring(STAT$HISTOGRAM_TEXT from 1 for 300) h1 from STAT$COLUMNS where STAT$RELATION_NAME = 'TT' order by STAT$FIELD_NAME;
set list off;
