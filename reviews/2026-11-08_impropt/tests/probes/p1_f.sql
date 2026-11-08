connect 'probe1' user SYSDBA;
update ob set y = null where mod(x, 100) = 19;
update oa set z = null where mod(x, 1000) = 11;
update oa set x = null where mod(x, 1000) = 999;
update ob set x = null where mod(x, 1000) = 998;
commit;
set plan on;
-- F1 HJ
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and ob.y > oa.z;
-- F1r forced NL
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and ob.y > oa.z plan join (oa natural, ob index (ob_x));
-- F2 HJ, OR with IS NULL in ON
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and (ob.y > oa.z or ob.y is null);
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and (ob.y > oa.z or ob.y is null) plan join (oa natural, ob index (ob_x));
-- F3 IS NOT DISTINCT FROM key + residual
select count(*), count(ob.y) from oa left join ob on oa.x is not distinct from ob.x and ob.y > oa.z;
select count(*), count(ob.y) from oa left join ob on oa.x is not distinct from ob.x and ob.y > oa.z plan join (oa natural, ob index (ob_x));
-- F4 NOT in ON
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and not (ob.y > oa.z);
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and not (ob.y > oa.z) plan join (oa natural, ob index (ob_x));
