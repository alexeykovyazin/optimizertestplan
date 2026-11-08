connect 'probe8' user SYSDBA;
set explain on;
set stats on;
-- U8: LATERAL of 2 tables with a rare filter; real = number of RARE lines = 2007
select count(*) from o cross join lateral (select l.pb_id from l join ps on ps.id = l.ps_id where l.o_id = o.id and l.st = 'RARE') x;
-- U8b: the same, joined on to pb (100k)
select count(*) from o cross join lateral (select l.pb_id from l join ps on ps.id = l.ps_id where l.o_id = o.id and l.st = 'RARE') x join pb on pb.id = x.pb_id;
