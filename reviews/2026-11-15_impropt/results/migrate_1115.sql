-- Add the 06041718cc BLOB-profile columns to the a3cfa97218-format STAT$ store, then refresh.
set list on; set stats on;
alter table STAT$COLUMNS
  add STAT$BLOB_LEVELS blob sub_type binary,
  add STAT$BLOB_LEVELS_TEXT blob sub_type text character set utf8,
  add STAT$BLOB_AVG_PAGES double precision,
  add STAT$BLOB_MAX_PAGES integer,
  add STAT$BLOB_AVG_LEN double precision,
  add STAT$BLOB_MAX_LEN bigint,
  add STAT$SUB_TYPE smallint;
commit;
select current_timestamp as t_before from rdb$database;
alter database refresh statistics;
commit;
select current_timestamp as t_after from rdb$database;
set stats off;
select count(*) as cols_total, count(STAT$LEN_COUNT) as cols_with_len, count(STAT$BLOB_AVG_PAGES) as cols_with_blob from STAT$COLUMNS;
select count(*) as multi from STAT$MULTI_COLUMNS;
select count(*) as titles from TITLE;
