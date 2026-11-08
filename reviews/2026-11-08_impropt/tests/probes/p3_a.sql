create database 'probe3' user SYSDBA page_size 4096;
alter database add extended statistics; commit;
-- U1 repro (same data as 26_eqjoin)
create table ja(k int); create table jb(k int);
set term ^;
execute block as declare i int = 0; begin while (i < 100000) do begin
 insert into ja values(iif(:i < 75000, mod(:i, 50) + 1, 51 + mod(:i - 75000, 200)));
 insert into jb values(iif(:i < 50000, 100001 + mod(:i, 100), 51 + :i - 50000));
 i = i + 1; end end^
set term ;^
commit;
alter database refresh statistics for table ja; alter database refresh statistics for table jb; commit;
set list on;
select stat$relation_name, stat$field_name, stat$null_fraction, stat$ndistinct, stat$sample_size, stat$mcv_rows, stat$hist_rows from stat$columns where stat$relation_name in ('JA','JB');
set list off;
set planonly on; set explain on;
select count(*) from ja join jb on ja.k = jb.k;
set planonly off; set explain off;
select count(*) from ja join jb on ja.k = jb.k;
