connect 'tst2' user SYSDBA;
set planonly on;
set explain on;
select count(*) from tz where y between 10000 and 10199;
select count(*) from tz where y >= 10000 and y <= 10199;
select count(*) from tz where y >= 10000;
select count(*) from tz where y <= 10199;
