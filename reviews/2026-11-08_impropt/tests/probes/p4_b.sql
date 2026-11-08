connect 'probe4' user SYSDBA;
create table tc(s varchar(10) character set utf8, ci varchar(10) character set utf8 collate unicode_ci, ch char(10),
  chu char(10) character set utf8, chci char(10) character set utf8 collate unicode_ci, vn varchar(10));
set term ^;
execute block as declare i int = 0; begin while (i < 100000) do begin
 insert into tc values(iif(:i < 50000, 'abc', 'v' || mod(:i, 500)), iif(:i < 50000, 'abc', 'v' || mod(:i, 500)), iif(:i < 50000, 'ABC', 'v' || mod(:i, 500)),
   iif(:i < 50000, 'abc', 'v' || mod(:i, 500)), iif(:i < 50000, 'abc', 'v' || mod(:i, 500)), iif(:i < 50000, 'abc', 'v' || mod(:i, 500)));
 i = i + 1; end end^
set term ;^
commit;
alter database refresh statistics for table tc; commit;
