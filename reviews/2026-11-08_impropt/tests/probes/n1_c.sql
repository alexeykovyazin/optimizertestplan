set list on;
create database 'probe2' user SYSDBA;
create table q(x int, s varchar(40), t varchar(40));
insert into q select r, 'v' || lpad(mod(r, 50), 2 + mod(r, 7), '0'), 'k' || r || 'z' || mod(r * 7, 13)
  from (select row_number() over () r from rdb$types a, rdb$types b rows 3000);
commit;
alter database add extended statistics;
commit;
create extended statistics q_xs on q (x, s) mcv;
commit;
alter database refresh statistics;
commit;
-- imitate a store created before ab9730e98b: no STAT$LEN_* columns
alter table STAT$COLUMNS drop STAT$LEN_COUNT, drop STAT$LEN_SUM, drop STAT$LEN_MIN, drop STAT$LEN_MAX, drop STAT$LEN_BOUNDS, drop STAT$LEN_BOUNDS_TEXT;
commit;
connect 'probe2' user SYSDBA;
select 'C-old-store' tag from rdb$database;
select count(*) cnt_x from q where x = 1;
-- migration: add the six columns
alter table STAT$COLUMNS
  add STAT$LEN_COUNT BIGINT,
  add STAT$LEN_SUM BIGINT,
  add STAT$LEN_MIN INTEGER,
  add STAT$LEN_MAX INTEGER,
  add STAT$LEN_BOUNDS BLOB SUB_TYPE BINARY,
  add STAT$LEN_BOUNDS_TEXT BLOB SUB_TYPE TEXT CHARACTER SET UTF8;
commit;
connect 'probe2' user SYSDBA;
select 'C-migrated-before-refresh' tag from rdb$database;
set explain on;
select count(*) cnt_x from q where x = 1;
select count(*) cnt_t1 from q where t containing '12';
set explain off;
alter database refresh statistics;
commit;
connect 'probe2' user SYSDBA;
select 'C-after-refresh' tag from rdb$database;
select stat$field_name, stat$len_count, stat$len_sum, stat$len_min, stat$len_max, stat$len_bounds is not null has_bounds,
  substring(stat$len_bounds_text from 1 for 200) bounds_text
  from stat$columns where stat$relation_name = 'Q' order by 1;
select count(*) named_structs from stat$multi_columns where stat$system_flag = 0;
set explain on;
select count(*) cnt_x from q where x = 1;
select count(*) cnt_t2 from q where t containing '12';
select count(*) cnt_t3 from q where t like '%9z%';
set explain off;
