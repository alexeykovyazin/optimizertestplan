connect 'probe3' user SYSDBA;
-- E2: FK fanout skew correlated with the parent filter
-- par: 1000 rows unique id, flag 'Y' for id 1..10
-- chi: 100000 rows, 50000 rows pid in 1..10, 50000 rows pid in 11..1000
create table par(id int not null primary key, flag char(1));
create table chi(pid int);
-- E4: BLOB predicate
create table tbl(b blob sub_type text);
set term ^;
execute block as declare i int = 0; begin while (i < 100000) do begin
 if (i < 1000) then insert into par values(:i + 1, iif(:i < 10, 'Y', 'N'));
 insert into chi values(iif(:i < 50000, mod(:i, 10) + 1, 11 + mod(:i, 990)));
 insert into tbl values('v' || mod(:i, 1000));
 i = i + 1; end end^
set term ;^
commit;
create index chi_pid on chi(pid); commit;
alter database refresh statistics for table par; alter database refresh statistics for table chi;
alter database refresh statistics for table tbl; commit;
set planonly on; set explain on;
-- E2 real 50000
select count(*) from par p join chi c on c.pid = p.id where p.flag = 'Y';
-- E4 real 100 / 300
select count(*) from tbl where b = 'v1';
select count(*) from tbl where b in ('v1','v2','v3');
set planonly off; set explain off;
select count(*) from par p join chi c on c.pid = p.id where p.flag = 'Y';
select count(*) from tbl where b = 'v1';
select count(*) from tbl where b in ('v1','v2','v3');
