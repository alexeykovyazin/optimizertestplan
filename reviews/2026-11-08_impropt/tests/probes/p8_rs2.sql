connect 'probe8' user SYSDBA;
-- rc: like ra, but only 1 of 1000 rows has a join key present in rb (real output stays small,
-- the per-probe estimate of the filtered outer stays 60 rows)
create table rc (id int, x int, g int);
commit;
set term ^;
execute block as declare i int = 1; begin
  while (i <= 800000) do begin
    insert into rc values(:i, :i, iif(mod(:i, 1000) = 0, mod(:i, 70000) + 1, 200000 + :i));
    i = i + 1; end
end^
set term ;^
commit;
create index rc_x on rc(x);
commit;
alter database refresh statistics for table rc;
commit;
set explain on;
set stats on;
-- T1 ordered (restart path). expected: 36000 | 1000 | 600000
select count(*), min(x), max(x) from (select rc.x, rb.id from rc join rb on rb.g = rc.g where rc.x < 600001 order by rc.x rows 1000000000);
-- T2 control, no ORDER BY. expected: 36000 | 1000 | 600000
select count(*), min(x), max(x) from (select rc.x, rb.id from rc join rb on rb.g = rc.g where rc.x < 600001);
-- T3 ordered, top-level, first 3 rows by x desc via second sort column (plan only)
set planonly on;
select rc.x, rb.id from rc join rb on rb.g = rc.g where rc.x < 600001 order by rc.x;
