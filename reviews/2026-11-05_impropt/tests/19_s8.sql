connect 'tst2def' user SYSDBA;
create table sa(id int not null primary key, x int);
create table big(x int, y int);
commit;
set term ^;
execute block as declare i int = 0; begin while (i < 100000) do begin insert into sa values(:i, mod(:i * 7919, 100000)); i = i + 1; end end^
execute block as declare i int = 0; begin while (i < 4600000) do begin insert into big values(mod(:i, 100000), :i); i = i + 1; end end^
set term ;^
commit;
set explain on;
set planonly on;
select a.id, b.y from sa a join big b on b.x = a.x order by a.id;
select a.id, b.y from sa a join big b on b.x = a.x where a.id < 1000 order by a.id;
set planonly off;
set explain off;
set plan on;
select count(*) from (select a.id, lag(a.id) over (order by 1) prev from (select a.id from sa a join big b on b.x = a.x where a.id < 1000 order by a.id) a);
select min(d) from (select a.id - lag(a.id) over () d from (select a.id from sa a join big b on b.x = a.x where a.id < 1000 order by a.id) a);
