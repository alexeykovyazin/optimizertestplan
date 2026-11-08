connect 'probe1' user SYSDBA;
set explain on;
set plan on;
-- B1 plain chain: LEFT JOIN then INNER JOIN on outer-stream column, expected 20000
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x join oc on oc.k = oa.x;
-- B2 same with a non-equi ON residual, expected 20000 / 9000
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and ob.y > oa.z join oc on oc.k = oa.x;
-- B3 inner join first, expected 20000
select count(*), count(ob.x) from oc join oa on oc.k = oa.x left join ob on oa.x = ob.x;
