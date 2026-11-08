connect 'probe7' user SYSDBA;
drop table h;
commit;
create table h (k int, f int);
commit;
set term ^;
execute block as declare i int = 1; begin while (i <= 12000000) do begin insert into h values(case when mod(:i, 1000) = 500 then null else mod(:i, 12000) + 4499991 end, mod(:i, 7)); i = i + 1; end end^
set term ;^
commit;
create index h_k on h(k);
commit;
alter database refresh statistics;
commit;
select STAT$RELATION_NAME, STAT$CARDINALITY, STAT$CARD_EXACT from STAT$TABLES;
