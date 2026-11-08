-- Add the a3cfa97218 length-distribution columns to the existing STAT$ store,
-- then refresh so the new engine fills them (REFRESH ~73 s on dellg15).
set list on;
alter table STAT$COLUMNS
  add STAT$LEN_COUNT bigint,
  add STAT$LEN_SUM bigint,
  add STAT$LEN_MIN integer,
  add STAT$LEN_MAX integer,
  add STAT$LEN_BOUNDS blob sub_type binary,
  add STAT$LEN_BOUNDS_TEXT blob sub_type text character set utf8;
commit;
alter database refresh statistics;
commit;
select count(*) as cols_total, count(STAT$LEN_COUNT) as cols_with_len from STAT$COLUMNS;
select count(*) as multi from STAT$MULTI_COLUMNS;
