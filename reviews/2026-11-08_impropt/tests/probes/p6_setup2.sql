connect 'probe6' user SYSDBA;
alter table pn add nl varchar(200) character set utf8, add nq varchar(200) character set utf8;
commit;
update pn set nl = nm || ' / ' || nm || ' / ' || nm, nq = iif(mod(id, 1000) = 0, 'A', nm || ' / ' || nm || ' / ' || nm);
commit;
alter database refresh statistics for table pn;
commit;
set list on;
select STAT$FIELD_NAME, STAT$NDISTINCT, STAT$MCV_ROWS, STAT$LEN_MIN, STAT$LEN_MAX, STAT$LEN_BOUNDS_TEXT
from STAT$COLUMNS where STAT$RELATION_NAME = 'PN' and STAT$FIELD_NAME in ('NL', 'NQ');
set list off;
select min(char_length(nl)), avg(char_length(nl)), max(char_length(nl)) from pn;
