connect 'probe6' user SYSDBA;
alter table STAT$COLUMNS drop STAT$LEN_BOUNDS_TEXT, drop STAT$LEN_BOUNDS, drop STAT$LEN_MAX, drop STAT$LEN_MIN, drop STAT$LEN_SUM, drop STAT$LEN_COUNT;
commit;
select 'before' from rdb$database;
select count(*) from fn where id = 1;
select count(*) from pn where nm containing 'smith';
