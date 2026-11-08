connect 'probe7' user SYSDBA;
drop table h;
commit;
create table h (k int, f int);
commit;
set term ^;
execute block as declare i int = 1; begin while (i <= 12000000) do begin insert into h values(case when mod(:i, 1000) = 500 then null else mod(:i - 1, 6000000) + 3500001 end, mod(:i, 100)); i = i + 1; end end^
set term ;^
commit;
alter database refresh statistics;
commit;
select STAT$RELATION_NAME, STAT$CARDINALITY, STAT$CARD_EXACT from STAT$TABLES;
