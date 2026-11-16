set list on;
select current_timestamp as t_before from rdb$database;
alter database refresh statistics;
commit;
select current_timestamp as t_after from rdb$database;
select r.STAT$RELATION_NAME, r.STAT$FIELD_NAME, r.STAT$TYPE, r.STAT$SUB_TYPE, r.STAT$SAMPLE_SIZE, r.STAT$NDISTINCT, r.STAT$BLOB_AVG_LEN, r.STAT$BLOB_AVG_PAGES from STAT$COLUMNS r where r.STAT$SUB_TYPE is not null;
