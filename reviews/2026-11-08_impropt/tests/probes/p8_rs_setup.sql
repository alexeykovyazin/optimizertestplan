connect 'probe8' user SYSDBA;
-- ra: 800k rows, x = id (index for ORDER BY navigation), g = join key (no index)
create table ra (id int, x int, g int);
-- rb: 4.2M rows, g = mod(i,70000)+1 -> 60 rows per key, index on g (rb is join-dependent on ra)
create table rb (id int, g int);
commit;
set term ^;
execute block as declare i int = 1; begin
  while (i <= 800000) do begin insert into ra values(:i, :i, mod(:i, 70000) + 1); i = i + 1; end
  i = 1;
  while (i <= 4200000) do begin insert into rb values(:i, mod(:i, 70000) + 1); i = i + 1; end
end^
set term ;^
commit;
create index ra_x on ra(x);
create index rb_g on rb(g);
commit;
alter database refresh statistics for table ra;
alter database refresh statistics for table rb;
commit;
