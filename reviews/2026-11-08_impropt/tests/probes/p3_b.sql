connect 'probe3' user SYSDBA;
-- B: side d has all values in MCV (no tail); its values sit in the tail of f
-- f: 50000 rows hot 100001..100050 (1000 each), 50000 rows unique 1..50000
-- d: 1000 rows, values 1..10 (100 each)
create table pf(k int); create table pd(k int);
-- B2: partial overlap: d2 values 1..10, f2 hot values 1..5 and 100001..100045, tail unique 6..50005
create table pf2(k int); create table pd2(k int);
set term ^;
execute block as declare i int = 0; begin while (i < 100000) do begin
 insert into pf values(iif(:i < 50000, 100001 + mod(:i, 50), :i - 50000 + 1));
 insert into pf2 values(iif(:i < 50000, iif(mod(:i, 50) < 5, mod(:i, 50) + 1, 100001 + mod(:i, 50)), :i - 50000 + 6));
 if (i < 1000) then begin
   insert into pd values(mod(:i, 10) + 1);
   insert into pd2 values(mod(:i, 10) + 1);
 end
 i = i + 1; end end^
set term ;^
commit;
alter database refresh statistics for table pf; alter database refresh statistics for table pd;
alter database refresh statistics for table pf2; alter database refresh statistics for table pd2; commit;
set list on;
select stat$relation_name, stat$field_name, stat$null_fraction, stat$ndistinct, stat$sample_size, stat$mcv_rows, stat$hist_rows from stat$columns where stat$relation_name in ('PF','PD','PF2','PD2');
select stat$relation_name, substring(stat$mcv_text from 1 for 120) from stat$columns where stat$relation_name in ('PF','PD','PF2','PD2');
set list off;
set planonly on; set explain on;
-- B real 1000
select count(*) from pf join pd on pf.k = pd.k;
-- B2 real 5*1000*100 + 5*1*100 = 500500
select count(*) from pf2 join pd2 on pf2.k = pd2.k;
set planonly off; set explain off;
select count(*) from pf join pd on pf.k = pd.k;
select count(*) from pf2 join pd2 on pf2.k = pd2.k;
