connect 'probe7' user SYSDBA;
set term ^;
execute block as declare i int = 4300001; begin while (i <= 5600000) do begin insert into l values(:i, :i, mod(:i, 50)); i = i + 1; end end^
set term ;^
commit;
alter database refresh statistics;
commit;
select STAT$RELATION_NAME, STAT$CARDINALITY, STAT$CARD_EXACT from STAT$TABLES;
