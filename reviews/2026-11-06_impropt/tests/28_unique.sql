connect 'tst2' user SYSDBA;
create table td(d double precision, c varchar(10) character set utf8);
set term ^;
execute block as declare i int = 0; begin while (i < 100000) do begin
 insert into td values(:i / 1000000e0, 'k' || lpad(:i, 6, '0')); i = i + 1; end end^
set term ;^
commit;
alter database refresh statistics for table td; commit;
set planonly on; set explain on;
-- real 50000, 1001, 50000, 1000
select count(*) from td where d >= 0.05;
select count(*) from td where d between 0.01 and 0.011;
select count(*) from td where c >= 'k050000';
select count(*) from td where c between 'k050000' and 'k050999';
set planonly off;
select count(*) from td where d >= 0.05;
select count(*) from td where d between 0.01 and 0.011;
