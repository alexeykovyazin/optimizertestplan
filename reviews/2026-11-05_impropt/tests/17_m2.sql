connect 'tst2' user SYSDBA;
create index ob_x on ob(x);
commit;
set explain on;
set plan on;
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and ob.y > oa.z;
select count(*), count(ob.x) from oa left join ob on oa.x + 0 = ob.x + 0 and ob.y > oa.z;
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and (ob.y > oa.z or ob.y = 0);
