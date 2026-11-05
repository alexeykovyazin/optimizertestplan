connect 'tst2' user SYSDBA;
alter database refresh statistics for table oa;
alter database refresh statistics for table ob;
commit;
set planonly on;
set explain on;
select count(*), count(ob.x) from oa join ob on oa.x = ob.x;
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x;
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and ob.y > oa.z;
