connect 'probe8' user SYSDBA;
select (select count(*) from o) o, (select count(*) from l) l, (select count(*) from l2) l2,
       (select count(*) from ps) ps, (select count(*) from pb) pb,
       (select count(*) from l where st = 'RARE') rare,
       (select count(*) from l2 where o_id is not null) l2nn
from rdb$database;
select rdb$get_context('SYSTEM', 'ENGINE_VERSION') from rdb$database;
