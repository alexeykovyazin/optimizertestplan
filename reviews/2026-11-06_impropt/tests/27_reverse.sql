connect 'tst2' user SYSDBA;
create table tc(s varchar(10) character set utf8, ci varchar(10) character set utf8 collate unicode_ci, ch char(10));
set term ^;
execute block as declare i int = 0; begin while (i < 100000) do begin
 insert into tc values(iif(:i < 50000, 'abc', 'v' || mod(:i, 500)), iif(:i < 50000, 'abc', 'v' || mod(:i, 500)), iif(:i < 50000, 'ABC', 'v' || mod(:i, 500)));
 i = i + 1; end end^
set term ;^
commit;
alter database refresh statistics for table tc; commit;
set planonly on; set explain on;
select count(*) from tc where 'XABCX' containing s;
select count(*) from tc where 'ABCDEF' starting with ci;
select count(*) from tc where 'xABCabcx' containing ci;
select count(*) from tc where 'ABCDEF' starting with ch;
select count(*) from tc where 'v123' containing s;
set planonly off;
select count(*) from tc where 'XABCX' containing s;
select count(*) from tc where 'ABCDEF' starting with ci;
select count(*) from tc where 'xABCabcx' containing ci;
select count(*) from tc where 'ABCDEF' starting with ch;
select count(*) from tc where 'v123' containing s;
