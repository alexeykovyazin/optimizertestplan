connect 'probe8' user SYSDBA;
set explain on;
set stats on;
-- Q5b: unfiltered outer, l2.o_id 99% NULL (0.01 rows per probe of o), deep ps. real 1000
select count(*) from o join l2 on l2.o_id = o.id join ps on ps.id = l2.ps_id;
-- Q5c: forced NL for Q5b
select count(*) from o join l2 on l2.o_id = o.id join ps on ps.id = l2.ps_id
  plan join (o natural, l2 index (l2_o), ps index (rdb$primary7));
-- Q8: rare filter of 1 per probe vs rarer: st = 'N3' (10%, 2 rows per probe), deep ps. real 10000
select count(*) from o join l on l.o_id = o.id join ps on ps.id = l.ps_id where o.grp < 5 and l.st = 'N3';
