connect 'probe8' user SYSDBA;
create index o_grp on o(grp);
create table pt (id int not null primary key, v int);
create table la2 (id int, o_id int, pt_id int, st varchar(10));
create table lb2 (id int, o_id int, pt_id int, st varchar(10));
commit;
set term ^;
execute block as declare i int = 0; begin
  i = 1;
  while (i <= 4000) do begin insert into pt values(:i, :i); i = i + 1; end
  i = 0;
  -- la2: 1.2 rows per order
  while (i < 120000) do begin
    insert into la2 values(:i, mod(:i, 100000) + 1, mod(:i * 7, 4000) + 1, iif(mod(:i, 97) = 0, 'RARE', 'N'));
    i = i + 1; end
  i = 0;
  -- lb2: 0.8 rows per order (one row for 80% of the orders)
  while (i < 80000) do begin
    insert into lb2 values(:i, :i + 1, mod(:i * 7, 4000) + 1, iif(mod(:i, 97) = 0, 'RARE', 'N'));
    i = i + 1; end
end^
set term ;^
commit;
create index la2_o on la2(o_id);
create index lb2_o on lb2(o_id);
commit;
alter database refresh statistics for table o;
alter database refresh statistics for table pt;
alter database refresh statistics for table la2;
alter database refresh statistics for table lb2;
commit;
set explain on;
set stats on;
-- C1: la2 (1.2 rows/probe) + rare filter (~1%), deep pt (4000)
select count(*) from o join la2 on la2.o_id = o.id join pt on pt.id = la2.pt_id where o.grp < 2 and la2.st = 'RARE';
-- C2: lb2 (0.8 rows/probe) + the same rare filter, deep pt
select count(*) from o join lb2 on lb2.o_id = o.id join pt on pt.id = lb2.pt_id where o.grp < 2 and lb2.st = 'RARE';
