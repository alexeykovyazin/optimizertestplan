connect 'probe1' user SYSDBA;
create index ob_x on ob(x);
commit;
set explain on;
set plan on;
-- C1 B1 with index on ob(x), expected 20000 / 20000
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x join oc on oc.k = oa.x;
-- C2 B2 with index on ob(x), expected 20000 / 9000
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and ob.y > oa.z join oc on oc.k = oa.x;
-- C3 forced nested loop via PLAN, expected 20000 / 9000
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and ob.y > oa.z join oc on oc.k = oa.x
  plan join (join (oa natural, ob index (ob_x)), oc natural);
-- C4 M2 shape with index (17_m2), expected 20000 / 9000
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and ob.y > oa.z;
