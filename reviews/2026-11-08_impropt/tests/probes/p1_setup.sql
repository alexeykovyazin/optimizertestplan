create database 'probe1' user SYSDBA;
create table oa(x int, z int);
create table ob(x int, y int);
create table oc(k int, w int);
set term ^;
execute block as declare i int = 0; begin while (i < 20000) do begin insert into oa values(:i, 10); insert into ob values(:i, mod(:i, 20)); insert into oc values(:i, 10); i = i + 1; end end^
set term ;^
commit;
select count(*) from oa;
