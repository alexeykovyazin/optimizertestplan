connect 'probe8' user SYSDBA;
-- la: 1.2 rows per order; lb: 0.8 rows per order (estimate 1.0, containment). Same rare filter.
create table la (id int, o_id int, ps_id int, st varchar(10));
create table lb (id int, o_id int, ps_id int, st varchar(10));
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 120000) do begin
    insert into la values(:i, mod(:i, 100000) + 1, mod(:i * 7, 10000) + 1, iif(mod(:i, 97) = 0, 'RARE', 'N'));
    i = i + 1; end
  i = 0;
  while (i < 80000) do begin
    insert into lb values(:i, :i + 1, mod(:i * 7, 10000) + 1, iif(mod(:i, 97) = 0, 'RARE', 'N'));
    i = i + 1; end
end^
set term ;^
commit;
create index la_o on la(o_id);
create index lb_o on lb(o_id);
commit;
alter database refresh statistics for table la;
alter database refresh statistics for table lb;
commit;
set explain on;
set stats on;
-- C1: la (1.2 rows/probe) + rare filter (~1%), deep ps
select count(*) from o join la on la.o_id = o.id join ps on ps.id = la.ps_id where o.grp < 5 and la.st = 'RARE';
-- C2: lb (0.8 rows/probe, estimated 1.0) + the same rare filter, deep ps
select count(*) from o join lb on lb.o_id = o.id join ps on ps.id = lb.ps_id where o.grp < 5 and lb.st = 'RARE';
