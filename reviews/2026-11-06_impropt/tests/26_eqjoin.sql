connect 'tst2' user SYSDBA;
-- ja: 250 values (50 hot, 200 tail); jb: 100 hot values outside ja, 50000 unique values
create table ja(k int); create table jb(k int);
set term ^;
execute block as declare i int = 0; begin while (i < 100000) do begin
 insert into ja values(iif(:i < 75000, mod(:i, 50) + 1, 51 + mod(:i - 75000, 200)));
 insert into jb values(iif(:i < 50000, 100001 + mod(:i, 100), 51 + :i - 50000));
 i = i + 1; end end^
set term ;^
commit;
alter database refresh statistics for table ja; alter database refresh statistics for table jb; commit;
set planonly on; set explain on;
-- real 25000
select count(*) from ja join jb on ja.k = jb.k;
set planonly off;
select count(*) from ja join jb on ja.k = jb.k;
