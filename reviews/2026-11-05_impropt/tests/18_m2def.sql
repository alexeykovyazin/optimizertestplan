connect 'tst2def' user SYSDBA;
set plan on;
select rdb$get_context('SYSTEM', 'DB_NAME') from rdb$database;
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and ob.y > oa.z;
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and (ob.y > oa.z or ob.y = 0);
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and ob.y > 10;
