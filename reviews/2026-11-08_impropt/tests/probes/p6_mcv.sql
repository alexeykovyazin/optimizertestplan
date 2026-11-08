connect 'probe6' user SYSDBA;
set blob all;
set list on;
select STAT$MCV_TEXT from STAT$COLUMNS where STAT$RELATION_NAME = 'PN' and STAT$FIELD_NAME = 'NM';
