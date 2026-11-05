connect 'tst2' user SYSDBA;
set planonly on;
set explain on;
select count(*) from tz where y > ?;
select count(*) from tz where y > 1 + 1;
select count(*) from tz where y between ? and ?;
select count(*) from tz where y > ? and y < ?;
select count(*) from tz, oa where tz.y > oa.x;
