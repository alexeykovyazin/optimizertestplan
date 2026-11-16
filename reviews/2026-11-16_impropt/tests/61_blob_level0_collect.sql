-- 61_blob_level0_collect.sql - level-0 text blob distributions (b2800ecb7d), collection side. Alias tst11blb.
-- tb: 20 000 rows, 10% b = 'short' (2 000 rows), 90% b = 2 000 x 'x' (level 0, longer than 1 024 bytes - skipped by the collector). No NULLs.
-- Z1: after REFRESH SAMPLE the null fraction must be 0. Z2: b = 'short' real 2 000. Z3: COLUMN B refresh keeps charset. Z4: domain blob with COLLATE.
set bail off;
create database 'tst11blb' user SYSDBA default character set utf8;
create table tb (id int, b blob sub_type text character set utf8);
create domain d_t blob sub_type text character set utf8;
create table tc (b d_t collate unicode_ci);
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 20000) do begin insert into tb values (:i, iif(mod(:i,10)=0, 'short', rpad('', 2000, 'x'))); i = i + 1; end
  i = 0;
  while (i < 100) do begin insert into tc values (iif(mod(:i,2)=0,'abc','ABC')); i = i + 1; end
end^
set term ;^
commit;
alter database add extended statistics; commit;
set list on;
select 'Z2: FULL' as tag from rdb$database;
alter database refresh statistics full; commit;
select STAT$FIELD_NAME, STAT$TYPE, STAT$SUB_TYPE, STAT$CHARSET, STAT$COLLATE, STAT$NULL_FRACTION, STAT$SAMPLE_SIZE, STAT$NDISTINCT, cast(substring(STAT$MCV_TEXT from 1 for 200) as varchar(200)) mcv, cast(substring(STAT$BLOB_LEVELS_TEXT from 1 for 100) as varchar(100)) lv from STAT$COLUMNS where STAT$RELATION_NAME in ('TB','TC') and STAT$FIELD_NAME = 'B' order by STAT$RELATION_NAME;
commit;
connect 'tst11blb' user SYSDBA;
set list off; set explain on;
select count(*) from tb where b = 'short';
select count(*) from tb where b starting with 'sh';
select count(*) from tb where b starting with 'xx';
select count(*) from tb where b like '%x%';
select count(*) from tb where b is null;
select count(*) from tc where b = 'abc';
set explain off; set list on;
select 'Z1: SAMPLE' as tag from rdb$database;
alter database refresh statistics sample for table tb; commit;
select STAT$NULL_FRACTION, STAT$SAMPLE_SIZE from STAT$COLUMNS where STAT$RELATION_NAME = 'TB' and STAT$FIELD_NAME = 'B';
commit;
connect 'tst11blb' user SYSDBA;
set list off; set explain on;
select count(*) from tb where b is null;
select count(*) from tb where b is not null;
set explain off; set list on;
select 'Z3: COLUMN B' as tag from rdb$database;
alter database refresh statistics full for table tb column b; commit;
select STAT$TYPE, STAT$CHARSET, STAT$COLLATE, STAT$SAMPLE_SIZE, STAT$NULL_FRACTION from STAT$COLUMNS where STAT$RELATION_NAME = 'TB' and STAT$FIELD_NAME = 'B';
commit;
connect 'tst11blb' user SYSDBA;
set list off; set explain on;
select count(*) from tb where b = 'short';
set explain off; set list on;
select 'Z5: VARCHAR column replaced by a blob, no refresh' as tag from rdb$database;
create table tv (id int, c varchar(20) character set utf8); commit;
insert into tv select id, 'v' || mod(id, 100) from tb; commit;
alter database refresh statistics full for table tv; commit;
alter table tv drop c; commit;
alter table tv add c blob sub_type text character set utf8; commit;
update tv set c = 'w' || mod(id, 4); commit;
connect 'tst11blb' user SYSDBA;
set list off; set explain on;
select count(*) from tv where c = 'w1';
select count(*) from tv where c > 'v5';
