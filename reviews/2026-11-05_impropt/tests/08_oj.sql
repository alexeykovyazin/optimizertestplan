connect 'tst2' user SYSDBA;
create table oa(x int, z int);
create table ob(x int, y int);
set term ^;
execute block as declare i int = 0; begin while (i < 20000) do begin insert into oa values(:i, 10); insert into ob values(:i, mod(:i, 20)); i = i + 1; end end^
set term ;^
commit;
set explain on;
set plan on;
select count(*), count(ob.x) from oa join ob on oa.x = ob.x;
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x;
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and ob.y > oa.z;
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x where ob.y > 10 or ob.y is null;
