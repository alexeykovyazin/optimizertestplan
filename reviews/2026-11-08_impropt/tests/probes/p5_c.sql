connect 'probe5' user SYSDBA;
set list on;
select rdb$field_name from rdb$relation_fields where rdb$relation_name = 'STAT$COLUMNS' order by rdb$field_position;
set blob all;
select STAT$FIELD_NAME, STAT$MCV_TEXT from STAT$COLUMNS where STAT$RELATION_NAME = 'TZI' and STAT$FIELD_NAME = 'Y';
