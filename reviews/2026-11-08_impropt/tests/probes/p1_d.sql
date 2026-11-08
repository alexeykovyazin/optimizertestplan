connect 'probe1' user SYSDBA;
set explain on;
-- D1 expected 0 (15 > all fails on y=15..19)
select count(*) from rdb$database where 15 > all (select ob.y from oa left join ob on oa.x = ob.x);
-- D2 expected 1
select count(*) from rdb$database where not (15 > all (select ob.y from oa left join ob on oa.x = ob.x));
-- D2r reference with forced NL
select count(*) from rdb$database where not (15 > all (select ob.y from oa left join ob on oa.x = ob.x plan join (oa natural, ob index (ob_x))));
-- D3 expected 1 (no y > 100, NOT ANY true)
select count(*) from rdb$database where not (100 < any (select ob.y from oa left join ob on oa.x = ob.x));
-- D3r reference with forced NL
select count(*) from rdb$database where not (100 < any (select ob.y from oa left join ob on oa.x = ob.x plan join (oa natural, ob index (ob_x))));
-- D4 IN with a non-equi residual, expected 9000 rows of oc with w=10? -> count of oc where 15 in (...)
select count(*) from oc where oc.k in (select ob.x from oa left join ob on oa.x = ob.x where ob.y > oc.w);
