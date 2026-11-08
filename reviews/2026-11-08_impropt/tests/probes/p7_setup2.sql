create database 'probe7' user SYSDBA page_size 16384;
create table l (id int not null, id2 int, g int);
create table h (k int, f int);
commit;
set term ^;
execute block as declare i int = 1; begin while (i <= 4500000) do begin insert into l values(:i, :i, mod(:i, 50)); i = i + 1; end end^
execute block as declare i int = 1; begin while (i <= 5500000) do begin insert into h values(case when mod(:i, 1000) = 500 then null else mod(:i - 1, 2500000) + 1 end, mod(:i, 100)); i = i + 1; end end^
set term ;^
commit;
alter table l add constraint pk_l primary key (id);
commit;
alter database add extended statistics;
commit;
connect 'probe7' user SYSDBA;
alter database refresh statistics;
commit;
select STAT$RELATION_NAME, STAT$CARDINALITY, STAT$CARD_EXACT from STAT$TABLES;
