connect 'probe8' user SYSDBA;
-- ba: 3M rows, x = id, index on x (navigation for ORDER BY ba.x); no index on ba.id
create table ba (id int, x int, pad char(10));
-- bb: 4.2M rows, index on id (bb is join-dependent on ba)
create table bb (id int, g int, pad char(10));
commit;
set term ^;
execute block as declare i int = 1; begin
  while (i <= 3000000) do begin insert into ba values(:i, :i, 'a'); i = i + 1; end
  i = 1;
  while (i <= 4200000) do begin insert into bb values(:i, mod(:i, 1000), 'b'); i = i + 1; end
end^
set term ;^
commit;
create index ba_x on ba(x);
create index bb_id on bb(id);
commit;
alter database refresh statistics for table ba;
alter database refresh statistics for table bb;
commit;
