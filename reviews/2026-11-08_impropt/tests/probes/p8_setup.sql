create database 'probe8' user SYSDBA page_size 8192;
alter database add extended statistics;
commit;
-- o: 100k orders, grp = mod(id,100) (grp < 5 keeps 5%)
create table o (id int not null primary key, grp int);
-- l: 2M lines, 20 per order; st = 'RARE' for i mod 997 = 0 (~0.05%, independent of grp)
create table l (id int, o_id int, ps_id int, pb_id int, st varchar(10));
-- l2: 100k rows, o_id NOT NULL only for 1% (per probe of o: 0.01 rows)
create table l2 (id int, o_id int, ps_id int);
create table ps (id int not null primary key, v int);
create table pb (id int not null primary key, v int);
commit;
set term ^;
execute block as declare i int = 1; begin
  while (i <= 100000) do begin insert into o values(:i, mod(:i, 100)); insert into pb values(:i, :i); i = i + 1; end
  i = 1;
  while (i <= 10000) do begin insert into ps values(:i, :i); i = i + 1; end
end^
execute block as declare i int = 0; begin
  while (i < 2000000) do begin
    insert into l values(:i, mod(:i, 100000) + 1, mod(:i * 7, 10000) + 1, mod(:i * 7, 100000) + 1,
      iif(mod(:i, 997) = 0, 'RARE', 'N' || mod(:i, 10)));
    i = i + 1; end
end^
execute block as declare i int = 0; begin
  while (i < 100000) do begin
    insert into l2 values(:i, iif(mod(:i, 100) = 0, mod(:i * 13, 100000) + 1, null), mod(:i * 7, 10000) + 1);
    i = i + 1; end
end^
set term ;^
commit;
create index l_o on l(o_id);
create index l2_o on l2(o_id);
commit;
alter database refresh statistics;
commit;
