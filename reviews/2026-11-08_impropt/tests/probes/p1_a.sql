connect 'probe1' user SYSDBA;
set explain on;
set plan on;
-- A1 baseline M2 (no index)
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and ob.y > oa.z;
-- A2 sibling stream in WHERE (oc joined after the outer join), expected 9000
select count(*) from oa left join ob on oa.x = ob.x join oc on oc.k = oa.x where ob.y > oc.w;
-- A3 same, reference value (WHERE possiblyUnknown, not pushed), expected 9000
select count(*) from oa left join ob on oa.x = ob.x join oc on oc.k = oa.x where coalesce(ob.y, -1) > oc.w;
-- A4 sibling first in FROM
select count(*) from oc join oa on oc.k = oa.x left join ob on oa.x = ob.x where ob.y > oc.w;
-- A5 RIGHT JOIN, expected 20000 / 9000
select count(*), count(ob.x) from ob right join oa on oa.x = ob.x and ob.y > oa.z;
-- A6 FULL JOIN, expected 31000 / 20000 / 20000
select count(*), count(oa.x), count(ob.x) from oa full join ob on oa.x = ob.x and ob.y > oa.z;
-- A7 WHERE conjunct both streams, no ON residual, expected 9000
select count(*) from oa left join ob on oa.x = ob.x where ob.y > oa.z;
