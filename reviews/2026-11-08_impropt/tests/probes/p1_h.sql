connect 'probe1' user SYSDBA;
create table od(k int primary key, w int);
set term ^;
execute block as declare i int = 0; begin while (i < 100) do begin insert into od values(:i, 1); i = i + 1; end end^
set term ;^
commit;
set explain on;
-- H1 chain of LEFT JOINs, expected 20000
select count(*) from oa left join ob on oa.x = ob.x left join oc on oc.k = oa.x;
-- H2 FULL JOIN then inner join on the oa column; correct value from NL-forced variant H2r
select count(*) from oa full join ob on oa.x = ob.x join oc on oc.k = oa.x;
-- H3 LEFT JOIN then lookup to a small PK table on an outer-stream column; expected = count of oa with z in od.k -> oa.z=10 or null
select count(*) from oa left join ob on oa.x = ob.x join od on od.k = oa.z;
-- H3r reference: same join as derived table (no pushing of od.k = oa.z into the left join)
select count(*) from (select oa.z from oa left join ob on oa.x = ob.x rows 100000) t join od on od.k = t.z;
