connect 'probe8' user SYSDBA;
set list off;
set explain on;
set stats on;
-- Q1: rare filter on join-driven l, deep pb (100k). real ~100
select count(*) from o join l on l.o_id = o.id join pb on pb.id = l.pb_id where o.grp < 5 and l.st = 'RARE';
-- Q3 control: same without the rare filter. real 100000
select count(*) from o join l on l.o_id = o.id join pb on pb.id = l.pb_id where o.grp < 5;
-- Q2: rare filter, deep ps (10k). real ~100
select count(*) from o join l on l.o_id = o.id join ps on ps.id = l.ps_id where o.grp < 5 and l.st = 'RARE';
-- Q2c control: same without the rare filter. real 100000
select count(*) from o join l on l.o_id = o.id join ps on ps.id = l.ps_id where o.grp < 5;
-- Q4: 4 tables. real ~100
select count(*) from o join l on l.o_id = o.id join ps on ps.id = l.ps_id join pb on pb.id = l.pb_id where o.grp < 5 and l.st = 'RARE';
-- Q5: floor-limited join-driven l2 (0.01 rows per probe), deep ps. real ~50
select count(*) from o join l2 on l2.o_id = o.id join ps on ps.id = l2.ps_id where o.grp < 5;
-- Q6: forced NL plan for Q2, to compare time
select count(*) from o join l on l.o_id = o.id join ps on ps.id = l.ps_id where o.grp < 5 and l.st = 'RARE'
  plan join (o natural, l index (l_o), ps index (rdb$primary7));
