create database 'tst2' user SYSDBA page_size 4096;
create table t(x int, n numeric(9,2), s varchar(30), g int, p varchar(100));
set term ^;
execute block as declare i int = 0; begin while (i < 100000) do begin insert into t values(:i, mod(:i,100) + 0.34, 'v' || mod(:i, 500), mod(:i, 10), lpad(:i, 100, 'abcdefghij')); i = i + 1; end end^
set term ;^
commit;
create table tb(bins int); insert into tb values(7); commit;
select bins from tb;
alter database add extended statistics;
commit;
