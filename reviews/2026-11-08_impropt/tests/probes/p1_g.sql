connect 'probe1' user SYSDBA;
create index ob_y on ob(y);
commit;
set explain on;
-- G1 forced NL, rare inner filter: real count(*) 20000
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and ob.y = 5 plan join (oa natural, ob index (ob_x));
-- G2 optimizer choice, rare filter
select count(*), count(ob.x) from oa left join ob on oa.x = ob.x and ob.y = 5;
set planonly on;
-- G3 expression keys + local index on y: match share taken from local index?
select count(*), count(ob.x) from oa left join ob on oa.x + 0 = ob.x + 0 and ob.y = 5;
