connect 'probe1' user SYSDBA;
set explain on;
-- E1 oa.z = 10 everywhere: 5 > all -> FALSE, expected 0
select count(*) from rdb$database where 5 > all (select oa.z from oa left join ob on oa.x = ob.x);
-- E2 expected 1
select count(*) from rdb$database where not (5 > all (select oa.z from oa left join ob on oa.x = ob.x));
-- E3 15 > all -> TRUE, expected 1
select count(*) from rdb$database where 15 > all (select oa.z from oa left join ob on oa.x = ob.x);
-- E4 5 = any -> FALSE, expected 0
select count(*) from rdb$database where 5 = any (select oa.z from oa left join ob on oa.x = ob.x);
-- E5 plain WHERE on outer stream only, expected 20000 (z=10)
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x where oa.z = 10;
